from django.contrib import admin
from .models import AIFeature


@admin.register(AIFeature)
class AIFeatureAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'feature_type',
        'detected_activity',
        'food_name',
        'form_accuracy',
        'calories_detected',
        'status',
        'created_at'
    )


    list_filter = (
        'feature_type',
        'status',
        'created_at'
    )


    search_fields = (
        'user__username',
        'detected_activity',
        'food_name'
    )


    readonly_fields = (
        'created_at',
    )


    fieldsets = (

        ("User & Feature", {
            "fields": (
                "user",
                "feature_type",
                "workout"
            )
        }),


        ("AI Input", {
            "fields": (
                "input_image",
                "input_video"
            )
        }),


        ("Workout AI Analysis", {
            "fields": (
                "detected_activity",
                "form_accuracy",
                "feedback"
            )
        }),


        ("Food Recognition Result", {
            "fields": (
                "food_name",
                "calories_detected",
                "protein_detected",
                "carbs_detected",
                "fats_detected"
            )
        }),


        ("AI Status", {
            "fields": (
                "status",
                "created_at"
            )
        }),
    )

# Register your models here.
