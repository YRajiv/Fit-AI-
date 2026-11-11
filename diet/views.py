
import json
import os
import re
import time
import datetime

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from google import genai
from google.genai import types

from .models import UserFitnessProfile, WeeklyDietPlan


# ============================================================
# GEMINI CLIENT
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = None

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# BMI CALCULATOR
# ============================================================

def calculate_bmi(profile):

    height = float(profile.height_cm)
    weight = float(profile.weight_kg)

    if height <= 0 or weight <= 0:
        raise ValueError("Height and weight must be greater than zero.")

    height_m = height / 100

    bmi = weight / (height_m * height_m)

    bmi = round(bmi, 1)

    if bmi < 18.5:
        bmi_category = "Underweight"

    elif bmi < 25:
        bmi_category = "Normal weight"

    elif bmi < 30:
        bmi_category = "Overweight"

    else:
        bmi_category = "Obese"

    return {
        "bmi": bmi,
        "bmi_category": bmi_category
    }


# ============================================================
# FALLBACK DIET PLAN
# Used when Gemini is unavailable
# ============================================================

def create_fallback_diet_plan():

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    # Each meal:
    # Meal name, food, calories, protein, carbs,
    # fat, fiber, sugar, cost

    breakfast_options = [
        ("Idli with sambar", 300, 10, 50, 5, 6, 3, 25),
        ("Vegetable upma with curd", 320, 11, 48, 8, 5, 5, 30),
        ("Oats with milk and banana", 320, 12, 50, 8, 6, 10, 30),
        ("Dosa with sambar", 310, 10, 48, 7, 5, 4, 25),
        ("Vegetable poha", 300, 9, 48, 7, 5, 5, 25),
        ("Pesarattu with chutney", 300, 14, 42, 7, 6, 3, 30),
        ("Idli with sambar and milk", 320, 12, 48, 7, 5, 5, 30)
    ]

    mid_morning_options = [
        ("Banana and curd", 180, 5, 35, 3, 2, 12, 20),
        ("Apple and curd", 150, 5, 28, 3, 4, 15, 20),
        ("Guava and curd", 140, 5, 25, 3, 5, 10, 20),
        ("Banana and milk", 190, 7, 32, 4, 2, 12, 20),
        ("Orange and peanuts", 160, 5, 22, 7, 4, 10, 20),
        ("Papaya and curd", 150, 5, 28, 3, 4, 15, 20),
        ("Seasonal fruit and curd", 150, 5, 28, 3, 4, 12, 20)
    ]

    lunch_options = [
        ("Rice, dal, vegetables and curd", 500, 18, 75, 12, 9, 8, 60),
        ("Rice, sambar, vegetables and curd", 480, 16, 75, 10, 8, 6, 55),
        ("Rice, chicken curry and vegetables", 520, 28, 65, 14, 5, 4, 70),
        ("Rice, rajma and vegetables", 500, 18, 78, 10, 10, 5, 55),
        ("Rice, dal and vegetable curry", 480, 17, 75, 10, 9, 5, 50),
        ("Rice, chicken curry and vegetables", 520, 28, 65, 14, 5, 4, 70),
        ("Rice, chicken curry and vegetables", 520, 28, 65, 14, 5, 4, 70)
    ]

    snack_options = [
        ("Roasted chana and fruit", 180, 8, 28, 4, 6, 5, 20),
        ("Peanuts and banana", 200, 6, 30, 8, 4, 8, 20),
        ("Roasted chana", 160, 8, 25, 3, 5, 2, 15),
        ("Sprouts salad", 150, 9, 22, 3, 6, 4, 20),
        ("Boiled eggs", 150, 13, 1, 10, 0, 0, 20),
        ("Roasted peanuts", 170, 7, 8, 14, 3, 2, 20),
        ("Sprouts and roasted chana", 180, 10, 25, 4, 6, 3, 20)
    ]

    dinner_options = [
        ("Chapati, paneer curry and vegetables", 450, 20, 45, 18, 7, 5, 55),
        ("Chapati, dal and vegetable curry", 420, 16, 55, 10, 8, 5, 45),
        ("Chapati, dal and paneer", 450, 22, 45, 16, 7, 5, 55),
        ("Chapati, egg curry and vegetables", 430, 20, 45, 15, 6, 4, 50),
        ("Chapati, paneer curry and salad", 450, 20, 48, 16, 7, 5, 55),
        ("Chapati, dal and vegetable curry", 420, 16, 55, 10, 8, 5, 45),
        ("Chapati, paneer curry and salad", 450, 20, 48, 16, 7, 5, 55)
    ]

    all_options = [
        breakfast_options,
        mid_morning_options,
        lunch_options,
        snack_options,
        dinner_options
    ]

    meal_names = [
        "Breakfast",
        "Mid-morning",
        "Lunch",
        "Evening Snack",
        "Dinner"
    ]

    fallback_plan = {}

    for day_index in range(7):

        day_name = days[day_index]

        fallback_plan[day_name] = []

        for meal_index in range(5):

            meal_data = all_options[meal_index][day_index]

            meal = {

                "meal": meal_names[meal_index],

                "food": meal_data[0],

                "ingredients": [
                    meal_data[0]
                ],

                "calories": meal_data[1],

                "protein": meal_data[2],

                "carbs": meal_data[3],

                "fat": meal_data[4],

                "fiber": meal_data[5],

                "sugar": meal_data[6],

                "cost": meal_data[7]

            }

            fallback_plan[day_name].append(meal)

    return fallback_plan


# ============================================================
# JSON CLEANER
# ============================================================

def clean_json_response(response_text):

    if not response_text:
        raise ValueError("Gemini returned an empty response.")

    response_text = response_text.strip()

    if response_text.startswith("```json"):
        response_text = response_text[7:]

    elif response_text.startswith("```"):
        response_text = response_text[3:]

    if response_text.endswith("```"):
        response_text = response_text[:-3]

    return response_text.strip()


# ============================================================
# GEMINI DIET GENERATOR WITH AUTOMATIC RETRIES
# ============================================================

def generate_ai_diet_plan(profile, bmi_data):

    # If API key or client is unavailable,
    # immediately use the fallback plan.

    if client is None:

        print("Gemini API key missing. Using fallback diet plan.")

        return create_fallback_diet_plan()

    height = float(profile.height_cm)
    weight = float(profile.weight_kg)

    bmi = bmi_data["bmi"]
    bmi_category = bmi_data["bmi_category"]

    prompt = f"""
You are FitAI, an Indian diet planning assistant.

Create a practical and balanced 7-day Indian diet plan.

USER INFORMATION
----------------

Height: {height} cm
Weight: {weight} kg
BMI: {bmi}
BMI Category: {bmi_category}

DIET INSTRUCTIONS
-----------------

Use the user's BMI category to guide general food recommendations.

If Underweight:
- Suggest balanced meals with adequate energy.
- Include protein-rich foods.
- Include healthy fats and carbohydrates.
- Avoid extreme overeating.

If Normal weight:
- Suggest a balanced diet.
- Include protein, vegetables, fruits and carbohydrates.
- Include a variety of nutritious foods.

If Overweight:
- Suggest balanced meals with reasonable portions.
- Include vegetables, fiber and protein-rich foods.
- Avoid extreme calorie restriction.

If Obese:
- Suggest balanced, portion-conscious meals.
- Include vegetables, fiber and protein-rich foods.
- Avoid crash diets and extreme calorie restriction.

IMPORTANT:
BMI alone cannot determine exact calorie or protein requirements.
Do not claim that calorie or protein values are personalized medical targets.

MEAL STRUCTURE
--------------

Every day must contain exactly these five meals:

1. Breakfast
2. Mid-morning
3. Lunch
4. Evening Snack
5. Dinner

Use realistic Indian foods such as:

- Idli
- Dosa
- Upma
- Oats
- Eggs
- Rice
- Chapati
- Dal
- Sambar
- Curd
- Paneer
- Soy chunks
- Chicken
- Seasonal vegetables
- Fruits
- Roasted chana
- Peanuts

Make meals different across the seven days.

Use realistic ingredient quantities.

NUTRITION INFORMATION
---------------------

For every meal, provide estimated:

- Calories
- Protein
- Carbohydrates
- Fat
- Fiber
- Sugar
- Cost in Indian Rupees

These values are estimates, not medical prescriptions.

FINAL JSON FORMAT
-----------------

Return ONLY valid JSON.

Use exactly this structure:

{{
    "Monday": [
        {{
            "meal": "Breakfast",
            "food": "Idli with sambar",
            "ingredients": [
                "3 idlis",
                "1 bowl sambar"
            ],
            "calories": 350,
            "protein": 12,
            "carbs": 55,
            "fat": 8,
            "fiber": 6,
            "sugar": 5,
            "cost": 25
        }}
    ],
    "Tuesday": [],
    "Wednesday": [],
    "Thursday": [],
    "Friday": [],
    "Saturday": [],
    "Sunday": []
}}

Each day MUST contain exactly five meals.

Use the required meal order.

Do not return markdown.
Do not return explanations.
Return JSON only.
"""

    system_instruction = """
You are FitAI's Indian diet planning engine.

Generate realistic and balanced Indian meals.

Use BMI category to guide general food recommendations.

Do not treat BMI as sufficient information for exact calorie
or protein requirements.

Return valid JSON only.
"""

    # Try Gemini up to three times.

    for attempt in range(3):

        try:

            print(
                f"Gemini diet generation attempt {attempt + 1}/3"
            )

            response = client.models.generate_content(

                model="gemini-3.8-flash",

                contents=prompt,

                config=types.GenerateContentConfig(

                    system_instruction=system_instruction,

                    temperature=0.7,

                    response_mime_type="application/json"

                )

            )

            response_text = clean_json_response(
                response.text
            )

            ai_plan = json.loads(response_text)

            validate_diet_plan(ai_plan)

            print("Gemini diet plan generated successfully.")

            return ai_plan

        except Exception as e:

            error_message = str(e)

            print(
                "GEMINI ERROR:",
                error_message
            )

            # Temporary server or quota errors.
            temporary_error = any(
                error in error_message.upper()
                for error in [
                    "503",
                    "UNAVAILABLE",
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "500",
                    "502",
                    "504",
                    "INTERNAL"
                ]
            )

            if temporary_error and attempt < 2:

                wait_time = 2 ** (attempt + 1)

                print(
                    f"Retrying Gemini in {wait_time} seconds..."
                )

                time.sleep(wait_time)

                continue

            # If Gemini fails, use fallback.
            print(
                "Gemini failed. Switching to fallback diet plan."
            )

            return create_fallback_diet_plan()

    # Final safety fallback.
    return create_fallback_diet_plan()


# ============================================================
# VALIDATE AI DIET PLAN
# ============================================================

def validate_diet_plan(plan):

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    required_meal_types = [
        "Breakfast",
        "Mid-morning",
        "Lunch",
        "Evening Snack",
        "Dinner"
    ]

    required_fields = [
        "calories",
        "protein",
        "carbs",
        "fat",
        "fiber",
        "sugar",
        "cost"
    ]

    if not isinstance(plan, dict):
        raise ValueError("Diet plan must be a JSON object.")

    for day in days:

        if day not in plan:
            raise ValueError(
                f"{day} is missing from the diet plan."
            )

        meals = plan[day]

        if not isinstance(meals, list):
            raise ValueError(
                f"{day} must contain a list of meals."
            )

        if len(meals) != 5:
            raise ValueError(
                f"{day} must contain exactly five meals."
            )

        for index, meal in enumerate(meals):

            if not isinstance(meal, dict):
                raise ValueError(
                    f"Invalid meal in {day}."
                )

            if meal.get("meal") != required_meal_types[index]:
                raise ValueError(
                    f"Incorrect meal order in {day}."
                )

            if "food" not in meal:
                raise ValueError(
                    f"Food information missing in {day}."
                )

            for field in required_fields:

                if field not in meal:
                    raise ValueError(
                        f"{field} information missing in {day}."
                    )

                try:

                    value = float(meal[field])

                    if value < 0:
                        raise ValueError()

                except (ValueError, TypeError):

                    raise ValueError(
                        f"Invalid {field} value in {day}."
                    )

    return plan


# ============================================================
# CALCULATE DAILY TOTALS
# ============================================================

def calculate_daily_total(meals):

    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fat = 0
    total_fiber = 0
    total_sugar = 0
    total_cost = 0

    for meal in meals:

        total_calories += float(
            meal.get("calories", 0)
        )

        total_protein += float(
            meal.get("protein", 0)
        )

        total_carbs += float(
            meal.get("carbs", 0)
        )

        total_fat += float(
            meal.get("fat", 0)
        )

        total_fiber += float(
            meal.get("fiber", 0)
        )

        total_sugar += float(
            meal.get("sugar", 0)
        )

        cost = meal.get("cost", 0)

        if isinstance(cost, str):

            cost = re.sub(
                r"[^0-9.]",
                "",
                cost
            )

        try:

            total_cost += float(cost)

        except (ValueError, TypeError):

            total_cost += 0

    return {

        "calories": round(total_calories),

        "protein": round(total_protein, 1),

        "carbs": round(total_carbs, 1),

        "fat": round(total_fat, 1),

        "fiber": round(total_fiber, 1),

        "sugar": round(total_sugar, 1),

        "cost": round(total_cost, 2)

    }


# ============================================================
# PREPARE PLAN FOR TEMPLATE
# ============================================================

def prepare_plan_for_template(plan):

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    final_plan = {}

    for day in days:

        meals = plan.get(day, [])

        # Support older saved plan format.
        if isinstance(meals, dict):

            meals = meals.get(
                "meals",
                []
            )

        total = calculate_daily_total(meals)

        final_plan[day] = {

            "meals": meals,

            "calories": total["calories"],

            "protein": total["protein"],

            "carbs": total["carbs"],

            "fat": total["fat"],

            "fiber": total["fiber"],

            "sugar": total["sugar"],

            "cost": total["cost"],

            "total": total

        }

    return final_plan


# ============================================================
# MAIN DASHBOARD
# ============================================================

@login_required
def dashboard_view(request):

    try:

        profile = UserFitnessProfile.objects.get(
            user=request.user
        )

    except UserFitnessProfile.DoesNotExist:

        return redirect("onboarding")

    plan_obj = WeeklyDietPlan.objects.filter(
        user=request.user
    ).last()

    today_diet_meals = []

    current_day_name = datetime.datetime.now().strftime("%A")

    if plan_obj and plan_obj.plan_json:

        today_data = plan_obj.plan_json.get(
            current_day_name,
            {}
        )

        if isinstance(today_data, dict):

            today_diet_meals = today_data.get(
                "meals",
                []
            )

        else:

            today_diet_meals = today_data

    context = {

        "profile": profile,

        "current_day_name": current_day_name,

        "today_diet_meals": today_diet_meals

    }

    return render(
        request,
        "dashboard.html",
        context
    )


# ============================================================
# ONBOARDING
# ============================================================

@login_required
def onboarding_view(request):

    return render(
        request,
        "diet/onboarding.html"
    )


# ============================================================
# SAVE PROFILE API
# ============================================================

@login_required
@csrf_exempt
def save_profile_api(request):

    if request.method != "POST":

        return JsonResponse({

            "success": False,

            "error": "Invalid request method."

        }, status=405)

    try:

        data = json.loads(request.body)

        height = float(data.get("height"))

        weight = float(data.get("weight"))

        if height <= 0:
            raise ValueError(
                "Height must be greater than zero."
            )

        if weight <= 0:
            raise ValueError(
                "Weight must be greater than zero."
            )

        if height < 50 or height > 250:
            raise ValueError(
                "Please enter a valid height in cm."
            )

        if weight < 10 or weight > 300:
            raise ValueError(
                "Please enter a valid weight in kg."
            )

        # Save only height and weight.
        profile, created = UserFitnessProfile.objects.update_or_create(

            user=request.user,

            defaults={

                "height_cm": height,

                "weight_kg": weight

            }

        )

        bmi_data = calculate_bmi(profile)

        # Remove the previous plan because the BMI may have changed.
        WeeklyDietPlan.objects.filter(
            user=request.user
        ).delete()

        return JsonResponse({

            "success": True,

            "message": "Profile saved successfully.",

            "bmi": bmi_data["bmi"],

            "bmi_category": bmi_data["bmi_category"]

        })

    except Exception as e:

        print(
            "SAVE PROFILE ERROR:",
            str(e)
        )

        return JsonResponse({

            "success": False,

            "error": str(e)

        }, status=400)


# ============================================================
# DIET DASHBOARD
# ============================================================

@login_required
def diet_dashboard_view(request):

    try:

        profile = UserFitnessProfile.objects.get(
            user=request.user
        )

    except UserFitnessProfile.DoesNotExist:

        return redirect("onboarding")

    # Calculate BMI.
    bmi_data = calculate_bmi(profile)

    bmi = bmi_data["bmi"]

    bmi_category = bmi_data["bmi_category"]

    # Get existing diet plan.
    plan_obj = WeeklyDietPlan.objects.filter(
        user=request.user
    ).last()

    plan_data = {}

    # Generate a plan if no plan exists.
    if not plan_obj:

        try:

            print(
                "Generating BMI-based diet plan..."
            )

            ai_plan = generate_ai_diet_plan(
                profile,
                bmi_data
            )

            validate_diet_plan(ai_plan)

            plan_data = prepare_plan_for_template(
                ai_plan
            )

            # Save the plan.
            plan_obj = WeeklyDietPlan.objects.create(

                user=request.user,

                plan_json=plan_data

            )

        except Exception as e:

            print(
                "DIET GENERATION ERROR:",
                str(e)
            )

            return render(

                request,

                "diet/diet_dashboard.html",

                {

                    "profile": profile,

                    "bmi": bmi,

                    "bmi_category": bmi_category,

                    "weekly_plan": {},

                    "error": str(e)

                }

            )

    else:

        # Read existing saved plan.
        existing_plan = plan_obj.plan_json

        if existing_plan:

            first_day = existing_plan.get(
                "Monday",
                []
            )

            # Old format: Monday = [meal, meal, ...]
            if isinstance(first_day, list):

                plan_data = prepare_plan_for_template(
                    existing_plan
                )

                plan_obj.plan_json = plan_data

                plan_obj.save(
                    update_fields=["plan_json"]
                )

            else:

                plan_data = existing_plan

        else:

            plan_data = {}

    context = {

        "weekly_plan": plan_data,

        "profile": profile,

        "bmi": bmi,

        "bmi_category": bmi_category,

        "error": None

    }

    return render(

        request,

        "diet/diet_dashboard.html",

        context

    )


# ============================================================
# BODY FAT ANALYSIS - NO LONGER USED
# ============================================================

@login_required
@csrf_exempt
def analyze_body_fat_api(request):

    return JsonResponse({

        "success": False,

        "error": (
            "Body fat analysis is no longer used. "
            "Enter height and weight to calculate BMI."
        )

    }, status=410)
