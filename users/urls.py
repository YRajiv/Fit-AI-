from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView  # <-- Import directly
from . import views

app_name = 'users'

urlpatterns = [
    path('api/csrf/', views.api_csrf, name='api_csrf'),
    path('api/session/', views.api_session, name='api_session'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/register/', views.api_register, name='api_register'),
    path('api/logout/', views.api_logout, name='api_logout'),
    path('login/', LoginView.as_view(template_name='users/login.html'), name='login'), # <-- Use LoginView here
    path('register/', views.register, name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    
]