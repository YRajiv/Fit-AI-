from django.db import models
from django.contrib.auth.models import User


class FoodScan(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    food_name = models.CharField(
        max_length=100
    )

    image = models.ImageField(
        upload_to="food_images/"
    )

    calories = models.FloatField()

    protein = models.FloatField()

    carbohydrates = models.FloatField()

    fats = models.FloatField()

    fiber = models.FloatField()

    quantity = models.CharField(
        max_length=50
    )

    is_consumed = models.BooleanField(
        default=True
    )

    scan_date = models.DateTimeField(
        auto_now_add=True
    )



class NutritionGoal(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    calories_target = models.IntegerField()

    protein_target = models.FloatField()

    carbs_target = models.FloatField()

    fat_target = models.FloatField()


    def __str__(self):
        return self.user.username



class WaterIntake(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    water_amount = models.FloatField()

    target_amount = models.FloatField(
        default=3
    )

    date = models.DateField(
        auto_now_add=True
    )