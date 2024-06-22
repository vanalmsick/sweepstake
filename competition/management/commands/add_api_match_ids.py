# -*- coding: utf-8 -*-
import os
from django.core.management import BaseCommand
from django.db.models import Q

from competition.models import Match
from competition.api_football_scores import get_api_match_ids


class Command(BaseCommand):
    """Adds match ids for api"""

    # Show this when the user types help
    help = "Adds match ids for api"

    def handle(self, *args, **options):
        if os.environ.get("API_KEY_FOOTBALL_SCORES", "") == "":
            print('Required API Key "API_KEY_FOOTBALL_SCORES" not set')

        else:
            match_id_data = get_api_match_ids(season_year="2024")
            for match in match_id_data:
                match_search = Match.objects.filter(match_time=match["fixture"]["date"])
                if len(match_search) > 1:
                    match_search = match_search.filter(
                        Q(team_a__name__icontains=match["teams"]["home"]["name"])
                        | Q(team_a__name__icontains=match["teams"]["away"]["name"])
                        | Q(team_b__name__icontains=match["teams"]["home"]["name"])
                        | Q(team_b__name__icontains=match["teams"]["away"]["name"])
                    )
                if len(match_search) == 1:
                    match_found = match_search[0]
                    setattr(match_found, "api_match_id", int(match["fixture"]["id"]))
                    if match["fixture"]["status"]["short"] == "FT":
                        if match_found.api_match_data is None:
                            setattr(match_found, "api_match_data", match)
                        if match_found.score_a is None:
                            setattr(match_found, "score_a", match["goals"]["home"])
                        if match_found.score_b is None:
                            setattr(match_found, "score_b", match["goals"]["away"])
                    match_found.save()
                print(f"API data added for match {match_found}")
