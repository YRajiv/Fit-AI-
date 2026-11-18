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


# -------------------------------------------------------
# Body Composition History Model
# -------------------------------------------------------
class BodyCompositionRecord(models.Model):
    """Stores a snapshot of a user's body measurements and derived metrics.
    Used for tracking progress over time and providing inputs to the
    personalized workout recommendation engine.
    """

    DATA_SOURCE_CHOICES = [
        ("manual", "Manual Measurement"),
        ("formula", "Formula Estimate"),
        ("dexa", "DEXA Report (upload)"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="body_compositions")
    measurement_date = models.DateField(default=timezone.now)

    # Raw inputs – optional where appropriate
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    waist_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    neck_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hip_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # needed for female formula
    sex = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female')], null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)

    # Derived fields – stored for quick retrieval & historical charting
    bmi = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    body_fat_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fat_mass_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    lean_body_mass_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    skeletal_muscle_mass_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    waist_to_height_ratio = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    visceral_fat_risk = models.CharField(max_length=50, null=True, blank=True)
    bmr = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    data_source = models.CharField(max_length=10, choices=DATA_SOURCE_CHOICES, default="manual")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.measurement_date}"