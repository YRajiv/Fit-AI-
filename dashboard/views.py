
import ast
import json
import requests

from datetime import datetime, time, timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from workouts.models import Workout
from diet.models import WeeklyDietPlan, UserFitnessProfile
from nutrition.models import FoodScan, NutritionGoal, WaterIntake
from reminders.models import Reminder
from ai_features.models import AIFeature
from progress.models import DailyProgress

from .models import Dashboard


# ==============================================================
# HELPER 1: GET TODAY'S DATETIME RANGE
# ==============================================================

def get_today_datetime_range():

    today = timezone.localdate()

    tomorrow = today + timedelta(days=1)

    today_start = timezone.make_aware(
        datetime.combine(today, time.min),
        timezone.get_current_timezone()
    )

    tomorrow_start = timezone.make_aware(
        datetime.combine(tomorrow, time.min),
        timezone.get_current_timezone()
    )

    return today, tomorrow, today_start, tomorrow_start


# ==============================================================
# HELPER 2: CONVERT STORED JSON / PYTHON DATA
# ==============================================================

def parse_stored_data(data):

    if not isinstance(data, str):
        return data

    try:
        return json.loads(data)

    except (json.JSONDecodeError, TypeError):

        try:
            return ast.literal_eval(data)

        except (ValueError, SyntaxError):

            return {}


# ==============================================================
# HELPER 3: NORMALIZE DIET MEALS
# ==============================================================

def normalize_diet_meals(meals):

    cleaned_meals = []

    # If only one meal dictionary is provided
    if isinstance(meals, dict):
        meals = [meals]

    if not isinstance(meals, list):
        return cleaned_meals

    for meal in meals:

        # Convert string meal into dictionary
        if isinstance(meal, str):

            meal = parse_stored_data(meal)

        # Keep valid meal dictionaries
        if isinstance(meal, dict):

            cleaned_meals.append(meal)

        # Handle plain text meal names
        elif isinstance(meal, str) and meal.strip():

            cleaned_meals.append({

                "meal": "Meal",

                "food": meal,

                "calories": 0,

                "protein": 0,

                "cost": 0

            })

    return cleaned_meals


# ==============================================================
# HELPER 4: GET TODAY'S MEALS FROM WEEKLY PLAN
# ==============================================================

def get_today_diet_meals(user, today):

    plan_obj = WeeklyDietPlan.objects.filter(
        user=user
    ).order_by('-created_at').first()

    if not plan_obj or not plan_obj.plan_json:

        return []

    plan_data = parse_stored_data(
        plan_obj.plan_json
    )

    if not isinstance(plan_data, dict):

        return []

    current_day_name = today.strftime("%A")

    today_data = plan_data.get(
        current_day_name,
        {}
    )

    today_data = parse_stored_data(today_data)

    if isinstance(today_data, dict):

        meals = today_data.get(
            "meals",
            []
        )

    elif isinstance(today_data, list):

        meals = today_data

    else:

        meals = []

    return normalize_diet_meals(meals)


# ==============================================================
# 1. MAIN DASHBOARD
# ==============================================================

@login_required
def dashboard(request):

    user = request.user

    today, tomorrow, today_start, tomorrow_start = (
        get_today_datetime_range()
    )

    # ==========================================================
    # DASHBOARD SUMMARY
    # ==========================================================

    dashboard_data = Dashboard.objects.filter(
        user=user
    ).first()

    # ==========================================================
    # TODAY'S WORKOUT
    # ==========================================================

    workout = Workout.objects.filter(
        user=user,
        workout_date=today
    ).order_by('-created_at').first()

    recent_workouts = Workout.objects.filter(
        user=user
    ).order_by('-created_at')[:5]

    # ==========================================================
    # TODAY'S COMPLETED WORKOUTS
    # ==========================================================

    today_completed_workouts = Workout.objects.filter(
        user=user,
        is_completed=True,
        completed_at__gte=today_start,
        completed_at__lt=tomorrow_start
    )

    completed_workout_count = today_completed_workouts.count()

    # ==========================================================
    # TODAY'S DIET PLAN
    # ==============================================================

    current_day_name = today.strftime("%A")

    today_diet_meals = get_today_diet_meals(
        user,
        today
    )

    # ==========================================================
    # CALCULATE PLANNED PROTEIN
    # ==============================================================

    planned_protein_today = 0

    for meal in today_diet_meals:

        try:

            planned_protein_today += float(
                meal.get("protein", 0) or 0
            )

        except (ValueError, TypeError):

            pass

    planned_protein_today = round(
        planned_protein_today,
        1
    )

    # ==========================================================
    # TODAY'S CONSUMED NUTRITION
    # ==============================================================

    food_data = FoodScan.objects.filter(
        user=user,
        is_consumed=True,
        scan_date__gte=today_start,
        scan_date__lt=tomorrow_start
    ).aggregate(

        total_protein=Sum('protein'),

        total_calories=Sum('calories')

    )

    consumed_protein = round(
        float(food_data["total_protein"] or 0),
        1
    )

    consumed_calories = round(
        float(food_data["total_calories"] or 0),
        1
    )

    # ==========================================================
    # LATEST FOOD SCAN
    # ==============================================================

    food_scan = FoodScan.objects.filter(
        user=user
    ).order_by('-scan_date').first()

    # ==========================================================
    # NUTRITION GOAL
    # ==============================================================

    nutrition_goal = NutritionGoal.objects.filter(
        user=user
    ).first()

    # ==========================================================
    # WATER INTAKE
    # ==============================================================

    water_intake = WaterIntake.objects.filter(
        user=user,
        date=today
    ).first()

    # ==========================================================
    # DAILY PROGRESS
    # ==============================================================

    daily_progress, created = DailyProgress.objects.get_or_create(

        user=user,

        date=today,

        defaults={

            'steps': 0,

            'steps_goal': 8000,

            'active_minutes': 0,

            'distance_km': 0.0,

            'activity_calories': 0.0

        }

    )

    # ==========================================================
    # STEP PERCENTAGE
    # ==============================================================

    if daily_progress.steps_goal > 0:

        step_percentage = round(

            (
                daily_progress.steps /
                daily_progress.steps_goal
            ) * 100

        )

        step_percentage = min(
            step_percentage,
            100
        )

    else:

        step_percentage = 0

    # ==========================================================
    # DAILY ACTIVITY INFORMATION
    # ==============================================================

    active_minutes_today = daily_progress.active_minutes

    activity_calories_today = daily_progress.activity_calories

    steps_today = daily_progress.steps

    distance_today = daily_progress.distance_km

    # ==========================================================
    # AI ANALYSIS
    # ==============================================================

    ai_result = AIFeature.objects.filter(
        user=user
    ).order_by('-created_at').first()

    # ==========================================================
    # REMINDERS
    # ==============================================================

    all_reminders = Reminder.objects.filter(
        user=user,
        is_active=True
    ).order_by('reminder_time')

    todays_reminders = []

    for reminder in all_reminders:

        if reminder.repeat == "Daily":

            todays_reminders.append(reminder)

        elif reminder.repeat == "Once":

            if reminder.reminder_date == today:

                todays_reminders.append(reminder)

        elif reminder.repeat == "Weekly":

            if (
                reminder.reminder_date
                and reminder.reminder_date.weekday() == today.weekday()
            ):

                todays_reminders.append(reminder)

    # ==========================================================
    # DASHBOARD CONTEXT
    # ==============================================================

    context = {

        "dashboard": dashboard_data,

        "workout": workout,

        "recent_workouts": recent_workouts,

        "today_completed_workouts": today_completed_workouts,

        "completed_workout_count": completed_workout_count,

        "today_diet_meals": today_diet_meals,

        "current_day_name": current_day_name,

        "consumed_protein": consumed_protein,

        "consumed_calories": consumed_calories,

        "planned_protein_today": planned_protein_today,

        "food_scan": food_scan,

        "nutrition_goal": nutrition_goal,

        "water_intake": water_intake,

        "ai_result": ai_result,

        "reminders": todays_reminders,

        "daily_progress": daily_progress,

        "step_percentage": step_percentage,

        "steps_today": steps_today,

        "active_minutes_today": active_minutes_today,

        "activity_calories_today": activity_calories_today,

        "distance_today": distance_today,

    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )


# ==============================================================
# 2. QUICK WATER ADD
# ==============================================================

@login_required
@require_POST
def add_water_quick(request):

    try:

        amount_to_add = float(
            request.POST.get(
                "amount",
                0.25
            )
        )

    except (ValueError, TypeError):

        amount_to_add = 0.25

    if amount_to_add not in [0.25, 0.5, 1.0]:

        return redirect('dashboard:home')

    today = timezone.localdate()

    water_record = WaterIntake.objects.filter(
        user=request.user,
        date=today
    ).first()

    if water_record is None:

        water_record = WaterIntake.objects.create(
            user=request.user,
            water_amount=0.0
        )

    water_record.water_amount += amount_to_add

    water_record.save()

    return redirect('dashboard:home')


# ==============================================================
# 3. GET USER FITNESS INFORMATION FOR AI
# ==============================================================

def get_user_fitness_context(user):

    today, tomorrow, today_start, tomorrow_start = (
        get_today_datetime_range()
    )

    context = {}

    # ==========================================================
    # USER FITNESS PROFILE
    # ==============================================================

    profile = UserFitnessProfile.objects.filter(
        user=user
    ).first()

    if profile:

        weight = getattr(
            profile,
            'weight_kg',
            None
        )

        height = getattr(
            profile,
            'height_cm',
            None
        )

        age = getattr(
            profile,
            'age',
            None
        )

        goal = getattr(
            profile,
            'goal',
            None
        )

        gender = getattr(
            profile,
            'gender',
            None
        )

        activity = getattr(
            profile,
            'activity_level',
            None
        )

        context["fitness_profile"] = {

            "weight_kg": weight,

            "height_cm": height,

            "age": age,

            "gender": gender,

            "goal": goal,

            "activity_level": activity,

        }

        # CALCULATE BMI

        if weight and height:

            height_m = float(height) / 100

            if height_m > 0:

                bmi = float(weight) / (
                    height_m ** 2
                )

                context["fitness_profile"]["BMI"] = round(
                    bmi,
                    2
                )

    else:

        context["fitness_profile"] = (
            "User has not completed fitness profile."
        )

    # ==========================================================
    # RECENT WORKOUTS
    # ==============================================================

    workouts = Workout.objects.filter(
        user=user
    ).order_by('-created_at')[:5]

    workout_list = []

    for item in workouts:

        workout_list.append({

            "exercise": getattr(
                item,
                'workout_name',
                'Unknown'
            ),

            "category": getattr(
                item,
                'workout_category',
                'Unknown'
            ),

            "date": str(
                item.workout_date
            ),

            "completed": item.is_completed,

            "completed_reps": getattr(
                item,
                'completed_reps',
                0
            ),

            "target_reps": getattr(
                item,
                'target_reps',
                0
            ),

            "form_status": getattr(
                item,
                'form_status',
                'Not available'
            ),

        })

    context["recent_workouts"] = workout_list

    # ==========================================================
    # TODAY'S DIET
    # ==============================================================

    context["today_diet"] = get_today_diet_meals(
        user,
        today
    )

    # ==========================================================
    # NUTRITION TARGETS
    # ==============================================================

    nutrition = NutritionGoal.objects.filter(
        user=user
    ).first()

    if nutrition:

        context["nutrition_targets"] = {

            "protein_target": getattr(
                nutrition,
                'protein_target',
                None
            ),

            "water_target": getattr(
                nutrition,
                'water_target',
                None
            ),

            "calories_target": getattr(
                nutrition,
                'calories_target',
                None
            ),

            "carbs_target": getattr(
                nutrition,
                'carbs_target',
                None
            ),

            "fat_target": getattr(
                nutrition,
                'fat_target',
                None
            ),

        }

    else:

        context["nutrition_targets"] = (
            "Nutrition targets not configured."
        )

    # ==========================================================
    # TODAY'S CONSUMED NUTRITION
    # ==============================================================

    food_data = FoodScan.objects.filter(
        user=user,
        is_consumed=True,
        scan_date__gte=today_start,
        scan_date__lt=tomorrow_start
    ).aggregate(

        total_protein=Sum('protein'),

        total_calories=Sum('calories'),

        total_carbs=Sum('carbohydrates'),

        total_fats=Sum('fats'),

        total_fiber=Sum('fiber')

    )

    context["today_nutrition"] = {

        "protein": food_data["total_protein"] or 0,

        "calories": food_data["total_calories"] or 0,

        "carbohydrates": food_data["total_carbs"] or 0,

        "fats": food_data["total_fats"] or 0,

        "fiber": food_data["total_fiber"] or 0,

    }

    context["today_protein_consumed"] = (
        food_data["total_protein"] or 0
    )

    # ==========================================================
    # WATER INTAKE
    # ==============================================================

    water = WaterIntake.objects.filter(
        user=user,
        date=today
    ).first()

    context["today_water_intake"] = (
        water.water_amount if water else 0
    )

    # ==========================================================
    # TODAY'S PROGRESS
    # ==============================================================

    progress = DailyProgress.objects.filter(
        user=user,
        date=today
    ).first()

    if progress:

        context["today_progress"] = {

            "steps": progress.steps,

            "steps_goal": progress.steps_goal,

            "active_minutes": progress.active_minutes,

            "distance_km": progress.distance_km,

            "activity_calories": progress.activity_calories,

        }

    else:

        context["today_progress"] = {

            "steps": 0,

            "steps_goal": 8000,

            "active_minutes": 0,

            "distance_km": 0,

            "activity_calories": 0,

        }

    # ==========================================================
    # TODAY'S COMPLETED WORKOUTS
    # ==============================================================

    context["today_completed_workouts"] = Workout.objects.filter(

        user=user,

        is_completed=True,

        completed_at__gte=today_start,

        completed_at__lt=tomorrow_start

    ).count()

    return context


# ==============================================================
# 4. FITNESS KNOWLEDGE BASE
# ==============================================================

FITNESS_KNOWLEDGE = [

    {
        "topic": "weight_loss",
        "keywords": [
            "weight loss",
            "lose weight",
            "fat loss",
            "cutting",
            "belly fat"
        ],
        "content": """
        Weight management should use a sustainable calorie
        deficit, resistance training, regular physical activity,
        adequate protein and sufficient sleep.
        Spot reduction of belly fat is not possible.
        """
    },

    {
        "topic": "muscle_gain",
        "keywords": [
            "muscle gain",
            "bulking",
            "build muscle",
            "strength",
            "hypertrophy"
        ],
        "content": """
        Muscle development requires progressive resistance
        training, adequate nutrition, sufficient protein,
        proper recovery and consistent sleep.
        Increase training loads gradually.
        """
    },

    {
        "topic": "protein",
        "keywords": [
            "protein",
            "eggs",
            "chicken",
            "paneer",
            "whey",
            "muscle recovery"
        ],
        "content": """
        Protein supports muscle repair and growth.
        Sources include eggs, milk, curd, paneer, chicken,
        fish, pulses, beans and whey protein.
        Requirements depend on body weight and goals.
        """
    },

    {
        "topic": "workout",
        "keywords": [
            "workout",
            "exercise",
            "gym",
            "chest",
            "back",
            "legs",
            "shoulder",
            "arms",
            "biceps",
            "triceps"
        ],
        "content": """
        A balanced workout should train major muscle groups,
        include suitable recovery days, use progressive overload
        and consider the person's training experience.
        Correct exercise technique is important.
        """
    },

    {
        "topic": "bmi",
        "keywords": [
            "bmi",
            "body mass index",
            "height",
            "weight"
        ],
        "content": """
        BMI is calculated as weight in kilograms divided by
        height in metres squared. Adult BMI categories are
        screening tools and do not directly measure body fat
        or distinguish muscle from fat.
        """
    },

    {
        "topic": "hydration",
        "keywords": [
            "water",
            "hydration",
            "drink water"
        ],
        "content": """
        Hydration needs vary with activity, climate, body size
        and health. Water intake should be adjusted to
        individual needs and exercise conditions.
        """
    },

    {
        "topic": "diet",
        "keywords": [
            "diet",
            "food",
            "meal",
            "nutrition",
            "calories",
            "carbohydrates",
            "fat"
        ],
        "content": """
        A balanced diet includes protein, carbohydrates,
        healthy fats, vegetables, fruits and adequate fluids.
        Food portions and calorie intake should match
        individual goals and activity levels.
        """
    }

]


# ==============================================================
# 5. NLP + KNOWLEDGE RETRIEVAL
# ==============================================================

def retrieve_fitness_knowledge(message):

    message = message.lower()

    retrieved_documents = []

    for document in FITNESS_KNOWLEDGE:

        for keyword in document["keywords"]:

            if keyword in message:

                retrieved_documents.append({

                    "topic": document["topic"],

                    "content": document["content"]

                })

                break

    return retrieved_documents


# ==============================================================
# 6. CHATBOT PAGE
# ==============================================================

@login_required
@ensure_csrf_cookie
def chat_page(request):

    return render(
        request,
        "chatbot/chat.html"
    )


# ==============================================================
# 7. AI CHATBOT API
# ==============================================================

@login_required
@require_POST
def chat_api(request):

    try:

        data = json.loads(
            request.body.decode("utf-8")
        )

        message = data.get(
            "message",
            ""
        ).strip()

        if not message:

            return JsonResponse({

                "error": "Please enter a message."

            }, status=400)

        if len(message) > 2000:

            return JsonResponse({

                "error": "Message is too long."

            }, status=400)

        # GET USER FITNESS DATA

        user_context = get_user_fitness_context(
            request.user
        )

        # RETRIEVE RELEVANT KNOWLEDGE

        retrieved_knowledge = retrieve_fitness_knowledge(
            message
        )

        knowledge_text = json.dumps(
            retrieved_knowledge,
            indent=2
        )

        if not retrieved_knowledge:

            knowledge_text = (
                "No directly matching fitness knowledge found."
            )

        # AI SYSTEM PROMPT

        system_prompt = f"""
        You are FitAI, a personalized AI fitness assistant.

        YOUR RESPONSIBILITIES:

        1. Recommend personalized workouts.
        2. Explain BMI.
        3. Recommend diet and nutrition.
        4. Analyze workout history.
        5. Explain protein and calorie requirements.
        6. Give fitness progress suggestions.
        7. Help users achieve their fitness goals.

        IMPORTANT INSTRUCTIONS:

        - Use the actual user's fitness information.
        - Consider weight, height, BMI, age and fitness goal.
        - Consider previous workouts.
        - Consider available diet information.
        - Do not invent missing information.
        - Give beginner-friendly explanations.
        - Recommend realistic workouts.
        - Explain sets, repetitions and rest periods.
        - Never recommend extreme dieting.
        - Do not diagnose medical conditions.
        - Ask questions if important information is missing.

        USER FITNESS INFORMATION:

        {json.dumps(user_context, indent=2, default=str)}

        RETRIEVED FITNESS KNOWLEDGE:

        {knowledge_text}

        Always provide clear, structured and helpful answers.
        """

        # GET CHAT HISTORY

        history = request.session.get(
            "fitai_chat_history",
            []
        )

        chat_messages = [

            {
                "role": "system",
                "content": system_prompt
            }

        ]

        for item in history[-10:]:

            if item.get("role") in [
                "user",
                "assistant"
            ]:

                chat_messages.append({

                    "role": item["role"],

                    "content": item["content"]

                })

        # ADD CURRENT MESSAGE

        chat_messages.append({

            "role": "user",

            "content": message

        })

        # CONNECT TO OLLAMA

        ollama_response = requests.post(

            "http://localhost:11434/api/chat",

            json={

                "model": "llama3.2",

                "messages": chat_messages,

                "stream": False

            },

            timeout=120

        )

        ollama_response.raise_for_status()

        result = ollama_response.json()

        ai_reply = result["message"]["content"]

        # SAVE CHAT HISTORY

        history.append({

            "role": "user",

            "content": message

        })

        history.append({

            "role": "assistant",

            "content": ai_reply

        })

        request.session["fitai_chat_history"] = history[-10:]

        request.session.modified = True

        return JsonResponse({

            "success": True,

            "reply": ai_reply

        })

    except json.JSONDecodeError:

        return JsonResponse({

            "error": "Invalid message format."

        }, status=400)

    except requests.exceptions.ConnectionError:

        return JsonResponse({

            "error": (
                "Ollama is not running. "
                "Please start Ollama first."
            )

        }, status=503)

    except requests.exceptions.Timeout:

        return JsonResponse({

            "error": (
                "AI response timed out. Please try again."
            )

        }, status=504)

    except requests.exceptions.RequestException as error:

        print("OLLAMA ERROR:", str(error))

        return JsonResponse({

            "error": "Unable to connect to the AI model."

        }, status=502)

    except Exception as error:

        print("FITAI CHAT ERROR:", str(error))

        return JsonResponse({

            "error": "Something went wrong. Please try again."

        }, status=500)


# ==============================================================
# 8. CLEAR CHAT HISTORY
# ==============================================================

@login_required
@require_POST
def clear_chat(request):

    request.session.pop(
        "fitai_chat_history",
        None
    )

    return JsonResponse({

        "success": True,

        "message": "Chat history cleared."

    })
