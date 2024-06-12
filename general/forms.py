# -*- coding: utf-8 -*-
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django import forms

from .models import CustomUser
from .models import USER_TEAMS


def email_domain(value):
    """email validation to only allow certain email dimains to sign-up"""
    if "@morganstanley.com" not in str(value).lower():
        raise ValidationError("Email must be a @morganstanley.com")
    return value


class CustomUserCreationForm(UserCreationForm):
    """Form to create a new user"""

    email = forms.EmailField(label=False, validators=[email_domain])
    first_name = forms.CharField(label=False)
    last_name = forms.CharField(label=False)
    team = forms.CharField(label=False, widget=forms.Select(choices=[("", "---------")] + USER_TEAMS))
    password1 = forms.CharField(label=False, widget=forms.PasswordInput())
    password2 = forms.CharField(label=False, widget=forms.PasswordInput())
    is_active = True

    email.widget.attrs.update({"class": "form-control", "placeholder": "Enter email"})
    first_name.widget.attrs.update({"class": "form-control", "placeholder": "First name"})
    last_name.widget.attrs.update({"class": "form-control", "placeholder": "Last name"})
    team.widget.attrs.update({"class": "form-control", "placeholder": "Department"})
    password1.widget.attrs.update({"class": "form-control", "placeholder": "Password"})
    password2.widget.attrs.update({"class": "form-control", "placeholder": "Password"})

    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name", "team")


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

    username = forms.EmailField(label=False)
    password = forms.CharField(label=False, widget=forms.PasswordInput())

    username.widget.attrs.update({"class": "form-control", "placeholder": "Enter email", "autofocus": True})
    password.widget.attrs.update({"class": "form-control", "placeholder": "Password"})
