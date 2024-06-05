# -*- coding: utf-8 -*-
from django.core.management import BaseCommand

from competition.models import Participant, Match, Bet
from general.models import CustomUser


class Command(BaseCommand):
    """Add additional test data"""

    # Show this when the user types help
    help = "Adds test data"

    def handle(self, *args, **options):
        """Actual Commandline executed function when manage.py command is called"""
        test_users = [
            {"email": "user1@admin.local", "password": "password", "first_name": "User1", "last_name": "Aaa"},
            {"email": "user2@admin.local", "password": "password", "first_name": "User2", "last_name": "Bbb-Cc"},
            {"email": "user3@admin.local", "password": "password", "first_name": "User3", "last_name": "Dd Ee"},
        ]

        user_obj_dict = {}
        for user_i in test_users:
            user_obj = CustomUser(**user_i)
            user_obj.save()

            user_obj_dict[user_i["email"]] = user_obj

        test_matches = [
            {
                "phase": "group",
                "match_time": "2024-06-01T20:00",
                "team_a": Participant.objects.get(name="Germany"),
                "score_a": 4,
                "score_b": 2,
                "team_b": Participant.objects.get(name="Scotland"),
                "bets": {
                    "user1@admin.local": {"score_a": 4, "score_b": 2},
                    "user2@admin.local": {"score_a": 2, "score_b": 4},
                    "user3@admin.local": {"score_a": 2, "score_b": 2},
                },
            },
            {
                "phase": "group",
                "match_time": "2024-06-04T20:00",
                "team_a": Participant.objects.get(name="England"),
                "team_b": Participant.objects.get(name="Scotland"),
                "bets": {
                    "user1@admin.local": {"score_a": 4, "score_b": 2},
                    "user2@admin.local": {"score_a": 2, "score_b": 4},
                },
            },
            {
                "phase": "group",
                "match_time": "2024-06-05T20:00",
                "team_a": Participant.objects.get(name="Germany"),
                "team_b": Participant.objects.get(name="England"),
            },
        ]

        for match_i in test_matches:
            bets = match_i.pop("bets", {})
            match_obj = Match(**match_i)
            match_obj.save()

            for user_i, bet_i in bets.items():
                bet_obj = Bet(match=match_obj, user=CustomUser.objects.get(email=user_i), **bet_i)
                bet_obj.save()
