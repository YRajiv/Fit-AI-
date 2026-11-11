from django.urls import path
from . import views

urlpatterns = [
    path('', views.diet_dashboard_view, name='diet_dashboard'),

    path('onboarding/', views.onboarding_view, name='onboarding'),

    path(
        'api/analyze-body-fat/',
        views.analyze_body_fat_api,
        name='analyze_body_fat_api'
    ),

    path(
        'api/save-profile/',
        views.save_profile_api,
        name='save_profile_api'
    ),
]