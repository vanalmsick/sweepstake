# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.db.models import Sum
from django.http import HttpResponseRedirect

from .models import Match, Bet
from .forms import getBetFormSet, BetFormSet


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
    if request.method == "POST":
        formset = BetFormSet(request.POST)  # , request.FILES
        if formset.is_valid():
            # do something with the formset.cleaned_data
            pass

    # View/Edit Request
    else:
        formset = getBetFormSet(user=request.user)

    return render(request, "bets.html", {"formset": formset})


def LeaderboardView(request):
    """View to show leaderboard of users - who predicted the matches best"""
    all_matches = (
        Bet.objects.all()
        .values("user__username", "user__pk")
        .annotate(total_points=Sum("points"))
        .order_by("-total_points")
    )

    final_ranking = []
    last_points = 1_000_000
    last_position = 0

    for i in all_matches:
        total_points = i["total_points"]
        if total_points < last_points:
            last_position += 1
            last_points = total_points
        final_ranking.append({**i, "rank": last_position})

    return render(request, "leaderboard.html", {"ranking": final_ranking})
