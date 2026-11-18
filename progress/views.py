
import json
from math import isfinite, floor
from datetime import timedelta

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction

from .models import DailyProgress

from workouts.models import Workout
from nutrition.models import FoodScan, WaterIntake
from diet.models import UserFitnessProfile


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_today_progress(user):
    """
    Get or create today's progress record.
    Each user gets only one record per day.
    """

    today = timezone.localdate()

    daily_progress, created = DailyProgress.objects.get_or_create(
        user=user,
        date=today
    )

    return daily_progress


def round_half_up(value, places=2):
    """
    Round positive values in a predictable way.

    Example:
    1.085 -> 1.09
    12.5 -> 13
    """

    multiplier = 10 ** places

    return floor(float(value) * multiplier + 0.5) / multiplier


def calculate_step_percentage(steps, goal):
    """
    Calculate daily step goal percentage.
    Never return more than 100%.
    """

    if not goal or goal <= 0:
        return 0

    percentage = (steps / goal) * 100

    return min(
        round_half_up(percentage, 0),
        100
    )


def get_user_fitness_profile(user):
    """
    Return the user's fitness profile.
    """

    return UserFitnessProfile.objects.filter(
        user=user
    ).first()


def get_user_stride_length(user):
    """
    Estimate walking step length from height.

    Formula:
    Walking step length = Height x 0.415

    Height is converted from cm to metres.

    This is an estimate, not an actual measured stride.
    """

    profile = get_user_fitness_profile(user)

    if profile and profile.height_cm:

        height_cm = float(profile.height_cm)

        stride_length_m = (
            height_cm * 0.415
        ) / 100

        return stride_length_m

    # Default stride length when height is unavailable.
    return 0.70


def estimate_step_calories(user, steps):
    """
    Estimate walking calories from steps and body weight.

    Formula:
    Calories per step = Weight x 0.0006

    If body weight is unavailable:
    use approximately 0.04 calories per step.

    This is an estimate, not a medical measurement.
    """

    profile = get_user_fitness_profile(user)

    if profile and profile.weight_kg:

        weight = float(profile.weight_kg)

        calories_per_step = weight * 0.0006

    else:

        calories_per_step = 0.04

    return steps * calories_per_step


def get_step_metrics(user, daily_progress):
    """
    Calculate step-related metrics consistently
    for API responses and frontend updates.
    """

    stride_length_m = get_user_stride_length(user)

    distance_km = (
        daily_progress.steps
        * stride_length_m
        / 1000
    )

    return {
        'steps': daily_progress.steps,

        'steps_goal': daily_progress.steps_goal,

        'step_percentage': calculate_step_percentage(
            daily_progress.steps,
            daily_progress.steps_goal
        ),

        'distance_km': round_half_up(
            distance_km,
            2
        ),

        'active_minutes': daily_progress.active_minutes,

        'calories_burned': round_half_up(
            daily_progress.activity_calories,
            1
        )
    }


def get_weekly_progress(user):
    """
    Return progress for the last seven calendar days.
    """

    today = timezone.localdate()

    last_7_days = DailyProgress.objects.filter(
        user=user,
        date__gte=today - timedelta(days=6),
        date__lte=today
    ).order_by('date')

    weekly_progress = []

    for item in last_7_days:

        weekly_progress.append({

            'date': item.date.strftime('%a'),

            'full_date': item.date.strftime('%Y-%m-%d'),

            'steps': item.steps,

            'distance': round_half_up(
                item.distance_km,
                2
            ),

            'active_minutes': item.active_minutes,

            'calories': round_half_up(
                item.activity_calories,
                1
            )

        })

    return weekly_progress


def get_weight_for_user(user, daily_progress=None):
    """
    Return today's weight, or profile weight if today's
    weight has not been entered.
    """

    if daily_progress and daily_progress.weight_kg is not None:

        return daily_progress.weight_kg

    profile = get_user_fitness_profile(user)

    if profile:

        return profile.weight_kg

    return None


def calculate_bmi(weight, height):
    """
    Calculate BMI using weight in kilograms
    and height in centimetres.
    """

    if not weight or not height:

        return None

    height_m = float(height) / 100

    if height_m <= 0:

        return None

    return round(
        float(weight) / (height_m * height_m),
        1
    )


# ============================================================
# REAL-TIME PROGRESS SUMMARY API
# ============================================================

@require_GET
def progress_summary_api(request):
    """
    API used by the progress page to refresh dynamically.

    Frontend can call this API every 60 seconds.
    """

    if not request.user.is_authenticated:

        return JsonResponse({

            'success': False,

            'message': 'Authentication required.'

        }, status=401)

    user = request.user

    today = timezone.localdate()

    daily_progress = DailyProgress.objects.filter(
        user=user,
        date=today
    ).first()

    profile = get_user_fitness_profile(user)

    weight = get_weight_for_user(
        user,
        daily_progress
    )

    # If no daily progress exists, return defaults.

    if daily_progress is None:

        steps = 0

        goal = 8000

        distance = 0

        active_minutes = 0

        calories = 0

        step_percentage = 0

        last_updated = None

    else:

        metrics = get_step_metrics(
            user,
            daily_progress
        )

        steps = metrics['steps']

        goal = metrics['steps_goal']

        distance = metrics['distance_km']

        active_minutes = metrics['active_minutes']

        calories = metrics['calories_burned']

        step_percentage = metrics['step_percentage']

        last_updated = (
            daily_progress.updated_at.isoformat()
        )

    height = (
        profile.height_cm
        if profile else None
    )

    bmi = calculate_bmi(
        weight,
        height
    )

    weekly_progress = get_weekly_progress(user)

    return JsonResponse({

        'success': True,

        'date': today.strftime('%Y-%m-%d'),

        'steps': steps,

        'steps_goal': goal,

        'step_percentage': step_percentage,

        'distance_km': distance,

        'active_minutes': active_minutes,

        'calories_burned': calories,

        'weight_kg': weight,

        'height_cm': height,

        'bmi': bmi,

        'weekly_progress': weekly_progress,

        'last_updated': last_updated,

        'stride_length_m': round_half_up(
            get_user_stride_length(user),
            3
        )

    })


# ============================================================
# PROGRESS PAGE
# ============================================================

@login_required
@ensure_csrf_cookie
def progress_page(request):

    user = request.user

    today = timezone.localdate()

    tomorrow = today + timedelta(days=1)

    # --------------------------------------------------------
    # TODAY'S PROGRESS
    # --------------------------------------------------------

    daily_progress = get_today_progress(user)

    metrics = get_step_metrics(
        user,
        daily_progress
    )

    steps = metrics['steps']

    steps_goal = metrics['steps_goal']

    step_percentage = metrics['step_percentage']

    distance_km = metrics['distance_km']

    activity_calories = metrics['calories_burned']

    active_minutes = metrics['active_minutes']

    # --------------------------------------------------------
    # WATER INTAKE
    # --------------------------------------------------------

    water_record = WaterIntake.objects.filter(
        user=user,
        date=today
    ).first()

    water_intake = (
        water_record.water_amount
        if water_record else 0
    )

    # --------------------------------------------------------
    # FOOD CONSUMED TODAY
    # --------------------------------------------------------

    today_start = timezone.make_aware(
        timezone.datetime.combine(
            today,
            timezone.datetime.min.time()
        )
    )

    tomorrow_start = timezone.make_aware(
        timezone.datetime.combine(
            tomorrow,
            timezone.datetime.min.time()
        )
    )

    food_records = FoodScan.objects.filter(
        user=user,
        is_consumed=True,
        scan_date__gte=today_start,
        scan_date__lt=tomorrow_start
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

    # --------------------------------------------------------
    # COMPLETED WORKOUTS TODAY
    # --------------------------------------------------------

    workouts_today = Workout.objects.filter(
        user=user,
        is_completed=True,
        completed_at__gte=today_start,
        completed_at__lt=tomorrow_start
    )

    workout_count = workouts_today.count()

    # --------------------------------------------------------
    # USER PROFILE
    # --------------------------------------------------------

    profile = get_user_fitness_profile(user)

    weight = None

    height = None

    if profile:

        weight = profile.weight_kg

        height = profile.height_cm

    # Daily weight overrides profile weight.

    if daily_progress.weight_kg is not None:

        weight = daily_progress.weight_kg

    # --------------------------------------------------------
    # BMI
    # --------------------------------------------------------

    bmi = calculate_bmi(
        weight,
        height
    )

    # --------------------------------------------------------
    # SAVE PROFILE WEIGHT INTO TODAY'S RECORD
    # --------------------------------------------------------

    if (
        profile
        and profile.weight_kg
        and daily_progress.weight_kg is None
    ):

        daily_progress.weight_kg = profile.weight_kg

        daily_progress.save(
            update_fields=[
                'weight_kg',
                'updated_at'
            ]
        )

    # --------------------------------------------------------
    # WEEKLY PROGRESS
    # --------------------------------------------------------

    weekly_progress = get_weekly_progress(user)

    # --------------------------------------------------------
    # LAST 30 DAYS WEIGHT HISTORY
    # --------------------------------------------------------

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

            'full_date': item.date.strftime('%Y-%m-%d'),

            'weight': item.weight_kg

        })

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {

        'daily_progress': daily_progress,

        'steps': steps,

        'steps_goal': steps_goal,

        'step_percentage': step_percentage,

        'distance_km': distance_km,

        'activity_calories': activity_calories,

        'active_minutes': active_minutes,

        'water_intake': water_intake,

        'calories_consumed': round_half_up(
            calories_consumed,
            1
        ),

        'protein_consumed': round_half_up(
            protein_consumed,
            1
        ),

        'calories_burned': activity_calories,

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

        'stride_length_m': round_half_up(
            get_user_stride_length(user),
            3
        ),

    }

    return render(
        request,
        'progress/progress.html',
        context
    )


# ============================================================
# SENSOR / AUTOMATIC STEP UPDATE API
# ============================================================

@login_required
@require_POST
def update_steps(request):
    """
    Receive detected step increments from a phone sensor.

    Example JSON:

    {
        "steps_increment": 15,
        "active_minutes_increment": 0
    }

    Browser sensor detects movement.
    Django validates the data.
    Django updates today's progress.
    """

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

        active_minutes_increment = int(
            data.get('active_minutes_increment', 0)
        )

        # ----------------------------------------------------
        # VALIDATE STEP INCREMENT
        # ----------------------------------------------------

        if (
            steps_increment < 0
            or steps_increment > 100000
        ):

            return JsonResponse({

                'success': False,

                'message': 'Invalid step count.'

            }, status=400)

        # ----------------------------------------------------
        # VALIDATE ACTIVE MINUTES
        # ----------------------------------------------------

        if (
            active_minutes_increment < 0
            or active_minutes_increment > 60
        ):

            return JsonResponse({

                'success': False,

                'message': 'Invalid active minute count.'

            }, status=400)

        today = timezone.localdate()

        # ----------------------------------------------------
        # SAFE DATABASE UPDATE
        # ----------------------------------------------------

        with transaction.atomic():

            daily_progress, created = (
                DailyProgress.objects
                .select_for_update()
                .get_or_create(
                    user=request.user,
                    date=today
                )
            )

            # Add detected steps.

            daily_progress.steps += steps_increment

            # ------------------------------------------------
            # DISTANCE
            # ------------------------------------------------

            stride_length_m = get_user_stride_length(
                request.user
            )

            daily_progress.distance_km = (
                daily_progress.steps
                * stride_length_m
                / 1000
            )

            # ------------------------------------------------
            # CALORIES
            # ------------------------------------------------

            calories_increment = estimate_step_calories(
                request.user,
                steps_increment
            )

            daily_progress.activity_calories += (
                calories_increment
            )

            # ------------------------------------------------
            # ACTIVE MINUTES
            # ------------------------------------------------

            daily_progress.active_minutes += (
                active_minutes_increment
            )

            daily_progress.save()

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        metrics = get_step_metrics(
            request.user,
            daily_progress
        )

        return JsonResponse({

            'success': True,

            'steps': metrics['steps'],

            'goal': metrics['steps_goal'],

            'step_percentage': metrics['step_percentage'],

            'distance': metrics['distance_km'],

            'calories': metrics['calories_burned'],

            'active_minutes': metrics['active_minutes'],

            'last_updated': (
                daily_progress.updated_at.isoformat()
            ),

            'message': 'Progress synchronized successfully.'

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

        with transaction.atomic():

            daily_progress, created = (
                DailyProgress.objects
                .select_for_update()
                .get_or_create(
                    user=request.user,
                    date=today
                )
            )

            daily_progress.steps_goal = goal

            daily_progress.save(
                update_fields=[
                    'steps_goal',
                    'updated_at'
                ]
            )

        step_percentage = calculate_step_percentage(
            daily_progress.steps,
            goal
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

        if (
            not isfinite(weight)
            or weight < 20
            or weight > 300
        ):

            return JsonResponse({

                'success': False,

                'message': 'Enter a valid weight between 20 and 300 kg.'

            }, status=400)

        today = timezone.localdate()

        with transaction.atomic():

            daily_progress, created = (
                DailyProgress.objects
                .select_for_update()
                .get_or_create(
                    user=request.user,
                    date=today
                )
            )

            daily_progress.weight_kg = weight

            daily_progress.save(
                update_fields=[
                    'weight_kg',
                    'updated_at'
                ]
            )

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
