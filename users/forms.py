from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import userProfile  # Updated to lowercase 'u'

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = userProfile  # Updated to lowercase 'u'
        fields = ['age', 'height', 'weight', 'fitness_goal', 'experience_level']