from django.contrib import admin
from .models import UserFitnessProfile, WeeklyDietPlan

# Register your models here
admin.site.register(UserFitnessProfile)
admin.site.register(WeeklyDietPlan)