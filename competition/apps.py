# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CompetitionConfig(AppConfig):
    """Sub-app default config"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "competition"
