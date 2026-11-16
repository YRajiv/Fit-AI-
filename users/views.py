import json

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .forms import UserRegisterForm, UserProfileForm
from .models import userProfile


@require_GET
@ensure_csrf_cookie
def api_csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


@require_GET
def api_session(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {'success': False, 'error': 'Authentication required.'},
            status=401
        )

    return JsonResponse({
        'success': True,
        'user': {'username': request.user.get_username()}
    })


@require_POST
@ensure_csrf_cookie
def api_login(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {'success': False, 'error': 'Invalid request data.'},
            status=400
        )

    if not isinstance(data, dict):
        return JsonResponse(
            {'success': False, 'error': 'Invalid request data.'},
            status=400
        )

    username = data.get('username')
    password = data.get('password')

    if not isinstance(username, str) or not isinstance(password, str):
        return JsonResponse(
            {'success': False, 'error': 'Enter your username and password.'},
            status=400
        )

    user = authenticate(
        request,
        username=username,
        password=password
    )

    if user is None:
        return JsonResponse(
            {'success': False, 'error': 'Invalid username or password.'},
            status=400
        )

    login(request, user)
    return JsonResponse({
        'success': True,
        'user': {'username': user.get_username()},
        'csrfToken': get_token(request)
    })


@require_POST
@ensure_csrf_cookie
def api_register(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {'success': False, 'error': 'Invalid request data.'},
            status=400
        )

    if not isinstance(data, dict):
        return JsonResponse(
            {'success': False, 'error': 'Invalid request data.'},
            status=400
        )

    form = UserRegisterForm(data)
    if not form.is_valid():
        return JsonResponse({
            'success': False,
            'errors': form.errors.get_json_data()
        }, status=400)

    user = form.save()
    login(request, user)
    return JsonResponse({
        'success': True,
        'user': {'username': user.get_username()},
        'csrfToken': get_token(request)
    }, status=201)


@require_POST
@ensure_csrf_cookie
def api_logout(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {'success': False, 'error': 'Authentication required.'},
            status=401
        )

    logout(request)
    return JsonResponse({
        'success': True,
        'csrfToken': get_token(request)
    })


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
