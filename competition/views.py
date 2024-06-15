# -*- coding: utf-8 -*-
import datetime
from django.shortcuts import render, redirect
from django.db.models import Sum, Q, F, Case, When
from django.db import models
from django.conf import settings
from django.core.cache import cache

from general.models import CustomUser
from .models import Match, MatchBet, Participant, Group, GroupBet, TournamentBet, MATCH_PHASES_DICT, BROADCASTER_URLS
from .forms import (
    getMatchBetFormSet,
    MatchBetFormSet,
    getGroupBetFormSet,
    GroupBetFormSet,
    TournamentBetForm,
    getTournamentForm,
    Tournament,
)


# Create your views here.
def ScheduleView(request, country_name=None, group_name=None):
    """View to see list of scheduled and past matches"""
    match_lst_date_sorted = cache.get(f"schedule_data_{country_name}_{group_name}", None)

    if match_lst_date_sorted is None:
        print(
            f'Get ScheduleView {("for all matches" if group_name is None else "with group " + group_name) if country_name is None else "with country " + country_name}.'
        )

        now = settings.TIME_ZONE_OBJ.localize(datetime.datetime.now())
        if country_name is not None:
            match_lst = Match.objects.filter(
                Q(team_a__name__icontains=country_name) | Q(team_b__name__icontains=country_name)
            ).order_by("match_time")
        elif group_name is not None:
            match_lst = Match.objects.filter(
                Q(team_a__group__name__icontains=group_name) | Q(team_b__group__name__icontains=group_name)
            ).order_by("match_time")
        else:
            match_lst = Match.objects.all().order_by("match_time")

        match_lst_date_sorted = {}
        last_date = None
        for match_i in match_lst:
            if last_date is None or match_i.match_time.date() != last_date:
                last_date = match_i.match_time.date()
                match_lst_date_sorted[last_date] = []
            match_i.tv_broadcaster__url = BROADCASTER_URLS[match_i.tv_broadcaster]
            match_i.finished = (match_i.match_time + datetime.timedelta(minutes=90)) < now
            match_lst_date_sorted[last_date].append(match_i)

        cache.set(
            f"schedule_data_{country_name}_{group_name}",
            match_lst_date_sorted,
            timeout=settings.DYNAMIC_PAGE_CACHE_TIME,
        )

    return render(
        request,
        "schedule.html",
        {
            "match_dict": match_lst_date_sorted,
            "title": "Tournament Schedule"
            if country_name is None and group_name is None
            else f"Matches: {group_name if country_name is None else country_name}",
            "group": None
            if country_name is None or len(match_lst_date_sorted) == 0
            else Participant.objects.get(name__icontains=country_name).group.name,
        },
    )


def MyBetView(request):
    """Ciew to place user's match score bets"""

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
            tournament_form = getTournamentForm(user=request.user)

        if "submit" in request.POST:
            # Matches
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
                        if searched_match.phase != "group" and bet_a == bet_b:
                            errors[i] = {"bet_a & bet_b": "Matches after the group-phase cannot end in a tie!"}
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

            # Groups
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

            # Tournament
            if "Tournament" in request.POST["submit"]:
                tournament_form = TournamentBetForm(data=request.POST, prefix="tournament")
                tournament_form.is_valid()

                tournament_update_kwargs = {}
                if "charity" in tournament_form.cleaned_data:
                    tournament_update_kwargs["charity"] = tournament_form.cleaned_data["charity"]
                if "bet" in tournament_form.cleaned_data:
                    tournament_update_kwargs["winner"] = tournament_form.cleaned_data["bet"]
                if len(tournament_update_kwargs) > 0:
                    tournament_id = tournament_form.cleaned_data["tournament_id"]
                    searched_tournament = Tournament.objects.get(pk=tournament_id)
                    if searched_tournament.is_editable is False:
                        tournament_update_kwargs.pop("winner", None)
                    bet_obj = TournamentBet.objects.filter(user=request.user, tournament=searched_tournament)
                    if len(bet_obj) > 0:
                        bet_obj = bet_obj[0]
                        for field, value in tournament_update_kwargs.items():
                            setattr(bet_obj, field, value)
                        bet_obj.save()
                    else:
                        TournamentBet(
                            user=request.user, tournament=searched_tournament, **tournament_update_kwargs
                        ).save()

            # Fetch updated pre-filled forms
            match_formset = getMatchBetFormSet(user=request.user, prefix="matches")
            group_formset = getGroupBetFormSet(user=request.user, prefix="groups")
            tournament_form = getTournamentForm(user=request.user)

    # View/Edit Request
    else:
        match_formset = getMatchBetFormSet(user=request.user, prefix="matches")
        group_formset = getGroupBetFormSet(user=request.user, prefix="groups")
        tournament_form = getTournamentForm(user=request.user)

    return render(
        request,
        "predictions.html",
        {
            "match_formset": match_formset,
            "group_formset": group_formset,
            "tournament_form": tournament_form,
            "stake_received": request.user.has_paid,
            "email_verified": request.user.is_verified,
            "errors": errors,
            "user_name": "-/-" if user_data is None else user_data["user__username"],
            "user_rank": "-/-" if user_data is None else user_data["rank"],
            "user_points": "-/-" if user_data is None else user_data["total_points"],
            "edit": True,
        },
    )


def OthersBetView(request, other_user_id):
    """Ciew to place user's match score bets"""

    # Not logged-in
    if request.user.id is None:
        return redirect("log-in")

    print(f"Get OthersBetView with other_user_id={other_user_id}.")

    other_user_obj = CustomUser.objects.get(pk=other_user_id)
    user_data = getMyScore(pk=other_user_id)

    # View Request
    match_formset = getMatchBetFormSet(user=other_user_obj, prefix="matches", only_not_editable=True)
    group_formset = getGroupBetFormSet(user=other_user_obj, prefix="groups", only_not_editable=True)
    tournament_form = getTournamentForm(user=other_user_obj, charity_editable=False)

    return render(
        request,
        "predictions.html",
        {
            "match_formset": match_formset,
            "group_formset": group_formset,
            "tournament_form": tournament_form,
            "stake_received": other_user_obj.has_paid,
            "email_verified": other_user_obj.is_verified,
            "errors": None,
            "user_name": user_data["user__username"],
            "user_rank": user_data["rank"],
            "user_points": "-/-" if user_data["total_points"] is None else user_data["total_points"],
            "edit": False,
        },
    )


def getLeaderboard():
    """Generate leaderboard table"""
    final_ranking = cache.get("leaderboard_data", None)
    if final_ranking is None:
        print("Get latest leaderboard")
        combined = {
            user.pk: {
                "user__username": user.username,
                "user__pk": user.pk,
                "user__team": user.team,
                "total_points": None,
            }
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
            TournamentBet.objects.filter(points__isnull=False)
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
            combined.values(),
            key=lambda d: f'00-{d["user__username"]}'
            if d["total_points"] is None
            else f'{d["total_points"]+1:02d}-{d["user__username"]}',
            reverse=True,
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

        cache.set("leaderboard_data", final_ranking, timeout=settings.DYNAMIC_PAGE_CACHE_TIME)

    return final_ranking


def getMyScore(pk):
    """Get a user's score and ranking"""
    leaderboard = getLeaderboard()
    my_score = [i for i in leaderboard if i["user__pk"] == pk]
    return None if len(my_score) == 0 else my_score[0]


def LeaderboardView(request):
    """View to show leaderboard of users - who predicted the matches best"""
    print("Get LeaderboardView.")

    return render(
        request, "leaderboard.html", {"ranking": getLeaderboard(), "logged_in": request.user.is_authenticated}
    )


def getOthersNonMatchPredictions(level, filter):
    grouped_queryset = cache.get(f"predictions_nonmatch_{level}_{filter}", None)
    title = f"{filter} Predictions"

    if grouped_queryset is None:
        print(f"Get latest predictions for {level}={filter}")
        if level == "group":
            level_obj = Group.objects.filter(name=filter)
            if len(level_obj) > 0 and level_obj[0].is_editable is False:
                level_obj = level_obj[0]
                queryset = GroupBet.objects.filter(group=level_obj).order_by("-points", "winner", "user__username")
            else:
                queryset = []
        elif level == "tournament":
            level_obj = Tournament.objects.filter(name=filter)
            if len(level_obj) > 0 and level_obj[0].is_editable is False:
                level_obj = level_obj[0]
                queryset = TournamentBet.objects.filter(tournament=level_obj, winner__isnull=False).order_by(
                    "-points", "winner", "user__username"
                )
            else:
                queryset = []

        grouped_queryset = {}
        for bet in queryset:
            winner_name = bet.winner.name
            if winner_name not in grouped_queryset:
                grouped_queryset[winner_name] = []
            grouped_queryset[winner_name].append(
                {
                    "user__id": bet.user.id,
                    "user__username": bet.user.username,
                    "user__team": bet.user.team,
                    "points": bet.points,
                }
            )

        cache.set(
            f"predictions_nonmatch_{level}_{filter}",
            grouped_queryset,
            timeout=settings.STATIC_PAGE_CACHE_TIME,
        )

    return {"title": title, "predictions": grouped_queryset, "type": level}


def getOthersMatchPredictions(match_id):
    out = cache.get(f"predictions_match_{match_id}", None)

    if out is None:
        print(f"Get latest predictions for match={match_id}")
        match_obj = Match.objects.get(pk=match_id)
        title = f'{match_obj.match_time.strftime("%a %d %b")} ({match_obj.team_a.group.name if match_obj.phase == "group" else MATCH_PHASES_DICT[match_obj.phase]}): {match_obj.team_a_placeholder} vs. {match_obj.team_b_placeholder} Predictions'
        if match_obj.is_editable is False:
            queryset = (
                MatchBet.objects.filter(match=match_obj)
                .annotate(
                    winner=Case(
                        When(Q(score_a__gt=F("score_b")), then=1),
                        When(Q(score_b__gt=F("score_a")), then=-1),
                        default=0,
                        output_field=models.IntegerField(),
                    )
                )
                .annotate(
                    winner_score=Case(
                        When(Q(winner=1), then=-F("score_a")),
                        When(Q(winner=-1), then=F("score_b")),
                        default=-F("score_a"),
                        output_field=models.IntegerField(),
                    )
                )
                .annotate(
                    loser_score=Case(
                        When(Q(winner=1), then=-F("score_b")),
                        When(Q(winner=-1), then=F("score_a")),
                        default=-F("score_b"),
                        output_field=models.IntegerField(),
                    )
                )
                .order_by("-winner", "winner_score", "loser_score", "user__username")
            )
            has_match_score = match_obj.score_a is not None and match_obj.score_b is not None
            if has_match_score and match_obj.score_a < match_obj.score_b:
                queryset = queryset.reverse()
            predictions = []
            prev_section = 1 if has_match_score is False or match_obj.score_a >= match_obj.score_b else -1
            match_was_added = False
            for bet in queryset:
                if (
                    has_match_score
                    and match_was_added is False
                    and (
                        ((bet.score_a < match_obj.score_a) and (bet.winner != -1 or bet.score_b == match_obj.score_b))
                        or (
                            (bet.score_b < match_obj.score_b) and (bet.winner == -1 or bet.score_a == match_obj.score_a)
                        )
                    )
                ):
                    predictions.append(
                        {
                            "user__id": None,
                            "user__username": f"MATCH: {match_obj.team_a_placeholder} vs. {match_obj.team_b_placeholder}",
                            "user__team": None,
                            "points": "-/-",
                            "goal_difference": 0,
                            "score_a": match_obj.score_a,
                            "score_b": match_obj.score_b,
                            "is_match": True,
                        }
                    )
                    match_was_added = True
                curr_section = 0 if bet.score_a == bet.score_b else (1 if bet.score_a > bet.score_b else -1)
                predictions.append(
                    {
                        "user__id": bet.user.id,
                        "user__username": bet.user.username,
                        "user__team": bet.user.team,
                        "points": "-/-" if bet.points is None else bet.points,
                        "goal_difference": bet.goal_difference,
                        "score_a": bet.score_a,
                        "score_b": bet.score_b,
                        "is_match": False,
                        "is_new_section": curr_section != prev_section,
                    }
                )
                prev_section = curr_section
        else:
            predictions = []

        out = {
            "title": title,
            "predictions": predictions,
            "flag_a": match_obj.team_a.flag,
            "flag_b": match_obj.team_b.flag,
        }

        cache.set(
            f"predictions_match_{match_id}",
            out,
            timeout=settings.STATIC_PAGE_CACHE_TIME,
        )

    return out


def OthersGroupPredictionsView(request, group_name):
    """View to see other users' group winner preditions"""
    # Not logged-in
    if request.user.id is None:
        return redirect("log-in")

    print(f"Get OthersGroupPredictionsView with group_name={group_name}.")
    return render(
        request, "predictions/GroupAndTournament.html", getOthersNonMatchPredictions(level="group", filter=group_name)
    )


def OthersTournamentPredictionsView(request, tournament_name):
    """View to see other users' tournament winner preditions"""
    # Not logged-in
    if request.user.id is None:
        return redirect("log-in")

    print(f"Get OthersTournamentPredictionsView with tournament_name={tournament_name}.")
    return render(
        request,
        "predictions/GroupAndTournament.html",
        getOthersNonMatchPredictions(level="tournament", filter=tournament_name),
    )


def OthersMatchPredictionsView(request, match_id):
    """View to see other users' match preditions"""
    # Not logged-in
    if request.user.id is None:
        return redirect("log-in")

    print(f"Get OthersMatchPredictionsView with match_id={match_id}.")
    return render(request, "predictions/Match.html", getOthersMatchPredictions(match_id=match_id))
