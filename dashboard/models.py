from django.db import models
from django.contrib.auth.models import User


class Dashboard(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    # Daily Progress

    calories_burned = models.IntegerField(
        default=0
    )

    calories_consumed = models.IntegerField(
        default=0
    )

    protein_consumed = models.FloatField(
        default=0
    )

    protein_target = models.FloatField(
        default=0
    )

    carbs_consumed = models.FloatField(
        default=0
    )

    carbs_target = models.FloatField(
        default=0
    )

    fats_consumed = models.FloatField(
        default=0
    )

    fats_target = models.FloatField(
        default=0
    )


    # Water Tracking

    water_intake = models.FloatField(
        default=0,
        help_text="Litres"
    )

    water_target = models.FloatField(
        default=3,
        help_text="Daily water target in litres"
    )


    # Workout Tracking

    total_workout_time = models.IntegerField(
        default=0,
        help_text="Minutes"
    )

    workouts_completed = models.IntegerField(
        default=0
    )


    # AI Workout Performance

    correct_reps = models.IntegerField(
        default=0
    )

    incorrect_reps = models.IntegerField(
        default=0
    )

    posture_score = models.FloatField(
        default=0
    )


    # Date

    updated_date = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):
        return self.user.username + " Dashboard"

# Create your models here.
