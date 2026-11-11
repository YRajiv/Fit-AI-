from django.contrib import admin
from .models import FoodScan, NutritionGoal, WaterIntake


admin.site.register(FoodScan)
admin.site.register(NutritionGoal)
admin.site.register(WaterIntake)

# Register your models here.
