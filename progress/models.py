
from django.db import models
from django.contrib.auth.models import User


class DailyProgress(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='daily_progress'
    )

    date = models.DateField()

    steps = models.PositiveIntegerField(default=0)

    steps_goal = models.PositiveIntegerField(default=8000)

    active_minutes = models.PositiveIntegerField(default=0)

    distance_km = models.FloatField(default=0.0)

    activity_calories = models.FloatField(default=0.0)

    weight_kg = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date'],
                name='unique_daily_progress_per_user'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.date}"


# Create your models here.
