# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.db.models import Sum

from general.models import CustomUser
from .models import Match, MatchBet, Participant, Group, GroupBet, TournamentBet
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
        return redirect("log-in")

    user_data = getMyScore(request.user.pk)

    # Save/update Request
    errors = {}
    if request.method == "POST":
        if "random" in request.POST:
            match_formset = getMatchBetFormSet(user=request.user, random=True, prefix="matches")
            group_formset = getGroupBetFormSet(user=request.user, prefix="groups")

        if "submit" in request.POST:
            match_formset = MatchBetFormSet(data=request.POST, prefix="matches")
            match_formset.is_valid()

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
                                bet_obj = MatchBet.objects.filter(user=request.user, match=searched_match)
                                if len(bet_obj) > 0:
                                    bet_obj = bet_obj[0]
                                    setattr(bet_obj, "score_a", bet_a)
                                    setattr(bet_obj, "score_b", bet_b)
                                    bet_obj.save()
                                else:
                                    MatchBet(
                                        user=request.user, match=searched_match, score_a=bet_a, score_b=bet_b
                                    ).save()
                        else:
                            errors[i] = errors_i
                    else:
                        errors[i] = form.errors

            group_formset = GroupBetFormSet(data=request.POST, prefix="groups")
            group_formset.is_valid()

            for i, form in enumerate(group_formset, 1):
                if form.is_valid():
                    group_id = form.cleaned_data["group_id"]
                    bet_winner = form.cleaned_data["bet"]
                    searched_group = Group.objects.get(pk=group_id)
                    searched_winner = Participant.objects.get(pk=bet_winner)
                    if searched_group.is_editable:
                        bet_obj = GroupBet.objects.filter(user=request.user, group=searched_group)
                        if len(bet_obj) > 0:
                            bet_obj = bet_obj[0]
                            setattr(bet_obj, "winner", searched_winner)
                            bet_obj.save()
                        else:
                            GroupBet(user=request.user, group=searched_group, winner=searched_winner).save()

            match_formset = getMatchBetFormSet(user=request.user, prefix="matches")
            group_formset = getGroupBetFormSet(user=request.user, prefix="groups")

    # View/Edit Request
    else:
        match_formset = getMatchBetFormSet(user=request.user, prefix="matches")
        group_formset = getGroupBetFormSet(user=request.user, prefix="groups")

    return render(
        request,
        "predictions.html",
        {
            "match_formset": match_formset,
            "group_formset": group_formset,
            "errors": errors,
            "user_name": user_data["user__username"],
            "user_rank": user_data["rank"],
            "user_points": "-/-" if user_data["total_points"] is None else user_data["total_points"],
        },
    )


def getLeaderboard():
    combined = {
        user.pk: {"user__username": user.username, "user__pk": user.pk, "user__team": user.team, "total_points": None}
        for user in CustomUser.objects.filter(email__isnull=False)
    }

    all_matches = (
        MatchBet.objects.filter(match__score_a__isnull=False, match__score_b__isnull=False, points__isnull=False)
        .values("user__username", "user__pk", "user__team")
        .annotate(total_points=Sum("points"))
    )
    all_groups = (
        GroupBet.objects.filter(group__winner__isnull=False, points__isnull=False)
        .values("user__username", "user__pk", "user__team")
        .annotate(total_points=Sum("points"))
    )
    all_tournaments = (
        TournamentBet.objects.filter(tournament__third_place__isnull=False, points__isnull=False)
        .values("user__username", "user__pk", "user__team")
        .annotate(total_points=Sum("points"))
    )
    for dataset in [all_matches, all_groups, all_tournaments]:
        for datapoint in dataset:
            user__username = datapoint["user__pk"]
            total_points = datapoint["total_points"]
            if combined[user__username]["total_points"] is None:
                combined[user__username]["total_points"] = total_points
            else:
                combined[user__username]["total_points"] += total_points

    combined = sorted(
        combined.values(), key=lambda d: -1 if d["total_points"] is None else d["total_points"], reverse=True
    )
    final_ranking = []
    last_points = 1_000_000
    last_position = 0

    for i in combined:
        total_points = i["total_points"]
        if total_points is None:
            _ = i.pop("total_points")
            final_ranking.append({**i, "rank": "-/-", "total_points": "-/-"})
        else:
            if total_points < last_points:
                last_position += 1
                last_points = total_points
            final_ranking.append({**i, "rank": last_position})

    return final_ranking


def getMyScore(pk):
    leaderboard = getLeaderboard()
    my_score = [i for i in leaderboard if i["user__pk"] == pk]
    return None if len(my_score) == 0 else my_score[0]


def LeaderboardView(request):
    """View to show leaderboard of users - who predicted the matches best"""
    return render(request, "leaderboard.html", {"ranking": getLeaderboard()})
