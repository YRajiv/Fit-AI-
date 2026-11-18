import logging
import base64
import binascii
import io
import json


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

# Import fallback helper utilities
from .ai_fallback import call_gemini, call_groq, call_openai, fallback_chain

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
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30_000))
    except Exception:
        logger.exception('Gemini client initialization failed.')
        return _error('Gemini could not be initialized.', 503)

    # STEP 7: Analyze image using fallback chain (Gemini -> optional Groq -> OpenAI)
    # Build the list of provider callables. Gemini will internally try its model fallbacks.
    fallback_steps: list[tuple[str, callable]] = []

    # Gemini model retries (preserve existing fallback list)
    fallback_models = list(dict.fromkeys([
        model_name,
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
    ]))
    for current_model in fallback_models:
        fallback_steps.append(
            (
                f"gemini-{current_model}",
                lambda m=current_model: call_gemini(
                    client,
                    m,
                    [image, prompt],
                ),
            )
        )

    # OPTIONAL: Groq vision‑capable model (if configured)
    groq_vision_model = getattr(settings, "GROQ_VISION_MODEL", None)
    if groq_vision_model:
        # Build messages compatible with Groq (OpenAI‑compatible). Assume the model can accept images via the standard spec.
        groq_messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data['image']}}
            ]
        }]
        fallback_steps.append(("groq", lambda: call_groq(groq_messages, model=groq_vision_model)))

    # OpenAI vision‑capable fallback (always added if API key present)
    openai_messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data['image']}}
        ]
    }]
    fallback_steps.append(("openai", lambda: call_openai(openai_messages)))

    try:
        response, used_provider = fallback_chain(fallback_steps)
    except Exception as exc:
        logger.exception("All AI providers failed for nutrition scan")
        return _error(
            "All AI providers failed to analyze the image. Please try again later.",
            503,
        )

    # Normalise response text regardless of provider source
    if used_provider.startswith("gemini"):
        # Gemini response object
        response_text = response.text
    elif isinstance(response, dict) and response.get("choices"):
        # Groq (OpenAI‑compatible) response dict
        response_text = response["choices"][0]["message"]["content"]
    else:
        # OpenAI response object
        response_text = response.choices[0].message.content

    logger.info("Nutrition analysis succeeded using provider %s", used_provider)


    # ---------------------------------------------------------------------
    # The original Gemini‑only retry block (lines 358‑447) was redundant because
    # the fallback chain above already obtained a successful response (if any).
    # We now parse the normalized `response_text` from the fallback, save the
    # scan, and return the result.
    # ---------------------------------------------------------------------
    # STEP 8: Parse nutrition response (already obtained from fallback)
    try:
        nutrition_data = _parse_nutrition(response_text)
    except Exception:
        logger.exception('Nutrition response parsing failed.')
        return _error(
            'Provider returned invalid nutrition data. Please scan again.',
            502,
        )

    # STEP 9: Save food and image to database (same as original logic)
    try:
        _save_food_scan(
            request.user,
            image,
            nutrition_data,
        )
    except Exception:
        logger.exception('Could not save food scan to database.')
        return _error(
            'Food was analyzed, but saving the result failed.',
            500,
        )

    # STEP 10: Return successful response
    return JsonResponse({
        'success': True,
        'nutrition': nutrition_data,
    })





