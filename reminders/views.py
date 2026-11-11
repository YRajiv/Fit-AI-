
import json
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Reminder
from diet.models import WeeklyDietPlan


# ============================================================
# DEFAULT MEAL REMINDER TIMES
# ============================================================

DEFAULT_REMINDERS = {
    "Breakfast": "08:00",
    "Mid-morning": "11:00",
    "Lunch": "13:00",
    "Evening Snack": "16:00",
    "Dinner": "20:00",
}


# ============================================================
# GET TODAY'S MEALS FROM DIET PLAN
# ============================================================

def get_todays_meals(user):

    today_name = timezone.localdate().strftime("%A")

    diet_plan = WeeklyDietPlan.objects.filter(
        user=user
    ).order_by("-created_at").first()

    if diet_plan is None:
        return [], today_name

    plan_data = diet_plan.plan_json

    # Convert JSON string into dictionary if necessary
    if isinstance(plan_data, str):

        try:
            plan_data = json.loads(plan_data)

        except json.JSONDecodeError:
            return [], today_name

    if not isinstance(plan_data, dict):
        return [], today_name

    # Find today's diet
    day_plan = None

    for day, value in plan_data.items():

        if str(day).lower() == today_name.lower():
            day_plan = value
            break

    if not isinstance(day_plan, dict):
        return [], today_name

    meals = day_plan.get("meals", [])

    if not isinstance(meals, list):
        return [], today_name

    today_meals = []

    for meal_data in meals:

        if not isinstance(meal_data, dict):
            continue

        today_meals.append({

            "meal": meal_data.get("meal", "Meal"),

            "food": meal_data.get(
                "food",
                "Food details unavailable"
            ),

            "ingredients": meal_data.get(
                "ingredients",
                []
            ),

            "calories": meal_data.get("calories", 0),

            "protein": meal_data.get("protein", 0),

            "carbs": meal_data.get("carbs", 0),

            "fat": meal_data.get("fat", 0),

            "fiber": meal_data.get("fiber", 0),

        })

    return today_meals, today_name


# ============================================================
# CREATE DEFAULT MEAL REMINDERS
# ============================================================

def create_default_meal_reminders(user):

    today = timezone.localdate()

    for meal_name, meal_time in DEFAULT_REMINDERS.items():

        reminder_time = datetime.strptime(
            meal_time,
            "%H:%M"
        ).time()

        Reminder.objects.get_or_create(

            user=user,

            reminder_type="Meal",

            meal_type=meal_name,

            defaults={

                "title": meal_name + " Reminder",

                "description": "Time to have your " + meal_name,

                "reminder_date": today,

                "reminder_time": reminder_time,

                "repeat": "Daily",

                "is_completed": False,

                "is_active": True,

                "notification_sent": False,

            }

        )


# ============================================================
# MEAL REMINDERS PAGE
# ============================================================

@login_required
def reminders_view(request):

    # Create default reminders for this user
    create_default_meal_reminders(request.user)

    # Save updated reminder settings
    if request.method == "POST":

        for meal_name in DEFAULT_REMINDERS:

            reminder = Reminder.objects.get(

                user=request.user,

                reminder_type="Meal",

                meal_type=meal_name

            )

            submitted_time = request.POST.get(
                "time_" + meal_name,
                ""
            )

            enabled = request.POST.get(
                "enabled_" + meal_name
            ) == "on"

            try:

                if submitted_time:

                    reminder.reminder_time = datetime.strptime(
                        submitted_time,
                        "%H:%M"
                    ).time()

                reminder.is_active = enabled

                reminder.notification_sent = False

                reminder.save()

            except ValueError:

                messages.error(
                    request,
                    "Invalid time for " + meal_name
                )

                return redirect("reminders:reminders")

        messages.success(
            request,
            "Your meal reminders have been updated successfully!"
        )

        return redirect("reminders:reminders")

    # Get meal reminders
    reminders = Reminder.objects.filter(

        user=request.user,

        reminder_type="Meal"

    ).order_by("reminder_time")

    # Get today's diet plan meals
    today_meals, today_name = get_todays_meals(
        request.user
    )

    meal_details = []

    for reminder in reminders:

        matched_food = None

        for meal in today_meals:

            if (
                meal["meal"].strip().lower()
                == reminder.meal_type.lower()
            ):

                matched_food = meal
                break

        meal_details.append({

            "id": reminder.id,

            "meal_type": reminder.meal_type,

            "title": reminder.title,

            "reminder_time": reminder.reminder_time.strftime(
                "%H:%M"
            ),

            "display_time": reminder.reminder_time.strftime(
                "%I:%M %p"
            ),

            "is_active": reminder.is_active,

            "food": matched_food,

        })

    context = {

        "reminders": meal_details,

        "today_name": today_name,

        "today_meals": today_meals,

    }

    return render(
        request,
        "reminders/reminders.html",
        context
    )

# Create your views here.
