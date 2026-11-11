from django.urls import path

from . import views

app_name = "workout"

urlpatterns = [
    path(
        "",
        views.workouts_view,
        name="workouts"
    ),

    path(
        "start/",
        views.start_workout,
        name="start_workout"
    ),

    path(
        "complete/<int:workout_id>/",
        views.complete_workout,
        name="complete_workout"
    ),
]