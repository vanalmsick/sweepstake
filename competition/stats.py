# -*- coding: utf-8 -*-
from django.db.models import Q, F, Count, Case, When
from django.core.cache import cache
from django.conf import settings
import random
import numpy as np

from .models import Match, MatchBet


def _get_real_match_distribution():
    """get general stats about match winner teams"""
    all_matches = Match.objects.filter(score_a__isnull=False, score_b__isnull=False)
    num_a_won = len(all_matches.filter(Q(score_a__gt=F("score_b"))))
    num_b_won = len(all_matches.filter(Q(score_b__gt=F("score_a"))))
    num_draw = len(all_matches.filter(Q(score_a=F("score_b"))))
    num_matches = len(all_matches)
    return num_matches, num_a_won, num_draw, num_b_won


def _get_user_match_predictions(user_id):
    """get a user's match prediction stats"""
    all_match_bets = MatchBet.objects.filter(points__isnull=False, user__pk=user_id).annotate(
        match_winner=Case(
            When(score_a__gt=F("score_b"), then=1),
            When(score_b__gt=F("score_a"), then=-1),
            default=0,
        )
    )

    grouped_match_bets = all_match_bets.values("match_winner", "points").annotate(count=Count("pk"))

    correct_score = [0, 0, 0]
    correct_winner = [0, 0, 0]
    correct_winner_sum = 0
    false_prediction = [0, 0, 0]
    for group in grouped_match_bets:
        if group["points"] == 5:
            tmp_dict = correct_score
            correct_winner_sum += group["count"]
        elif group["points"] == 3:
            tmp_dict = correct_winner
            correct_winner_sum += group["count"]
        elif group["points"] == 0:
            tmp_dict = false_prediction
        if group["match_winner"] == 1:
            tmp_dict[0] += group["count"]
        elif group["match_winner"] == 0:
            tmp_dict[1] += group["count"]
        elif group["match_winner"] == -1:
            tmp_dict[2] += group["count"]

    return correct_score, correct_winner, false_prediction, correct_winner_sum


def _get_random_distribution(random_seed=1, simulations=100_000):
    """get random distribution prediction stats binned"""
    random.seed(random_seed)
    num_matches, num_a_won, num_draw, num_b_won = _get_real_match_distribution()
    correct_matches = [1 for i in range(num_a_won)] + [0 for i in range(num_a_won)] + [-1 for i in range(num_b_won)]
    correct_predictions = []
    for i in range(simulations):
        random_scores = random.choices([1, 0, -1], k=num_matches)
        correct_predictions.append(sum([1 if i == j else 0 for i, j in zip(correct_matches, random_scores)]))
    binned_random_dist = np.histogram(correct_predictions, bins=np.arange(0, num_matches, 3))
    return binned_random_dist[0].tolist(), binned_random_dist[1].tolist()


def _get_prediction_distribution(bins, user_id=None):
    """get user's prediction stats binned"""
    users_correct_bets = {
        i["user"]: i["correct_cnt"]
        for i in MatchBet.objects.filter(points__gte=3).values("user").annotate(correct_cnt=Count("pk"))
    }
    users_lst = list(users_correct_bets.values())
    binned_user_dist = np.histogram(users_lst, bins=bins)
    return (
        binned_user_dist[0].tolist(),
        binned_user_dist[1].tolist(),
        None if user_id is None else users_correct_bets[user_id],
    )


def get_chart_data(user_id):
    """function to get all statistics data for statistics section on my prediction view"""
    stats_chart_data = cache.get("stats_data", None)

    if stats_chart_data is None:
        simulations = 1_000_000

        num_matches, num_a_won, num_draw, num_b_won = _get_real_match_distribution()

        if num_matches > 30:
            data_random, label_bins = _get_random_distribution(simulations=simulations)
            data_participants, _, user_correct_matches = _get_prediction_distribution(label_bins)
            data_random = [round(i / simulations * sum(data_participants), 2) for i in data_random]
            labels = [f"{label_bins[i]}-{label_bins[i + 1]}" for i in range(len(data_random))]

            stats_chart_data = {
                "labels": labels,
                "data_random": data_random,
                "data_participants": data_participants,
                "num_a_won": num_a_won,
                "num_draw": num_draw,
                "num_b_won": num_b_won,
                "num_total": num_matches,
                "data_matches": [num_a_won, num_draw, num_b_won],
            }

            cache.set(
                "stats_data",
                stats_chart_data,
                timeout=settings.STATIC_PAGE_CACHE_TIME,
            )

    user_stats = cache.get(f"stats_user_{user_id}", None)
    if user_stats is None and stats_chart_data is not None:
        my_correct_score, my_correct_winner, my_false_prediction, my_correct_winner_sum = _get_user_match_predictions(
            user_id
        )

        user_stats = {
            "my_correct_score": my_correct_score,
            "my_correct_winner": my_correct_winner,
            "my_false_prediction": my_false_prediction,
            "my_correct_winner_sum": my_correct_winner_sum,
        }

        cache.set(
            f"stats_user_{user_id}",
            user_stats,
            timeout=settings.STATIC_PAGE_CACHE_TIME,
        )

    return None if stats_chart_data is None else {**stats_chart_data, **user_stats}
