import logging
import base64
import binascii
import io
import json
import openai

import math
import time

from PIL import Image, UnidentifiedImageError

from django.conf import settings
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from google import genai
from google.genai import types

from .models import FoodScan


logger = logging.getLogger(__name__)


# ============================================================
# NUTRITION PAGE
# ============================================================

def nutrition_page_view(request):
    return render(request, 'nutrition/nutrition.html')


# ============================================================
# ERROR RESPONSE
# ============================================================

def _error(message, status):
    return JsonResponse({
        'success': False,
        'error': message
    }, status=status)


# ============================================================
# IMAGE VALIDATION
# ============================================================

def _nutrition_image(image_data_url):

    if not isinstance(image_data_url, str):
        raise ValueError('Please provide a valid food image.')

    if not image_data_url.startswith('data:image/'):
        raise ValueError('Please provide a valid food image.')

    header, separator, encoded_image = image_data_url.partition(',')

    if not separator or ';base64' not in header:
        raise ValueError(
            'The image data is invalid. Please capture it again.'
        )

    try:
        image_bytes = base64.b64decode(
            encoded_image,
            validate=True
        )

        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()

        with Image.open(io.BytesIO(image_bytes)) as image:
            return image.convert('RGB')

    except (
        binascii.Error,
        UnidentifiedImageError,
        OSError,
        ValueError
    ) as error:

        raise ValueError(
            'The image could not be read. Please capture it again.'
        ) from error


# ============================================================
# PARSE GEMINI RESPONSE
# ============================================================

def _parse_nutrition(response_text):

    try:
        nutrition_data = json.loads(response_text)

    except (TypeError, json.JSONDecodeError) as error:

        raise ValueError(
            'Gemini returned an invalid response. Please try again.'
        ) from error

    if not isinstance(nutrition_data, dict):
        raise ValueError('Invalid nutrition response.')

    nutrition_data['food_name'] = str(
        nutrition_data.get('food_name') or 'Scanned meal'
    )[:100]

    required_fields = (
        'calories',
        'protein',
        'carbs',
        'fat',
        'fiber',
        'sugar'
    )

    for key in required_fields:

        try:
            value = float(nutrition_data[key])

        except (KeyError, TypeError, ValueError) as error:

            raise ValueError(
                'Gemini returned incomplete nutrition values. Please scan again.'
            ) from error

        if not math.isfinite(value) or value < 0:

            raise ValueError(
                'Gemini returned invalid nutrition values.'
            )

        nutrition_data[key] = value

    nutrition_data['ai_tip'] = str(
        nutrition_data.get(
            'ai_tip',
            'Enjoy your meal and keep tracking your nutrition!'
        )
    )[:300]

    return nutrition_data


# ============================================================
# SAVE FOOD IMAGE
# ============================================================

def _save_food_scan(user, image, nutrition_data):

    image_buffer = io.BytesIO()

    image.save(
        image_buffer,
        format='JPEG',
        quality=90
    )

    image_content = ContentFile(
        image_buffer.getvalue()
    )

    image_name = (
        f"food_scan_{user.id}_"
        f"{timezone.now().strftime('%Y%m%d%H%M%S%f')}.jpg"
    )

    food_scan = FoodScan(
        user=user,
        food_name=nutrition_data['food_name'],
        calories=nutrition_data['calories'],
        protein=nutrition_data['protein'],
        carbohydrates=nutrition_data['carbs'],
        fats=nutrition_data['fat'],
        fiber=nutrition_data['fiber'],
        quantity='1 serving',
        is_consumed=True
    )

    food_scan.image.save(
        image_name,
        image_content,
        save=True
    )

    return food_scan


# ============================================================
# FOOD SCAN API
# ============================================================


@require_POST
def scan_food_view(request):
    # STEP 1: Check login
    request_start = time.time()

    if not request.user.is_authenticated:
        return _error('Please sign in to scan food.', 401)

    # STEP 2: Read frontend request
    try:
        data = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error('Invalid request data.', 400)

    parse_time = time.time()
    logger.info(
        'Request JSON parsing time: %.2f seconds',
        parse_time - request_start
    )

    if not isinstance(data, dict) or not data.get('image'):
        return _error('No image data provided.', 400)

    # STEP 3: Validate image
    try:
        image = _nutrition_image(data['image'])
    except ValueError as error:
        return _error(str(error), 400)

    validation_time = time.time()
    logger.info(
        'Image validation time: %.2f seconds',
        validation_time - parse_time
    )

    # STEP 4: Get Gemini API settings
    api_key = getattr(settings, 'GEMINI_API_KEY', None)

    model_name = getattr(
        settings,
        'GEMINI_MODEL',
        'gemini-3.8-flash'
    )

    if not api_key:
        logger.error('GEMINI_API_KEY is missing.')
        return _error('Gemini API key is not configured.', 503)

    # STEP 5: Prepare the nutrition analysis prompt
    prompt = """
    You are an AI nutrition analysis assistant.

    Analyze the food visible in the provided image.

    Estimate nutrition values for the visible serving.

    Return ONLY a valid JSON object.

    Use exactly these fields:

    {
        "food_name": "Name of the food",
        "calories": 250,
        "protein": 10,
        "carbs": 30,
        "fat": 8,
        "fiber": 4,
        "sugar": 5,
        "ai_tip": "A short helpful nutrition tip"
    }

    Rules:
    - Calories must be in kcal.
    - Protein, carbs, fat, fiber and sugar must be in grams.
    - All nutrition values must be numbers.
    - Do not include Markdown.
    - Do not include explanations outside JSON.
    - Estimate values carefully.
    - Do not claim exact serving weight if it cannot be identified.
    """

    # STEP 6: Initialize Gemini
    try:
        client = genai.Client(api_key=api_key)
    except Exception:
        logger.exception('Gemini client initialization failed.')
        return _error('Gemini could not be initialized.', 503)

    # STEP 7: Analyze image using Gemini
    fallback_models = list(dict.fromkeys([
        model_name,
        'gemini-3.8-flash',
        'gemini-3.5-flash-lite'
    ]))

    response = None
    used_model = None
    last_error = None

    for current_model in fallback_models:
        gemini_start = time.time()

        try:
            response = client.models.generate_content(
                model=current_model,
                contents=[image, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=0.2
                )
            )

            gemini_elapsed = time.time() - gemini_start

            logger.info(
                'Gemini response time: %.2f seconds using %s',
                gemini_elapsed,
                current_model
            )

            if response and getattr(response, 'text', None):
                used_model = current_model
                break

            logger.warning(
                'Empty Gemini response from model %s',
                current_model
            )

        except Exception as error:
            last_error = error
            error_message = str(error).upper()

            logger.exception(
                'Gemini request failed using model %s',
                current_model
            )

            # Quota exceeded: do not keep calling other models
            if (
                '429' in error_message
                or 'RESOURCE_EXHAUSTED' in error_message
            ):
                return _error(
                    'Gemini API quota exceeded. Please try again later.',
                    429
                )

            # Temporary service failure: try next model
            if (
                '503' in error_message
                or 'UNAVAILABLE' in error_message
            ):
                continue

            # Invalid API key
            if 'API_KEY' in error_message:
                return _error(
                    'Gemini API key is invalid or unavailable.',
                    503
                )

            # Try the next model for other model-specific errors
            continue

    if not response or not getattr(response, 'text', None):
        logger.error(
            'All Gemini models failed. Last error: %s',
            last_error
        )
        return _error(
            'Gemini could not analyze your image. Please try again later.',
            503
        )

    logger.info(
        'Food analysis succeeded using model %s',
        used_model
    )

    # STEP 8: Parse Gemini nutrition response
    try:
        nutrition_data = _parse_nutrition(response.text)

    except Exception:
        logger.exception('Nutrition response parsing failed.')
        return _error(
            'Gemini returned invalid nutrition data. Please scan again.',
            502
        )

    # STEP 9: Save food and image to database
    try:
        _save_food_scan(
            request.user,
            image,
            nutrition_data
        )

    except Exception:
        logger.exception('Could not save food scan to database.')
        return _error(
            'Food was analyzed, but saving the result failed.',
            500
        )

    # STEP 10: Return successful response
    return JsonResponse({
        'success': True,
        'nutrition': nutrition_data
    })



