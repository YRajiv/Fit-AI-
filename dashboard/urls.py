from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
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