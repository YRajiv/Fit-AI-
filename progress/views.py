
import json
from math import isfinite
from datetime import timedelta

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.db.models import Sum

from .models import DailyProgress

from workouts.models import Workout
from nutrition.models import FoodScan, WaterIntake
from diet.models import UserFitnessProfile


# ============================================================
# PROGRESS PAGE
# ============================================================

@login_required
@ensure_csrf_cookie
def progress_page(request):

    user = request.user

    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    # GET OR CREATE TODAY'S PROGRESS

    daily_progress, created = DailyProgress.objects.get_or_create(
        user=user,
        date=today
    )

    # TODAY'S STEPS

    steps = daily_progress.steps
    steps_goal = daily_progress.steps_goal

    step_percentage = 0

    if steps_goal > 0:
        step_percentage = min(
            round((steps / steps_goal) * 100),
            100
        )

    # DISTANCE AND ACTIVITY CALORIES

    distance_km = daily_progress.distance_km

    activity_calories = daily_progress.activity_calories

    # WATER INTAKE

    water_record = WaterIntake.objects.filter(
        user=user,
        date=today
    ).first()

    water_intake = 0

    if water_record:
        water_intake = water_record.water_amount

    # FOOD SCANS TODAY
    # Only include food marked as consumed.

    food_records = FoodScan.objects.filter(
        user=user,
        is_consumed=True,
        scan_date__gte=today,
        scan_date__lt=tomorrow
    )

    nutrition_data = food_records.aggregate(
        total_calories=Sum('calories'),
        total_protein=Sum('protein')
    )

    calories_consumed = (
        nutrition_data['total_calories'] or 0
    )

    protein_consumed = (
        nutrition_data['total_protein'] or 0
    )

    # TODAY'S COMPLETED WORKOUTS
    # Count workouts completed today.

    workouts_today = Workout.objects.filter(
        user=user,
        is_completed=True,
        completed_at__gte=timezone.make_aware(
            timezone.datetime.combine(
                today,
                timezone.datetime.min.time()
            )
        ),
        completed_at__lt=timezone.make_aware(
            timezone.datetime.combine(
                tomorrow,
                timezone.datetime.min.time()
            )
        )
    )

    workout_count = workouts_today.count()

    # CALORIES BURNED
    # This includes estimated step calories and
    # calories recorded for completed workouts.

    calories_burned = activity_calories

    # USER FITNESS PROFILE

    profile = UserFitnessProfile.objects.filter(
        user=user
    ).first()

    weight = None
    height = None
    bmi = None

    if profile:

        weight = profile.weight_kg
        height = profile.height_cm

        if weight and height:

            height_m = float(height) / 100

            if height_m > 0:

                bmi = round(
                    float(weight) / (height_m * height_m),
                    1
                )

    # SAVE PROFILE WEIGHT IF TODAY'S WEIGHT IS EMPTY

    if weight and daily_progress.weight_kg is None:

        daily_progress.weight_kg = weight
        daily_progress.save()

    # LAST 7 DAYS

    seven_days_ago = today - timedelta(days=6)

    last_7_days = DailyProgress.objects.filter(
        user=user,
        date__gte=seven_days_ago,
        date__lte=today
    ).order_by('date')

    weekly_progress = []

    for item in last_7_days:

        weekly_progress.append({

            'date': item.date.strftime('%a'),

            'steps': item.steps,

            'distance': round(
                item.distance_km,
                2
            ),

            'active_minutes': item.active_minutes,

        })

    # LAST 30 DAYS WEIGHT HISTORY

    thirty_days_ago = today - timedelta(days=29)

    weight_history = DailyProgress.objects.filter(
        user=user,
        weight_kg__isnull=False,
        date__gte=thirty_days_ago,
        date__lte=today
    ).order_by('date')

    weight_data = []

    for item in weight_history:

        weight_data.append({

            'date': item.date.strftime('%d %b'),

            'weight': item.weight_kg

        })

    # CONTEXT

    context = {

        'daily_progress': daily_progress,

        'steps': steps,

        'steps_goal': steps_goal,

        'step_percentage': step_percentage,

        'distance_km': round(
            distance_km,
            2
        ),

        'activity_calories': round(
            activity_calories,
            1
        ),

        'active_minutes': daily_progress.active_minutes,

        'water_intake': water_intake,

        'calories_consumed': round(
            calories_consumed,
            1
        ),

        'protein_consumed': round(
            protein_consumed,
            1
        ),

        'calories_burned': round(
            calories_burned,
            1
        ),

        'workout_count': workout_count,

        'weight': weight,

        'height': height,

        'bmi': bmi,

        'weekly_progress': json.dumps(
            weekly_progress
        ),

        'weight_data': json.dumps(
            weight_data
        ),

    }

    return render(
        request,
        'progress/progress.html',
        context
    )


# ============================================================
# UPDATE STEPS
# ============================================================

@login_required
@require_POST
def update_steps(request):

    try:

        data = json.loads(
            request.body.decode('utf-8')
        )

        if not isinstance(data, dict):

            return JsonResponse({
                'success': False,
                'message': 'Invalid request data.'
            }, status=400)

        steps_increment = int(
            data.get('steps_increment', 0)
        )

        # ALLOW MANUAL STEP UPDATES
        # Sensor requests can still send small increments.

        if steps_increment < 0 or steps_increment > 100000:

            return JsonResponse({
                'success': False,
                'message': 'Enter a valid step count.'
            }, status=400)

        today = timezone.localdate()

        daily_progress, created = DailyProgress.objects.get_or_create(
            user=request.user,
            date=today
        )

        # ADD STEPS

        daily_progress.steps += steps_increment

        # ESTIMATED DISTANCE
        # Average step length: 0.7 metres.

        daily_progress.distance_km = (
            daily_progress.steps * 0.0007
        )

        # ESTIMATED STEP CALORIES

        daily_progress.activity_calories += (
            steps_increment * 0.04
        )

        daily_progress.save()

        step_percentage = 0

        if daily_progress.steps_goal > 0:

            step_percentage = min(
                round(
                    (daily_progress.steps /
                     daily_progress.steps_goal) * 100
                ),
                100
            )

        return JsonResponse({

            'success': True,

            'steps': daily_progress.steps,

            'goal': daily_progress.steps_goal,

            'step_percentage': step_percentage,

            'distance': round(
                daily_progress.distance_km,
                2
            ),

            'calories': round(
                daily_progress.activity_calories,
                1
            )

        })

    except (
        ValueError,
        TypeError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        AttributeError
    ):

        return JsonResponse({
            'success': False,
            'message': 'Invalid request data.'
        }, status=400)


# ============================================================
# UPDATE DAILY STEP GOAL
# ============================================================

@login_required
@require_POST
def update_step_goal(request):

    try:

        data = json.loads(
            request.body.decode('utf-8')
        )

        if not isinstance(data, dict):

            return JsonResponse({
                'success': False,
                'message': 'Invalid request data.'
            }, status=400)

        goal = int(
            data.get('goal', 8000)
        )

        if goal < 1000 or goal > 50000:

            return JsonResponse({
                'success': False,
                'message': 'Goal must be between 1,000 and 50,000.'
            }, status=400)

        today = timezone.localdate()

        daily_progress, created = DailyProgress.objects.get_or_create(
            user=request.user,
            date=today
        )

        daily_progress.steps_goal = goal
        daily_progress.save()

        step_percentage = 0

        if goal > 0:

            step_percentage = min(
                round(
                    (daily_progress.steps / goal) * 100
                ),
                100
            )

        return JsonResponse({

            'success': True,

            'goal': goal,

            'steps': daily_progress.steps,

            'step_percentage': step_percentage

        })

    except (
        ValueError,
        TypeError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        AttributeError
    ):

        return JsonResponse({
            'success': False,
            'message': 'Invalid goal.'
        }, status=400)


# ============================================================
# UPDATE WEIGHT
# ============================================================

@login_required
@require_POST
def update_weight(request):

    try:

        data = json.loads(
            request.body.decode('utf-8')
        )

        if not isinstance(data, dict):

            return JsonResponse({
                'success': False,
                'message': 'Invalid request data.'
            }, status=400)

        weight = float(
            data.get('weight', 0)
        )

        if not isfinite(weight) or weight < 20 or weight > 300:

            return JsonResponse({
                'success': False,
                'message': 'Enter a valid weight between 20 and 300 kg.'
            }, status=400)

        today = timezone.localdate()

        daily_progress, created = DailyProgress.objects.get_or_create(
            user=request.user,
            date=today
        )

        daily_progress.weight_kg = weight
        daily_progress.save()

        return JsonResponse({

            'success': True,

            'weight': weight,

            'message': 'Weight saved successfully.'

        })

    except (
        ValueError,
        TypeError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        AttributeError
    ):

        return JsonResponse({
            'success': False,
            'message': 'Invalid weight.'
        }, status=400)
