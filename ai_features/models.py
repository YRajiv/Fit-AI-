from django.db import models
from django.contrib.auth.models import User
from workouts.models import Workout


class AIFeature(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    # Link AI analysis with workout
    workout = models.ForeignKey(
        Workout,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )


    # AI Feature Type
    feature_type = models.CharField(
        max_length=50,
        choices=[
            ('Workout Analysis', 'Workout Analysis'),
            ('Food Recognition', 'Food Recognition'),
            ('Calorie Prediction', 'Calorie Prediction'),
            ('Recommendation', 'Recommendation')
        ]
    )


    # Uploaded Image/Video for AI
    input_image = models.ImageField(
        upload_to="ai_inputs/",
        blank=True,
        null=True
    )

    input_video = models.FileField(
        upload_to="ai_videos/",
        blank=True,
        null=True
    )


    # AI Result
    detected_activity = models.CharField(
        max_length=100,
        blank=True
    )

    form_accuracy = models.IntegerField(
        default=0,
        help_text="AI form accuracy percentage"
    )


    feedback = models.TextField(
        blank=True
    )


    # Food AI Results
    food_name = models.CharField(
        max_length=100,
        blank=True
    )

    calories_detected = models.IntegerField(
        default=0
    )

    protein_detected = models.FloatField(
        default=0
    )

    carbs_detected = models.FloatField(
        default=0
    )

    fats_detected = models.FloatField(
        default=0
    )


    # AI Status
    status = models.CharField(
        max_length=50,
        choices=[
            ('Processing','Processing'),
            ('Completed','Completed'),
            ('Failed','Failed')
        ],
        default="Processing"
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return f"{self.user.username} - {self.feature_type}"

# Create your models here.
