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
from django.views.generic.base import TemplateView, RedirectView
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView

from competition.models import Tournament
from general.views import LoginView, LogoutView, SignupView, SignupParentView, VerifyEmailView
from competition.views import (
    ScheduleView,
    MyBetView,
    OthersBetView,
    LeaderboardView,
    OthersGroupPredictionsView,
    OthersTournamentPredictionsView,
    OthersMatchPredictionsView,
)


admin.site.site_title = "Prediction Game Admin"
admin.site.site_header = "Prediction Game Admin Space"
admin.site.index_title = "Prediction Game"
PasswordResetView.title = "Prediction Game Admin"

urlpatterns = [
    path(
        "",
        TemplateView.as_view(
            template_name="home.html",
            extra_context=dict(tournament_editable=Tournament.objects.all().first().is_editable),
        ),
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
    path("signup/", SignupParentView, name="sign-up"),
    path("late-signup/", SignupView, name="late-sign-up"),
    path("verify/<int:user_id>/", VerifyEmailView, name="verify-email"),
    path("login/", LoginView, name="log-in"),
    path("logout/", LogoutView, name="log-out"),
    path("admin/", admin.site.urls),
    path(
        "reset-password/",
        PasswordResetView.as_view(
            template_name="registration/password_reset.html",
            html_email_template_name="registration/password_reset_email.html",
        ),
        name="password_reset",
    ),
    path(
        "reset-password/done/",
        PasswordResetDoneView.as_view(template_name="registration/reset_password_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset-password/confirm/<uidb64>[0-9A-Za-z]+)-<token>/",
        PasswordResetConfirmView.as_view(template_name="registration/password_reset_complete.html"),
        name="password_reset_confirm",
    ),
    path("reset-password/complete/", RedirectView.as_view(url="/predictions/my/"), name="password_reset_complete"),
]
