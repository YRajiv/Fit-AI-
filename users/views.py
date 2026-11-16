from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView

from .forms import UserRegisterForm, UserProfileForm
from .models import userProfile


class CustomLoginView(LoginView):
    template_name = 'users/login.html'


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard:home')
    else:
        form = UserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    profile_obj, _ = userProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, instance=profile_obj)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
    else:
        profile_form = UserProfileForm(instance=profile_obj)

    return render(request, 'users/profile.html', {'profile_form': profile_form})


def logout_view(request):
    logout(request)
    return redirect('users:login')

# Create your views here.
