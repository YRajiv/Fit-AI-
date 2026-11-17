
import base64
import binascii
import io
import json
import logging
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
    # ---------- Timing start ----------
    request_start = time.time()
    # ---------------------------------


    # STEP 1: Check login

    if not request.user.is_authenticated:
        return _error(
            'Please sign in to scan food.',
            401
        )

    # STEP 2: Read frontend request
    try:
        data = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error(
            'Invalid request data.',
            400
        )
    # Log time after request parsing
    parse_time = time.time()
    logger.info('Request JSON parsing time: %.2f s', parse_time - request_start)
    # ---------- End of timing for step 2 ----------

    try:
        data = json.loads(request.body)

    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error(
            'Invalid request data.',
            400
        )

    if not isinstance(data, dict) or not data.get('image'):
        return _error(
            'No image data provided.',
            400
        )

    # STEP 3: Validate image

    try:
        image = _nutrition_image(data['image'])
    except ValueError as error:
        return _error(str(error), 400)

    # Log time after image validation
    validation_time = time.time()
    logger.info('Image validation time: %.2f s', validation_time - parse_time)
    # ---------- End of timing for step 3 ----------

    try:
        image = _nutrition_image(data['image'])

    except ValueError as error:
        return _error(str(error), 400)

    try:

        # STEP 4: Gemini configuration

        api_key = getattr(
            settings,
            'GEMINI_API_KEY',
            None
        )

        model_name = getattr(
            settings,
            'GEMINI_MODEL',
            'gemini-3.8-flash'
        )

        if not api_key:

            logger.error('GEMINI_API_KEY is missing.')

            return _error(
                'Gemini API key is not configured.',
                503
            )

        # STEP 5: Gemini prompt

        prompt = """
        You are an AI nutrition analysis assistant.

        Analyze the food visible in the provided image.

        Estimate the nutrition values for the visible serving.

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

        # STEP 6: Send image to Gemini

        client = genai.Client(api_key=api_key)

        # Define fallback model order: primary (from settings), then two alternatives
        fallback_models = [model_name, "gemini-3.8-flash", "gemini-3.5-flash-lite"]
        # Ensure we don't repeat the primary if it already matches an alternative
        fallback_models = list(dict.fromkeys(fallback_models))

        response = None
        used_model = None
        for m in fallback_models:
            used_model = m
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    response = client.models.generate_content(
                        model=m,
                        contents=[image, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type='application/json',
                            temperature=0.2
                        )
                    )
                    # Successful call, break out of both loops
                    break
                except Exception as error:
                    error_message = str(error).upper()
                    logger.exception('Gemini food scan failed. Model: %s, attempt %s', m, attempt + 1)

                    # Temporary 503 / UNAVAILABLE → exponential backoff
                    if attempt < max_attempts - 1 and (
                        '503' in error_message or 'UNAVAILABLE' in error_message
                    ):
                        backoff_seconds = 2 * (2 ** attempt)
                        time.sleep(backoff_seconds)
                        continue
                    # If last attempt for this model and still a 503/UNAVAILABLE, fall through to try next model
                    if '503' in error_message or 'UNAVAILABLE' in error_message:
                        break

                    # Rate limiting / quota exhausted – do not retry or fallback
                    if '429' in error_message or 'RESOURCE_EXHAUSTED' in error_message:
                        return _error(
                            'Gemini API quota exceeded. Please try again later.',
                            429
                        )

                    # Permanent errors – abort entirely
                    if 'API_KEY' in error_message or 'INVALID_ARGUMENT' in error_message or 'NOT_FOUND' in error_message:
                        return _error(
                            'Gemini could not analyze your image. Please try again.',
                            502
                        )

                    # Fallback for any other error
                    return _error(
                        'Gemini could not analyze your image. Please try again.',
                        502
                    )
            # If we got a successful response, exit the fallback loop
            if response and getattr(response, 'text', None):
                break
        # End of fallback attempts
        if response and getattr(response, 'text', None):
            logger.info('Gemini analysis succeeded with model %s', used_model)


        # If all attempts exhausted without a successful response
        if response is None:
            return _error(
                'Gemini is temporarily unavailable. Please try again in a few moments.',
                503
            )

        if not response or not response.text:

            return _error(
                'Gemini returned an empty response. Please scan again.',
                502
            )

        nutrition_data = _parse_nutrition(
            response.text
        )

        # STEP 8: Save food and image

        try:

            _save_food_scan(
                request.user,
                image,
                nutrition_data
            )

        except Exception:

            logger.exception(
                'Could not save food scan to database.'
            )

            return _error(
                'Food was analyzed, but saving the result failed.',
                500
            )

        # STEP 9: Return response

        return JsonResponse({
            'success': True,
            'nutrition': nutrition_data
        })

    except ValueError as error:

        logger.warning(
            'Nutrition response validation failed: %s',
            error
        )

        return _error(str(error), 502)

    except Exception:

        logger.exception(
            'Unexpected nutrition scanning error.'
        )

        return _error(
            'Something went wrong while analyzing your food.',
            500
        )

    finally:
        image.close()
