from django.contrib import admin
from .models import Workout


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):

    list_display = (
        'workout_name',
        'user',
        'workout_category',
        'difficulty_level',
        'duration',
        'calories_burned',
        'completed_reps',
        'target_reps',
        'form_status',
        'is_completed',
        'workout_date'
    )

    list_filter = (
        'workout_category',
        'difficulty_level',
        'form_status',
        'is_completed',
        'workout_date'
    )

    search_fields = (
        'workout_name',
        'user__username'
    )

    readonly_fields = (
        'workout_date',
        'created_at'
    )

    fieldsets = (

        ("User Information", {
            "fields": (
                "user",
            )
        }),

        ("Workout Information", {
            "fields": (
                "workout_name",
                "description",
                "workout_category",
                "difficulty_level",
                "equipment_required"
            )
        }),

        ("Workout Target & Progress", {
            "fields": (
                "target_sets",
                "target_reps",
                "completed_sets",
                "completed_reps",
                "is_completed"
            )
        }),

        ("Calories & Duration", {
            "fields": (
                "duration",
                "calories_burned"
            )
        }),

        ("AI Fitness Analysis", {
            "fields": (
                "exercise_image",
                "form_status",
                "ai_feedback"
            )
        }),

        ("Dates", {
            "fields": (
                "workout_date",
                "created_at"
            )
        }),
    )