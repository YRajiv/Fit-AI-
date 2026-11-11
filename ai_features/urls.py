from django.urls import path
from . import views

app_name = 'ai_features'

urlpatterns = [
    path('posture-check/', views.posture_check, name='posture_check'),
]