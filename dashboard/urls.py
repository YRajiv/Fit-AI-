from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('api/summary/', views.dashboard_summary_api, name='api_summary'),
    path('dashboard/api/summary/', views.dashboard_summary_api, name='dashboard_api_summary'),
    path('', views.dashboard, name='home'),
    path('water/add/', views.add_water_quick, name='add_water_quick'), # Add this line
    path( 'chat/',views.chat_page, name='chat'),
    path(
        'chat/api/message/',
        views.chat_api,
        name='send_message'
    ),

    path(
        'chat/api/clear/',
        views.clear_chat,
        name='clear_chat'
    ),
]