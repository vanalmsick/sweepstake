# -*- coding: utf-8 -*-
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.forms import AuthenticationForm
from django import forms

from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    """Form to create a new user"""

    email = forms.EmailField(label=False)
    first_name = forms.CharField(label=False)
    last_name = forms.CharField(label=False)
    password1 = forms.CharField(label=False, widget=forms.PasswordInput())
    password2 = forms.CharField(label=False, widget=forms.PasswordInput())

    email.widget.attrs.update({"class": "form-control", "placeholder": "Enter email"})
    first_name.widget.attrs.update({"class": "form-control", "placeholder": "First name"})
    last_name.widget.attrs.update({"class": "form-control", "placeholder": "Last name"})
    password1.widget.attrs.update({"class": "form-control", "placeholder": "Password"})
    password2.widget.attrs.update({"class": "form-control", "placeholder": "Password"})

    class Meta:
        model = CustomUser
        fields = (
            "email",
            "first_name",
            "last_name",
        )


class CustomUserChangeForm(UserChangeForm):
    """Form to change a user's details"""

    class Meta:
        model = CustomUser
        fields = (
            "email",
            "first_name",
            "last_name",
        )


class LoginForm(AuthenticationForm):
    """Form to login user"""

    pass
