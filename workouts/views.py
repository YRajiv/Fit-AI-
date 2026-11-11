
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
from math import isfinite

from .models import Workout
from diet.models import UserFitnessProfile
from progress.models import DailyProgress


# ============================================================
# EXERCISE LIBRARY
# ============================================================

EXERCISES = [

    # ========================================================
    # BEGINNER - NO EQUIPMENT
    # ========================================================

    {
        "name": "Push-ups",
        "muscle": "Chest",
        "category": "Strength",
        "equipment": "No Equipment",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 8,
        "goals": ["muscle_gain", "weight_loss", "general_fitness", "strength"],
        "video": "https://media.istockphoto.com/id/1693837942/video/muscular-man-character-training-chest-bodyweight-push-up-workout-3d-render.mp4?s=mp4-640x640-is&k=20&c=PfAcwNKU3LE52ZsJQIROK5-1zFrNzW_n7_ravXRzAuQ="
    },

    {
        "name": "Bodyweight Squats",
        "muscle": "Legs",
        "category": "Strength",
        "equipment": "No Equipment",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 12,
        "goals": ["muscle_gain", "weight_loss", "general_fitness", "strength"],
        "video": "https://media.istockphoto.com/id/1692419791/video/illustration-design-of-muscular-man-doing-squat-training.mp4?s=mp4-640x640-is&k=20&c=ub3lIV6F0l86Hlqb9P4HhKlsehsysPy2mOIlZabushg="
    },

    {
        "name": "Glute Bridges",
        "muscle": "Glutes",
        "category": "Strength",
        "equipment": "No Equipment",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 12,
        "goals": ["muscle_gain", "general_fitness", "strength"],
        "video": "https://media.istockphoto.com/id/1557721251/video/bridge-pose-setu-bandhasana-fitness-exercise-workout-animation-male-muscle-highlight.mp4?s=mp4-640x640-is&k=20&c=gnrOyc44lqisuXYnnP0nrS5SiW-_zP-V2n4Ra2fOdTo="
    },

    {
        "name": "Plank",
        "muscle": "Abs",
        "category": "Strength",
        "equipment": "No Equipment",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 20,
        "goals": ["weight_loss", "general_fitness", "strength"],
        "video": "https://media.istockphoto.com/id/1454352252/video/plank-on-elbows-fitness-exercise-workout-animation-male-muscle-highlight-demonstration-at-4k.mp4?s=mp4-640x640-is&k=20&c=y64hmxgrZSxmO8ZXiALLFwggwoE92IbvdxobcqkeILs="
    },

    {
        "name": "Jumping Jacks",
        "muscle": "Full Body",
        "category": "Cardio",
        "equipment": "No Equipment",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 20,
        "goals": ["weight_loss", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1192453043/video/fat-man-morphing-into-muscular-fit-doing-jumping-jacks-seamless-loop-luma-matte-attached.mp4?s=mp4-640x640-is&k=20&c=Xfk0KvFvvFFAh6XUz_AZR-WgKAegqRonNwXmkWCA-QA="
    },

    {
        "name": "Reverse Lunges",
        "muscle": "Legs",
        "category": "Strength",
        "equipment": "No Equipment",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 10,
        "goals": ["muscle_gain", "weight_loss", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1557755244/video/bodyweight-rear-lunge-fitness-exercise-workout-animation-male-muscle-highlight-demonstration.mp4?s=mp4-640x640-is&k=20&c=fNdsXyUrkMfzkZcycu7qrzlLVOV9sMxycXfe2aWqdZU="
    },


    # ========================================================
    # BEGINNER - DUMBBELLS
    # ========================================================

    {
        "name": "Dumbbell Bicep Curls",
        "muscle": "Biceps",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 12,
        "goals": ["muscle_gain", "strength", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1552990470/video/dumbbell-close-grip-simultaneous-curl-fitness-exercise-workout-animation-male-muscle.mp4?s=mp4-640x640-is&k=20&c=oppVCasy6PvNkzIE67KLBMI7_sI9cvi7YVEWV_exFGg="
    },

    {
        "name": "Dumbbell Shoulder Press",
        "muscle": "Shoulders",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 10,
        "goals": ["muscle_gain", "strength", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1558058513/video/standing-shoulder-press-dumbbell-fitness-exercise-workout-animation-male-muscle-highlight.mp4?s=mp4-640x640-is&k=20&c=bTx362cSW9jE5E4Vws82vHFZHKpjPkOhYK483tDu9lg="
    },

    {
        "name": "Dumbbell Goblet Squats",
        "muscle": "Legs",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 12,
        "goals": ["muscle_gain", "weight_loss", "general_fitness", "strength"],
        "video": "https://media.istockphoto.com/id/1199715115/video/sportsman-exercising-with-dumbbells.mp4?s=mp4-640x640-is&k=20&c=qhy6_6L9tWyYQ1yMwkg3hqel8pBlXFjRcmlr0oipeWo="
    },

    {
        "name": "Dumbbell Floor Press",
        "muscle": "Chest",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 10,
        "goals": ["muscle_gain", "strength", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1557688094/video/dumbbell-floor-fly-fitness-exercise-workout-animation-male-muscle-highlight-demonstration-at.mp4?s=mp4-640x640-is&k=20&c=EfI_C9Ft-_4LPbGCYxuBYV2w1pKwM-hs1SJbCvcooNw="
    },

    {
        "name": "Dumbbell Lateral Raises",
        "muscle": "Shoulders",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 12,
        "goals": ["muscle_gain", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1639439885/video/3d-illustration-of-a-character-exercising-shoulders-kettlebell-long-lever-lateral-raise.mp4?s=mp4-640x640-is&k=20&c=ArAd7ubmUWmsxktlQL7_jx28hmWa20ZXozT6KUzlkxY="
    },

    {
        "name": "Dumbbell Bent Over Rows",
        "muscle": "Back",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Beginner",
        "sets": 2,
        "reps": 12,
        "goals": ["muscle_gain", "strength", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1521899799/video/dumbbell-bent-over-reverse-row-fitness-exercise-workout-animation-male-muscle-highlight.mp4?s=mp4-640x640-is&k=20&c=xmm0QWN5NPBjk4by3fQntbxp7y6ZxxS8MAgCg-iH0pM="
    },


    # ========================================================
    # INTERMEDIATE - DUMBBELLS
    # ========================================================

    {
        "name": "Dumbbell Shoulder Press",
        "muscle": "Shoulders",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Intermediate",
        "sets": 3,
        "reps": 10,
        "goals": ["muscle_gain", "strength", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1557684644/video/dumbbell-chest-press-incline-bench-fitness-exercise-workout-animation-male-muscle-highlight.mp4?s=mp4-640x640-is&k=20&c=Kc3ONNP_gKRbgbHT_JljucFXFigXjn-0X_geubW7OPw="
    },

    {
        "name": "Dumbbell Rows",
        "muscle": "Back",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Intermediate",
        "sets": 3,
        "reps": 10,
        "goals": ["muscle_gain", "strength", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1558048497/video/dumbbell-rear-delt-row-fitness-exercise-workout-animation-male-muscle-highlight-demonstration.mp4?s=mp4-640x640-is&k=20&c=_YURx8WDGISszc1UIlr1bNlZ_WZZgaC51zTQHHTQczE="
    },

    {
        "name": "Dumbbell Bicep Curls",
        "muscle": "Biceps",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Intermediate",
        "sets": 3,
        "reps": 12,
        "goals": ["muscle_gain", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1552990470/video/dumbbell-close-grip-simultaneous-curl-fitness-exercise-workout-animation-male-muscle.mp4?s=mp4-640x640-is&k=20&c=oppVCasy6PvNkzIE67KLBMI7_sI9cvi7YVEWV_exFGg="
    },

    {
        "name": "Dumbbell Lunges",
        "muscle": "Legs",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Intermediate",
        "sets": 3,
        "reps": 10,
        "goals": ["muscle_gain", "strength", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1557782491/video/dumbbell-single-leg-split-squat-fitness-exercise-workout-animation-male-muscle-highlight.mp4?s=mp4-640x640-is&k=20&c=UXQ1gf06leYOwrBHHaYsKTdOIA4mZS-w9tICOsISSY4="
    },

    {
        "name": "Dumbbell Lateral Raises",
        "muscle": "Shoulders",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Intermediate",
        "sets": 3,
        "reps": 12,
        "goals": ["muscle_gain", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1558065600/video/lateral-raises-dumbbell-fitness-exercise-workout-animation-male-muscle-highlight.mp4?s=mp4-640x640-is&k=20&c=Mol3VE0PGl9pYB5muR2-4JMaoLzk6ian9oOhwzbgp3g="
    },

    {
        "name": "Dumbbell Romanian Deadlift",
        "muscle": "Hamstrings",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Intermediate",
        "sets": 3,
        "reps": 10,
        "goals": ["muscle_gain", "strength", "general_fitness"],
        "video": "https://media.istockphoto.com/id/2262170333/video/dumbell-romanian-deadlift-muscles-worked-anatomy-2.mp4?s=mp4-640x640-is&k=20&c=zckW7dP2vn59P0sySumghi1UuFoX8CPsYPnvRfWa2XY="
    },

    {
        "name": "Dumbbell Chest Press",
        "muscle": "Chest",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Intermediate",
        "sets": 3,
        "reps": 10,
        "goals": ["muscle_gain", "strength", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1557680175/video/dumbbell-alternate-bench-press-high-start-fitness-exercise-workout-animation-male-muscle.mp4?s=mp4-640x640-is&k=20&c=uTaKL88TpJ3nJdDQZHGjxjeOYFcsnX28MqvU2UfGWys="
    },

    {
        "name": "Dumbbell Hammer Curls",
        "muscle": "Biceps",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Intermediate",
        "sets": 3,
        "reps": 12,
        "goals": ["muscle_gain", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1553022926/video/hammer-curl-dumbbells-simultaneous-fitness-exercise-workout-animation-male-muscle-highlight.mp4?s=mp4-640x640-is&k=20&c=dmRLPxUY63a6rqPs3sC2Xh4O9_OfqD5CQisSzkj2P4c="
    },


    # ========================================================
    # INTERMEDIATE - NO EQUIPMENT
    # ========================================================

    {
        "name": "Mountain Climbers",
        "muscle": "Full Body",
        "category": "Cardio",
        "equipment": "No Equipment",
        "difficulty": "Intermediate",
        "sets": 3,
        "reps": 20,
        "goals": ["weight_loss", "general_fitness"],
        "video": None
    },


    # ========================================================
    # ADVANCED - DUMBBELLS
    # ========================================================

    {
        "name": "Dumbbell Romanian Deadlift",
        "muscle": "Hamstrings",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Advanced",
        "sets": 4,
        "reps": 10,
        "goals": ["muscle_gain", "strength"],
        "video": "https://media.istockphoto.com/id/2262170333/video/dumbell-romanian-deadlift-muscles-worked-anatomy-2.mp4?s=mp4-640x640-is&k=20&c=zckW7dP2vn59P0sySumghi1UuFoX8CPsYPnvRfWa2XY="
    },

    {
        "name": "Dumbbell Chest Press",
        "muscle": "Chest",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Advanced",
        "sets": 4,
        "reps": 10,
        "goals": ["muscle_gain", "strength"],
        "video": "https://media.istockphoto.com/id/1557680175/video/dumbbell-alternate-bench-press-high-start-fitness-exercise-workout-animation-male-muscle.mp4?s=mp4-640x640-is&k=20&c=uTaKL88TpJ3nJdDQZHGjxjeOYFcsnX28MqvU2UfGWys="
    },

    {
        "name": "Dumbbell Bulgarian Split Squats",
        "muscle": "Legs",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Advanced",
        "sets": 3,
        "reps": 10,
        "goals": ["muscle_gain", "strength"],
        "video": "https://media.istockphoto.com/id/1557750790/video/dumbbell-bulgarian-split-squat-fitness-exercise-workout-animation-male-muscle-highlight.mp4?s=mp4-640x640-is&k=20&c=usQOYce8-DyKnb8uZ9jNJ3C9FknFVL4imbYobs39WJw="
    },

    {
        "name": "Dumbbell Bent Over Rows",
        "muscle": "Back",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Advanced",
        "sets": 4,
        "reps": 10,
        "goals": ["muscle_gain", "strength"],
        "video": "https://media.istockphoto.com/id/1521899799/video/dumbbell-bent-over-reverse-row-fitness-exercise-workout-animation-male-muscle-highlight.mp4?s=mp4-640x640-is&k=20&c=xmm0QWN5NPBjk4by3fQntbxp7y6ZxxS8MAgCg-iH0pM="
    },

    {
        "name": "Dumbbell Arnold Press",
        "muscle": "Shoulders",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Advanced",
        "sets": 4,
        "reps": 10,
        "goals": ["muscle_gain", "strength"],
        "video": "https://media.istockphoto.com/id/1557791606/video/arnold-press-dumbbell-fitness-exercise-workout-animation-male-muscle-highlight-demonstration.mp4?s=mp4-640x640-is&k=20&c=__vXfIPN-UkKcDXziF86q_Jb9Yw_oapzxXHuhLxlKZk="
    },

    {
        "name": "Dumbbell Walking Lunges",
        "muscle": "Legs",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Advanced",
        "sets": 3,
        "reps": 12,
        "goals": ["muscle_gain", "strength"],
        "video": "https://media.istockphoto.com/id/1327346083/video/male-athlete-uses-kettlebells-in-cross-training-gym.mp4?s=mp4-640x640-is&k=20&c=xkZP52u3M28bjS5eeralaaY-izIbLJ5_doiVhceTWdg="
    },

    {
        "name": "Dumbbell Hammer Curls",
        "muscle": "Biceps",
        "category": "Strength",
        "equipment": "Dumbbells",
        "difficulty": "Advanced",
        "sets": 4,
        "reps": 10,
        "goals": ["muscle_gain", "strength"],
        "video": "https://media.istockphoto.com/id/1553022926/video/hammer-curl-dumbbells-simultaneous-fitness-exercise-workout-animation-male-muscle-highlight.mp4?s=mp4-640x640-is&k=20&c=dmRLPxUY63a6rqPs3sC2Xh4O9_OfqD5CQisSzkj2P4c="
    },


    # ========================================================
    # ADVANCED - FULL GYM
    # ========================================================

    {
        "name": "Barbell Squats",
        "muscle": "Legs",
        "category": "Strength",
        "equipment": "Full Gym",
        "difficulty": "Advanced",
        "sets": 4,
        "reps": 8,
        "goals": ["muscle_gain", "strength"],
        "video": "https://media.istockphoto.com/id/1709530016/video/3d-of-muscular-character-training-quads-barbell-high-bar-squat-on-isolated-white-background.mp4?s=mp4-640x640-is&k=20&c=X6RZ1F5xJ3YO5Lra8bMkHqCgf0hHQrAdNsoZt9igpdI="
    },

    {
        "name": "Barbell Bench Press",
        "muscle": "Chest",
        "category": "Strength",
        "equipment": "Full Gym",
        "difficulty": "Advanced",
        "sets": 4,
        "reps": 8,
        "goals": ["muscle_gain", "strength"],
        "video": "https://media.istockphoto.com/id/480371030/video/male-working-out-on-decline-bench-loop-able-with-alpha-channel.mp4?s=mp4-640x640-is&k=20&c=80FslXQRg5eTeVgsghhws-ZAWWXZshbot7M1Qf_807Q="
    },

    {
        "name": "Deadlifts",
        "muscle": "Back",
        "category": "Strength",
        "equipment": "Full Gym",
        "difficulty": "Advanced",
        "sets": 3,
        "reps": 6,
        "goals": ["muscle_gain", "strength"],
        "video": "https://media.istockphoto.com/id/2262164871/video/barbell-romanian-deadlift-muscles-worked-anatomy.mp4?s=mp4-640x640-is&k=20&c=hP06034tr-8pdidKhUj7m2oVY6K1WY7Z18j6GITsBDE="
    },

    {
        "name": "Cable Chest Fly",
        "muscle": "Chest",
        "category": "Strength",
        "equipment": "Full Gym",
        "difficulty": "Advanced",
        "sets": 3,
        "reps": 12,
        "goals": ["muscle_gain", "general_fitness"],
        "video": "https://media.istockphoto.com/id/1711159995/video/3d-illustration-of-a-muscular-man-practicing-chest-cable-pec-fly-gym-workout-fit.mp4?s=mp4-640x640-is&k=20&c=ENbu8mriD3EGgm-cYqEF7aeViyfMmzASwATIu6JWzAc="
    },


    # ========================================================
    # ADVANCED - NO EQUIPMENT
    # ========================================================

    {
        "name": "Burpees",
        "muscle": "Full Body",
        "category": "HIIT",
        "equipment": "No Equipment",
        "difficulty": "Advanced",
        "sets": 3,
        "reps": 15,
        "goals": ["weight_loss", "general_fitness"],
        "video": "https://media.istockphoto.com/id/478074290/video/man-doing-his-workout-in-gym.mp4?s=mp4-640x640-is&k=20&c=-Qu9AI25IkpIfZLEyzdE2K00ygE3z3tdJD7-2wPKLWQ="
    },
]


# ============================================================
# EXERCISE VIDEO SETUP
# ============================================================

for exercise in EXERCISES:

    if "video" not in exercise:
        exercise["video"] = None

    exercise["video_id"] = None
    exercise["video_start"] = 0


# ============================================================
# PERSONALIZED RECOMMENDATION ENGINE
# ============================================================

def recommend_workout(profile, user):

    level_order = {
        "Beginner": 1,
        "Intermediate": 2,
        "Advanced": 3
    }

    user_level = level_order.get(
        profile.fitness_level,
        1
    )

    goal = profile.goal
    equipment = profile.equipment

    recent_workouts = Workout.objects.filter(
        user=user,
        is_completed=True
    ).order_by("-completed_at", "-created_at")[:3]

    recent_categories = []

    for workout in recent_workouts:
        recent_categories.append(
            workout.workout_category
        )

    recommended_exercises = []

    for exercise in EXERCISES:

        exercise_level = level_order.get(
            exercise["difficulty"],
            1
        )

        if goal not in exercise["goals"]:
            continue

        if exercise_level > user_level:
            continue

        if exercise["equipment"] != equipment:
            continue

        exercise_data = exercise.copy()

        recommended_exercises.append(
            exercise_data
        )

    # PREFER DIFFERENT CATEGORIES

    if recent_categories and len(recommended_exercises) > 1:

        alternative_exercises = []

        for exercise in recommended_exercises:

            if exercise["category"] not in recent_categories:
                alternative_exercises.append(exercise)

        if len(alternative_exercises) >= 3:
            recommended_exercises = alternative_exercises

    # LIMIT EXERCISES ACCORDING TO DURATION

    duration = profile.workout_duration

    if duration <= 20:
        exercise_limit = 3

    elif duration <= 40:
        exercise_limit = 5

    else:
        exercise_limit = 7

    recommended_exercises = recommended_exercises[
        :exercise_limit
    ]

    # ADJUST SETS

    for exercise in recommended_exercises:

        if profile.fitness_level == "Beginner":
            exercise["sets"] = 2

        elif profile.fitness_level == "Intermediate":
            exercise["sets"] = 3

        else:
            exercise["sets"] = 4

    # FIND MOST COMMON CATEGORY

    category_counts = {}

    for exercise in recommended_exercises:

        category = exercise["category"]

        if category not in category_counts:
            category_counts[category] = 0

        category_counts[category] += 1

    if category_counts:

        recommended_category = max(
            category_counts,
            key=category_counts.get
        )

    else:
        recommended_category = "Strength"

    # WORKOUT TITLES

    goal_names = {
        "muscle_gain": "Muscle Building",
        "weight_loss": "Fat Burning",
        "general_fitness": "Full Body Fitness",
        "strength": "Strength Training"
    }

    goal_name = goal_names.get(
        goal,
        "Personalized Fitness"
    )

    recommended_name = (
        f"{profile.fitness_level} {goal_name} Workout"
    )

    return {

        "name": recommended_name,

        "category": recommended_category,

        "difficulty": profile.fitness_level,

        "duration": duration,

        "equipment": equipment,

        "exercises": recommended_exercises,

        "sets": (
            recommended_exercises[0]["sets"]
            if recommended_exercises else 0
        ),

        "reps": (
            recommended_exercises[0]["reps"]
            if recommended_exercises else 0
        ),

        "training_days": profile.training_days,

    }


# ============================================================
# WORKOUT PAGE
# ============================================================

@login_required
def workouts_view(request):

    profile = UserFitnessProfile.objects.filter(
        user=request.user
    ).first()

    recent_workouts = Workout.objects.filter(
        user=request.user
    ).order_by("-created_at")[:5]

    workout_plan = None
    form_submitted = False
    form_errors = []

    # DEFAULT FORM VALUES

    selected_fitness_level = (
        profile.fitness_level if profile else ""
    )

    selected_height = (
        profile.height_cm if profile else ""
    )

    selected_weight = (
        profile.weight_kg if profile else ""
    )

    selected_equipment = (
        profile.equipment if profile else "No Equipment"
    )

    if selected_equipment not in [
        "No Equipment",
        "Dumbbells",
        "Full Gym"
    ]:
        selected_equipment = "No Equipment"

    if selected_equipment == "No Equipment":
        selected_has_equipment = "No"
    else:
        selected_has_equipment = "Yes"

    # PROCESS FITNESS ASSESSMENT FORM

    if request.method == "POST":

        if profile is None:

            form_errors.append(
                "Please complete your fitness profile first."
            )

        else:

            fitness_level = request.POST.get(
                "fitness_level",
                ""
            ).strip()

            height_input = request.POST.get(
                "height_cm",
                ""
            ).strip()

            weight_input = request.POST.get(
                "weight_kg",
                ""
            ).strip()

            has_equipment = request.POST.get(
                "has_equipment",
                "No"
            ).strip()

            equipment = request.POST.get(
                "equipment",
                "No Equipment"
            ).strip()

            selected_fitness_level = fitness_level
            selected_height = height_input
            selected_weight = weight_input
            selected_has_equipment = has_equipment
            selected_equipment = equipment

            # VALIDATE FITNESS LEVEL

            valid_levels = [
                "Beginner",
                "Intermediate",
                "Advanced"
            ]

            if fitness_level not in valid_levels:

                form_errors.append(
                    "Please select a valid fitness level."
                )

            # VALIDATE HEIGHT

            height = None

            try:

                height = float(height_input)

                if not isfinite(height) or height < 50 or height > 250:

                    form_errors.append(
                        "Height must be between 50 and 250 cm."
                    )

            except (ValueError, TypeError):

                form_errors.append(
                    "Please enter a valid height."
                )

            # VALIDATE WEIGHT

            weight = None

            try:

                weight = float(weight_input)

                if not isfinite(weight) or weight < 10 or weight > 300:

                    form_errors.append(
                        "Weight must be between 10 and 300 kg."
                    )

            except (ValueError, TypeError):

                form_errors.append(
                    "Please enter a valid weight."
                )

            # VALIDATE EQUIPMENT AVAILABILITY

            if has_equipment not in ["Yes", "No"]:

                form_errors.append(
                    "Please select whether you have workout equipment."
                )

            if has_equipment == "No":

                equipment = "No Equipment"
                selected_equipment = "No Equipment"

            elif has_equipment == "Yes":

                valid_equipment = [
                    "Dumbbells",
                    "Full Gym"
                ]

                if equipment not in valid_equipment:

                    form_errors.append(
                        "Please select a valid equipment type."
                    )

            # SAVE PROFILE AND GENERATE WORKOUT

            if not form_errors:

                profile.fitness_level = fitness_level

                profile.height_cm = height

                profile.weight_kg = weight

                profile.equipment = equipment

                profile.save(
                    update_fields=[
                        "fitness_level",
                        "height_cm",
                        "weight_kg",
                        "equipment"
                    ]
                )

                workout_plan = recommend_workout(
                    profile,
                    request.user
                )

                form_submitted = True

    # TEMPLATE CONTEXT

    context = {

        "profile": profile,

        "profile_missing": profile is None,

        "form_submitted": form_submitted,

        "form_errors": form_errors,

        "selected_fitness_level": selected_fitness_level,

        "selected_height": selected_height,

        "selected_weight": selected_weight,

        "selected_has_equipment": selected_has_equipment,

        "selected_equipment": selected_equipment,

        "workout_plan": workout_plan,

        "recommendations": (
            workout_plan["exercises"]
            if workout_plan else []
        ),

        "recommended_name": (
            workout_plan["name"]
            if workout_plan else ""
        ),

        "recommended_category": (
            workout_plan["category"]
            if workout_plan else "Strength"
        ),

        "recommended_difficulty": (
            workout_plan["difficulty"]
            if workout_plan else ""
        ),

        "recommended_duration": (
            workout_plan["duration"]
            if workout_plan else 30
        ),

        "recommended_equipment": (
            workout_plan["equipment"]
            if workout_plan else ""
        ),

        "recommended_sets": (
            workout_plan["sets"]
            if workout_plan else 0
        ),

        "recommended_reps": (
            workout_plan["reps"]
            if workout_plan else 0
        ),

        "recommended_exercises": (
            workout_plan["exercises"]
            if workout_plan else []
        ),

        "recent_workouts": recent_workouts,

    }

    return render(
        request,
        "workouts/workouts.html",
        context
    )


# ============================================================
# START WORKOUT
# ============================================================

@login_required
@require_POST
def start_workout(request):

    try:

        profile = UserFitnessProfile.objects.get(
            user=request.user
        )

    except UserFitnessProfile.DoesNotExist:

        return JsonResponse({

            "status": "error",

            "message": "Please complete your fitness profile first."

        }, status=400)

    workout_plan = recommend_workout(
        profile,
        request.user
    )

    if not workout_plan["exercises"]:

        return JsonResponse({

            "status": "error",

            "message": (
                "No suitable exercises found. "
                "Please check your fitness level, goal and equipment."
            )

        }, status=400)

    workout_name = request.POST.get(
        "workout_name",
        ""
    ).strip()

    if workout_name != workout_plan["name"]:

        return JsonResponse({

            "status": "error",

            "message": (
                "Your workout recommendation has changed. "
                "Please refresh the page."
            )

        }, status=400)

    first_exercise = workout_plan["exercises"][0]

    workout = Workout.objects.create(

        user=request.user,

        workout_name=workout_plan["name"],

        description=(
            f"Personalized workout for {profile.fitness_level} level. "
            f"Goal: {profile.goal}. "
            f"Exercises: "
            + ", ".join(
                exercise["name"]
                for exercise in workout_plan["exercises"]
            )
        ),

        workout_category=workout_plan["category"],

        target_sets=first_exercise["sets"],

        target_reps=first_exercise["reps"],

        duration=workout_plan["duration"],

        calories_burned=0,

        difficulty_level=profile.fitness_level,

        equipment_required=profile.equipment,

        is_completed=False,

        started_at=timezone.now()

    )

    return JsonResponse({

        "status": "success",

        "message": "Your personalized workout has started!",

        "workout_id": workout.id,

        "workout_name": workout.workout_name,

        "difficulty": workout.difficulty_level,

        "duration": workout.duration,

    })


# ============================================================
# COMPLETE WORKOUT AND UPDATE DAILY PROGRESS
# ============================================================

@login_required
@require_POST
def complete_workout(request, workout_id):

    with transaction.atomic():

        # GET WORKOUT AND LOCK THE DATABASE ROW

        workout = get_object_or_404(
            Workout.objects.select_for_update(),
            id=workout_id,
            user=request.user
        )

        # PREVENT DUPLICATE COMPLETION

        if workout.is_completed:

            return JsonResponse({

                "status": "error",

                "message": "This workout is already completed."

            }, status=400)

        # MARK WORKOUT COMPLETED

        workout.is_completed = True

        workout.completed_sets = workout.target_sets

        workout.completed_reps = workout.target_reps

        workout.completed_at = timezone.now()

        workout.save()

        # GET LOCAL COMPLETION DATE

        today = timezone.localdate(
            workout.completed_at
        )

        # GET OR CREATE DAILY PROGRESS

        daily_progress, created = DailyProgress.objects.get_or_create(
            user=request.user,
            date=today
        )

        # ADD WORKOUT DURATION

        daily_progress.active_minutes += workout.duration

        # ADD RECORDED WORKOUT CALORIES

        daily_progress.activity_calories += workout.calories_burned

        # SAVE PROGRESS

        daily_progress.save()

    # RETURN SUCCESS RESPONSE

    return JsonResponse({

        "status": "success",

        "message": "Workout completed successfully!",

        "workout_id": workout.id,

        "active_minutes": daily_progress.active_minutes,

        "calories_burned": daily_progress.activity_calories

    })
