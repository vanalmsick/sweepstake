# -*- coding: utf-8 -*-
from django.core.management import BaseCommand

from competition.models import Participant, Match, Group, Tournament, MatchBet, GroupBet, TournamentBet
from general.models import CustomUser


class Command(BaseCommand):
    """Add additional test data"""

    # Show this when the user types help
    help = "Adds test data"

    def handle(self, *args, **options):
        """Actual Commandline executed function when manage.py command is called"""
        test_users = [
            {
                "email": "user1@admin.local",
                "password": "password",
                "team": "Credit",
                "first_name": "John",
                "last_name": "Doe",
            },
            {"email": "user2@admin.local", "password": "password", "first_name": "Tom", "last_name": "Smith-Bloggs"},
            {
                "email": "user3@admin.local",
                "password": "password",
                "team": "Market",
                "first_name": "User",
                "last_name": "von der Leyen",
            },
        ]

        user_obj_dict = {}
        for user_i in test_users:
            user_obj = CustomUser(**user_i)
            user_obj.save()

            user_obj_dict[user_i["email"]] = user_obj

        test_matches = [
            {
                "phase": "group",
                "match_time": "2024-06-01T20:00+01:00",
                "team_a": Participant.objects.get(name="Germany"),
                "score_a": 4,
                "score_b": 2,
                "team_b": Participant.objects.get(name="Scotland"),
                "bets": {
                    "user1@admin.local": {"score_a": 4, "score_b": 2},
                    "user2@admin.local": {"score_a": 2, "score_b": 4},
                    "user3@admin.local": {"score_a": 2, "score_b": 2},
                },
                "winner": "Italy",
                "groups": {
                    "Group A": "Germany",
                    "Group B": "Italy",
                    "Group C": "England",
                },
            },
            {
                "phase": "group",
                "match_time": "2024-06-04T20:00+01:00",
                "team_a": Participant.objects.get(name="England"),
                "team_b": Participant.objects.get(name="Scotland"),
                "bets": {
                    "user1@admin.local": {"score_a": 4, "score_b": 2},
                    "user2@admin.local": {"score_a": 2, "score_b": 4},
                },
            },
            {
                "phase": "group",
                "match_time": "2024-06-05T20:00+01:00",
                "team_a": Participant.objects.get(name="Germany"),
                "team_b": Participant.objects.get(name="England"),
                "winner": "Germany",
                "groups": {
                    "Group B": "Spain",
                    "Group C": "Denmark",
                },
            },
        ]

        for match_i in test_matches:
            bets = match_i.pop("bets", {})
            groups = match_i.pop("groups", {})
            tournament_winner = match_i.pop("winner", None)
            match_obj = Match(**match_i)
            match_obj.save()

            for user_i, bet_i in bets.items():
                bet_obj = MatchBet(match=match_obj, user=CustomUser.objects.get(email=user_i), **bet_i)
                bet_obj.save()

            for group, group_winner in groups.items():
                bet_obj = GroupBet(
                    user=CustomUser.objects.get(email=user_i),
                    group=Group.objects.get(name=group),
                    winner=Participant.objects.get(name=group_winner),
                )
                bet_obj.save()

            if tournament_winner is not None:
                bet_obj = TournamentBet(
                    user=CustomUser.objects.get(email=user_i),
                    tournament=Tournament.objects.get(name="UEFA EURO 2024"),
                    winner=Participant.objects.get(name=tournament_winner),
                )
                bet_obj.save()
