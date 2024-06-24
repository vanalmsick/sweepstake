# -*- coding: utf-8 -*-
import os
from django.core.management import BaseCommand
from competition.tasks import update_api_match_ids


class Command(BaseCommand):
    """Adds match ids for api"""

    # Show this when the user types help
    help = "Adds match ids for api"

    def handle(self, *args, **options):
        """Actual Commandline executed function when manage.py command is called"""
        if os.environ.get("API_KEY_FOOTBALL_SCORES", "") == "":
            print('Required API Key "API_KEY_FOOTBALL_SCORES" not set')
        else:
            update_api_match_ids()
