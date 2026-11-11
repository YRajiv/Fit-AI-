
from django.db import models
from django.contrib.auth.models import User


class Reminder(models.Model):

    # Reminder Type
    REMINDER_TYPE_CHOICES = [
        ('Workout', 'Workout'),
        ('Meal', 'Meal'),
        ('Water Intake', 'Water Intake'),
        ('Sleep', 'Sleep'),
        ('Custom', 'Custom'),
    ]

    # Meal Options
    MEAL_CHOICES = [
        ('Breakfast', 'Breakfast'),
        ('Mid-morning', 'Mid-morning'),
        ('Lunch', 'Lunch'),
        ('Evening Snack', 'Evening Snack'),
        ('Dinner', 'Dinner'),
    ]

    # Repeat Options
    REPEAT_CHOICES = [
        ('Once', 'Once'),
        ('Daily', 'Daily'),
        ('Weekly', 'Weekly'),
    ]

    # User
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reminders'
    )

    # Reminder Details
    reminder_type = models.CharField(
        max_length=50,
        choices=REMINDER_TYPE_CHOICES
    )

    title = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True
    )

    # Meal-specific field
    meal_type = models.CharField(
        max_length=30,
        choices=MEAL_CHOICES,
        blank=True,
        null=True
    )

    # Reminder Schedule
    reminder_date = models.DateField()

    reminder_time = models.TimeField()

    # Repeat Option
    repeat = models.CharField(
        max_length=50,
        choices=REPEAT_CHOICES,
        default='Daily'
    )

    # Dashboard Status
    is_completed = models.BooleanField(
        default=False
    )

    is_active = models.BooleanField(
        default=True
    )

    # Notification
    notification_sent = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.title}"
