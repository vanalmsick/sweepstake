# -*- coding: utf-8 -*-
import datetime
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth import logout
from django.conf import settings

from competition.models import Tournament
from .models import CustomUser
from .forms import LoginForm, CustomUserCreationForm


def SignupParentView(request):
    """Parent sign-up view to check if it is still possible to sign-up or too late"""
    tournament = Tournament.objects.all().first()
    now = settings.TIME_ZONE_OBJ.localize(datetime.datetime.now())

    if (now + datetime.timedelta(minutes=30)) < tournament.first_match_time:
        return SignupView(request)
    else:
        return TooLateView(request)


def SignupView(request):
    """View to create a new user"""
    if request.method == "POST":
        form = CustomUserCreationForm(data=request.POST)
        if form.is_valid():
            username = form.save()
            login(request, username)
            return redirect("predictions")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


def LoginView(request):
    """View to login user"""
    message = None
    if request.method == "POST":
        form = LoginForm(data=request.POST)
        if form.is_valid():
            message = "Login successful!"
            username = None
            try:
                username = CustomUser.objects.get(email=form.cleaned_data.get("username"))
                login(request, username)
                return redirect("predictions")
            except Exception as e:
                message = f"ERROR: {e}"
        else:
            message = "Login failed!"

    else:
        form = LoginForm()

    return render(request, "registration/login.html", {"form": form, "message": message})


def LogoutView(request):
    """View to log-out user"""
    logout(request)
    return redirect("home")


def VerifyEmailView(request, user_id):
    """View to verify user email via link"""
    user = CustomUser.objects.get(pk=user_id)
    setattr(user, "is_verified", True)
    user.save()
    return redirect("predictions")


def TooLateView(request):
    """View to say too late - that signup is closed"""
    return render(request, "registration/too_late.html", {})
