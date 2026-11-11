
from django.db import models
from django.contrib.auth.models import User


from django.db import models
from django.contrib.auth.models import User


class UserFitnessProfile(models.Model):

    GOAL_CHOICES = [
        ("muscle_gain", "Muscle Gain"),
        ("weight_loss", "Weight Loss"),
        ("general_fitness", "General Fitness"),
        ("strength", "Strength"),
    ]

    LEVEL_CHOICES = [
        ("Beginner", "Beginner"),
        ("Intermediate", "Intermediate"),
        ("Advanced", "Advanced"),
    ]

    EQUIPMENT_CHOICES = [
        ("No Equipment", "No Equipment"),
        ("Dumbbells", "Dumbbells"),
        ("Full Gym", "Full Gym"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="fitness_profile"
    )

    height_cm = models.FloatField()

    weight_kg = models.FloatField()

    goal = models.CharField(
        max_length=30,
        choices=GOAL_CHOICES,
        default="general_fitness"
    )

    fitness_level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default="Beginner"
    )

    equipment = models.CharField(
        max_length=30,
        choices=EQUIPMENT_CHOICES,
        default="No Equipment"
    )

    training_days = models.IntegerField(default=3)

    workout_duration = models.IntegerField(default=30)

    def __str__(self):
        return f"{self.user.username}'s Fitness Profile"


class WeeklyDietPlan(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="diet_plans"
    )

    plan_json = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Diet Plan for {self.user.username} - "
            f"{self.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
