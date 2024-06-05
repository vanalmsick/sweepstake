# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth import logout

from .models import CustomUser
from .forms import LoginForm, CustomUserCreationForm


def SignupView(request):
    """View to create a new user"""
    if request.method == "POST":
        form = CustomUserCreationForm(data=request.POST)
        if form.is_valid():
            username = form.save()
            login(request, username)
            return redirect("bets")
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
                return redirect("bets")
            except Exception as e:
                message = f"ERROR: {e}"
        else:
            message = "Login failed!"

    else:
        form = LoginForm()

    return render(request, "registration/login.html", {"form": form, "message": message})


def LogoutView(request):
    logout(request)
    return redirect("home")
