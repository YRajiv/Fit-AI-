from django.urls import path
from . import views

app_name = 'progress'

urlpatterns = [
    path('', views.progress_page, name='progress'),
    path('update-steps/', views.update_steps, name='update_steps'),
    path('update-goal/', views.update_step_goal, name='update_step_goal'),
    path('update-weight/', views.update_weight, name='update_weight'),
]