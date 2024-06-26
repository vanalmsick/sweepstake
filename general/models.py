# -*- coding: utf-8 -*-
import os
from django.db import models
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from sweepstake.celery import app


def delete_dynamic_cached_pages(
    prefix_lst=[
        "schedule_data_",
        "leaderboard_data",
        "predictions_nonmatch_",
        "predictions_match_",
    ],
):
    """delete cached pages - used e.g. if match scores are entered"""
    print("Deleting cached dynamic pages")
    os.system("redis-cli flushall")
    # cache_keys = cache_keys = cache._cache.get_client().keys(f"*{settings.CACHES['default']['KEY_PREFIX']}*")
    # for key in cache_keys:
    #     if any([i in str(key) for i in prefix_lst]):
    #         print("Deleted cached", key)
    #         cache.delete(key)


USER_TEAMS = [
    ("Credit", "Credit Risk"),
    ("Market", "Market Risk"),
    ("Liquidity", "Liquidity Risk"),
    ("COO", "Risk COO"),
    ("Capital / Model / Data / RA", "Risk Capital, Model Risk, Risk Analytics, Data"),
    ("Other", "Other"),
]


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        # extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom User model - needed to use email as login and a few more additional fields"""

    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(max_length=30, null=False, blank=False)
    last_name = models.CharField(max_length=40, null=False, blank=False)
    team = models.CharField(choices=USER_TEAMS, max_length=40, null=True, blank=True)

    username = models.CharField(max_length=40, null=True, blank=True)

    has_paid = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.first_name is None or self.first_name == "":
            self.username = self.email.split("@")[0]
        else:
            self.username = f'{self.first_name} {".".join([i[0] for i in self.last_name.replace("-"," ").split(" ") if len(i) >= 1])}.'
        _state_adding = self._state.adding
        super(CustomUser, self).save(*args, **kwargs)

        # Update Leaderboard view
        delete_dynamic_cached_pages(prefix_lst=["leaderboard"])

        # Send Welcome email
        if _state_adding and "admin" not in self.email and "local" not in self.email:
            app.send_task(
                "competition.tasks.welcome_email",
                args=[
                    self.pk,
                ],
            )


class EmailTemplates(models.Model):
    """Email Templates"""

    name = models.CharField(max_length=40, unique=True)
    email_subject = models.CharField(max_length=60, blank=True, null=True)
    html = models.TextField(max_length=3_000)
