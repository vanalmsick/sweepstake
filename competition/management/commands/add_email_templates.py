# -*- coding: utf-8 -*-
import os
from django.core.management import BaseCommand

from general.models import EmailTemplates


class Command(BaseCommand):
    """Adds email templates from html files into django admin"""

    # Show this when the user types help
    help = "Adds email templates from html files into django admin"

    def handle(self, *args, **options):
        """Actual Commandline executed function when manage.py command is called"""
        for file_name, email_subject in {
            "daily_email.html": "Place your predictions for today's matches",
            "final_reminder.html": "Last chance to place your EURO 2024 Champion prediction",
            "welcome_email.html": "Welcome to the MS Risk 2024 EURO Prediction Game",
            "payment_reminder.html": "MS Risk 2024 EURO Prediction Game",
        }.items():
            with open(os.path.join("templates", "emails", file_name), "r") as file:
                file_contents = file.read()
            EmailTemplates(name=file_name.split(".")[0], email_subject=email_subject, html=file_contents).save()
