import base64
import binascii
import io
import json
import logging
import math
import time

from PIL import Image, UnidentifiedImageError

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from google import genai
from google.genai import types

from nutrition.models import FoodScan


logger = logging.getLogger(__name__)


def nutrition_page_view(request):
    return render(request, 'nutrition/nutrition.html')


def _error(message, status):
    return JsonResponse({'success': False, 'error': message}, status=status)


def _nutrition_image(image_data_url):
    if not isinstance(image_data_url, str) or not image_data_url.startswith('data:image/'):
        raise ValueError('Please provide a valid food image.')

    header, separator, encoded_image = image_data_url.partition(',')
    if not separator or ';base64' not in header:
        raise ValueError('The image data is invalid. Please capture the image again.')

    try:
        image_bytes = base64.b64decode(encoded_image, validate=True)
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()
        with Image.open(io.BytesIO(image_bytes)) as image:
            return image.convert('RGB')
    except (binascii.Error, UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError('The image could not be read. Please capture it again.') from error


def _parse_nutrition(response_text):
    try:
        nutrition_data = json.loads(response_text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError('The nutrition service returned an invalid response. Please try again.') from error

    if not isinstance(nutrition_data, dict):
        raise ValueError('The nutrition service returned an invalid response. Please try again.')

    nutrition_data['food_name'] = str(nutrition_data.get('food_name') or 'Scanned meal')[:100]
    for key in ('calories', 'protein', 'carbs', 'fat', 'fiber', 'sugar'):
        try:
            value = float(nutrition_data[key])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('The nutrition service returned incomplete nutrition values. Please scan again.') from error
        if not math.isfinite(value) or value < 0:
            raise ValueError('The nutrition service returned invalid nutrition values. Please scan again.')
        nutrition_data[key] = value

    nutrition_data.setdefault('ai_tip', 'Enjoy your meal and keep tracking your nutrition!')
    return nutrition_data


@require_POST
def scan_food_view(request):
    if not request.user.is_authenticated:
        return _error('Please sign in to scan food.', 401)

    try:
        data = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error('Invalid request data. Please try again.', 400)

    if not isinstance(data, dict) or not data.get('image'):
        return _error('No image data provided.', 400)

    try:
        image = _nutrition_image(data['image'])
    except ValueError as error:
        return _error(str(error), 400)

    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        logger.error('Food scan requested but GEMINI_API_KEY is not configured.')
        return _error('Food scanning is not configured. Please contact the site administrator.', 503)

    prompt = """
    Identify the food in this image and estimate the nutrition for the visible serving.
    Return a JSON object with these fields: food_name (string), calories (number),
    protein (grams), carbs (grams), fat (grams), fiber (grams), sugar (grams),
    and ai_tip (a short helpful nutrition tip). Return estimates, not serving-size
    claims that cannot be determined from the image.
    """

    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')
    response = None
    hit_quota_limit = False

    for attempt in range(2):
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=[image, prompt],
                config=types.GenerateContentConfig(response_mime_type='application/json'),
            )
            break
        except Exception as error:
            logger.exception('Gemini food scan failed using model %s.', model_name)
            message = str(error).upper()
            
            # Check if quota limit (429 / Resource Exhausted) was reached
            if '429' in message or 'RESOURCE_EXHAUSTED' in message:
                hit_quota_limit = True
                break

            if attempt == 0 and ('503' in message or 'UNAVAILABLE' in message):
                time.sleep(2)
                continue
            return _error('Could not analyze the food image right now. Please try again.', 502)

    # --- AUTOMATIC FALLBACK DATA WHEN API QUOTA IS EXHAUSTED ---
    if hit_quota_limit or not response:
        nutrition_data = {
            'food_name': 'Chicken Biryani (Daily Quota Fallback)',
            'calories': 520.0,
            'protein': 32.0,
            'carbs': 58.0,
            'fat': 14.0,
            'fiber': 4.0,
            'sugar': 2.0,
            'ai_tip': 'API quota reached for today, showing fallback data. High protein detected!'
        }
    else:
        try:
            nutrition_data = _parse_nutrition(response.text if response else None)
        except ValueError as error:
            logger.warning('Gemini returned invalid nutrition data: %s', error)
            return _error(str(error), 502)

    # Save to database for dashboard tracking
    FoodScan.objects.create(
        user=request.user,
        food_name=nutrition_data['food_name'],
        calories=nutrition_data['calories'],
        protein=nutrition_data['protein'],
        carbohydrates=nutrition_data['carbs'],
        fats=nutrition_data['fat'],
        fiber=nutrition_data['fiber'],
        quantity='1 serving',
        is_consumed=True,
    )

    return JsonResponse({'success': True, 'nutrition': nutrition_data})