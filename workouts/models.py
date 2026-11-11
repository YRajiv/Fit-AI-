from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Workout(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    # Workout Basic Information
    workout_name = models.CharField(max_length=100)

    description = models.TextField(blank=True)

    workout_category = models.CharField(
        max_length=50,
        choices=[
            ("Strength", "Strength"),
            ("Cardio", "Cardio"),
            ("Yoga", "Yoga"),
            ("HIIT", "HIIT"),
            ("Flexibility", "Flexibility")
        ]
    )

    # Exercise Details
    target_sets = models.IntegerField(default=3)

    target_reps = models.IntegerField(default=10)

    completed_reps = models.IntegerField(default=0)

    completed_sets = models.IntegerField(default=0)

    # Time and Calories
    duration = models.IntegerField(
        help_text="Workout duration in minutes"
    )

    calories_burned = models.IntegerField(default=0)

    # Difficulty
    difficulty_level = models.CharField(
        max_length=50,
        choices=[
            ("Beginner", "Beginner"),
            ("Intermediate", "Intermediate"),
            ("Advanced", "Advanced")
        ]
    )

    # Equipment
    equipment_required = models.CharField(
        max_length=100,
        blank=True
    )

    # AI Workout Features
    exercise_image = models.ImageField(
        upload_to="workout_images/",
        blank=True,
        null=True
    )

    form_status = models.CharField(
        max_length=50,
        default="Not Checked",
        choices=[
            ("Good Form", "Good Form"),
            ("Needs Improvement", "Needs Improvement"),
            ("Not Checked", "Not Checked")
        ]
    )

    ai_feedback = models.TextField(blank=True)

    # Workout Progress
    is_completed = models.BooleanField(default=False)

    workout_date = models.DateField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)

    started_at = models.DateTimeField(default=timezone.now)

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.workout_name