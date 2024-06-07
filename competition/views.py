# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.db.models import Sum
from django.http import HttpResponseRedirect


from .models import Match, MatchBet, GroupBet, TournamentBet
from .forms import getMatchBetFormSet, MatchBetFormSet, getGroupBetFormSet, GroupBetFormSet


# Create your views here.
def ScheduleView(request):
    """View to see list of scheduled and past matches"""
    match_lst = Match.objects.all().order_by("match_time")

    match_lst_date_sorted = {}
    last_date = None
    for match_i in match_lst:
        if last_date is None or match_i.match_time.date() != last_date:
            last_date = match_i.match_time.date()
            match_lst_date_sorted[last_date] = []
        match_lst_date_sorted[last_date].append(match_i)

    return render(request, "schedule.html", {"match_dict": match_lst_date_sorted})


def BetView(request):
    """Ciew to place user's match score bets"""
    # ArticleFormSet = formset_factory(ArticleForm)

    # Not logged-in
    if request.user.id is None:
        return HttpResponseRedirect("/login/")

    # Save/update Request
    errors = {}
    if request.method == "POST":
        if "random" in request.POST:
            match_formset = getMatchBetFormSet(user=request.user, random=True, prefix="matches")
            group_formset = getGroupBetFormSet(user=request.user, prefix="groups")

        if "submit" in request.POST:
            match_formset = MatchBetFormSet(data=request.POST, prefix="matches")
            match_formset.is_valid()

            group_formset = GroupBetFormSet(data=request.POST, prefix="groups")
            group_formset.is_valid()

            for i, form in enumerate(match_formset, 1):
                if len(form.changed_data) > 1:
                    if form.is_valid():
                        match_id = form.cleaned_data["match_id"]
                        bet_a = form.cleaned_data["bet_a"]
                        bet_b = form.cleaned_data["bet_b"]
                        searched_match = Match.objects.get(pk=match_id)
                        errors_i = {}
                        if 0 > bet_a or bet_a > 20:
                            errors_i["bet_a"] = "Score has to be between 0 and 20"
                        if 0 > bet_b or bet_b > 20:
                            errors_i["bet_b"] = "Score has to be between 0 and 20"
                        if len(errors_i) == 0:
                            if searched_match.is_editable:
                                _, _ = MatchBet.objects.update_or_create(
                                    user=request.user, match=searched_match, score_a=bet_a, score_b=bet_b
                                )
                        else:
                            errors[i] = errors_i
                    else:
                        errors[i] = form.errors

            for i, form in enumerate(group_formset, 1):
                _, _ = MatchBet.objects.update_or_create(
                    user=request.user, match=searched_match, score_a=bet_a, score_b=bet_b
                )

            match_formset = getMatchBetFormSet(user=request.user, prefix="matches")
            group_formset = getGroupBetFormSet(user=request.user, prefix="groups")

    # View/Edit Request
    else:
        match_formset = getMatchBetFormSet(user=request.user, prefix="matches")
        group_formset = getGroupBetFormSet(user=request.user, prefix="groups")

    return render(
        request, "bets.html", {"match_formset": match_formset, "group_formset": group_formset, "errors": errors}
    )


def LeaderboardView(request):
    """View to show leaderboard of users - who predicted the matches best"""
    combined = {}

    all_matches = (
        MatchBet.objects.filter(match__score_a__isnull=False, match__score_b__isnull=False, points__isnull=False)
        .values("user__username", "user__pk", "user__team")
        .annotate(total_points=Sum("points"))
    )
    combined = {match["user__username"]: match.copy() for match in all_matches}

    all_groups = (
        GroupBet.objects.filter(group__winner__isnull=False, points__isnull=False)
        .values("user__username", "user__pk", "user__team")
        .annotate(total_points=Sum("points"))
    )
    for group in all_groups:
        user__username = group["user__username"]
        if user__username in combined:
            combined[user__username]["total_points"] += group["total_points"]
        else:
            combined[user__username] = group.copy()

    all_tournaments = (
        TournamentBet.objects.filter(tournament__third_place__isnull=False, points__isnull=False)
        .values("user__username", "user__pk", "user__team")
        .annotate(total_points=Sum("points"))
    )
    for tournament in all_tournaments:
        user__username = tournament["user__username"]
        if user__username in combined:
            combined[user__username]["total_points"] += tournament["total_points"]
        else:
            combined[user__username] = tournament.copy()

    combined = sorted(combined.values(), key=lambda d: d["total_points"], reverse=True)
    final_ranking = []
    last_points = 1_000_000
    last_position = 0

    for i in combined:
        total_points = i["total_points"]
        if total_points is not None:
            if total_points < last_points:
                last_position += 1
                last_points = total_points
            final_ranking.append({**i, "rank": last_position})

    return render(request, "leaderboard.html", {"ranking": final_ranking})
