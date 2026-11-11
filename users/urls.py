from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView  # <-- Import directly
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', LoginView.as_view(template_name='users/login.html'), name='login'), # <-- Use LoginView here
    path('register/', views.register, name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    
]