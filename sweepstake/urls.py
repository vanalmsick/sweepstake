# -*- coding: utf-8 -*-
"""sweepstake URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.views.generic.base import TemplateView

from general.views import LoginView, LogoutView, SignupView, VerifyEmailView
from competition.views import (
    ScheduleView,
    MyBetView,
    OthersBetView,
    LeaderboardView,
    OthersGroupPredictionsView,
    OthersTournamentPredictionsView,
    OthersMatchPredictionsView,
)

urlpatterns = [
    path(
        "",
        TemplateView.as_view(template_name="home.html"),
        name="home",
    ),
    path(
        "rules/",
        TemplateView.as_view(template_name="rules.html"),
        name="rules",
    ),
    path("schedule/", ScheduleView, name="schedule"),
    path(
        "schedule/country/<str:country_name>/",
        ScheduleView,
        name="country-schedule",
    ),
    path(
        "schedule/group/<str:group_name>/",
        ScheduleView,
        name="group-schedule",
    ),
    path("predictions/my/", MyBetView, name="predictions"),
    path(
        "predictions/other/<int:other_user_id>/",
        OthersBetView,
        name="others-predictions",
    ),
    path(
        "predictions/group/<str:group_name>/",
        OthersGroupPredictionsView,
        name="group-predictions",
    ),
    path(
        "predictions/tournament/<str:tournament_name>/",
        OthersTournamentPredictionsView,
        name="tournament-predictions",
    ),
    path(
        "predictions/match/<int:match_id>/",
        OthersMatchPredictionsView,
        name="match-predictions",
    ),
    path(
        "leaderboard/",
        LeaderboardView,
        name="leaderboard",
    ),
    path("signup/", SignupView, name="sign-up"),
    path("verify/<int:user_id>/", VerifyEmailView, name="verify-email"),
    path("login/", LoginView, name="log-in"),
    path("logout/", LogoutView, name="log-out"),
    path("admin/", admin.site.urls),
]
