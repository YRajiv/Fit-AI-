from django.urls import path
from nutrition.views import scan_food_view, nutrition_page_view

urlpatterns = [
    path('', nutrition_page_view, name='nutrition_page'),          # Renders HTML page
    path('scan/', scan_food_view, name='scan_food'),               # Handles API POST request
]