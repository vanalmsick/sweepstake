# -*- coding: utf-8 -*-
import datetime
from django.db import models
from django.db.models import Q
from django.conf import settings

from general.models import CustomUser, delete_dynamic_cached_pages


# Create your models here.
class EmptyStringToNoneField(models.CharField):
    """mode field to automatically transform empty strings to Null"""

    def get_prep_value(self, value):
        if value == "" or value == " ":
            return None
        return value


class Tournament(models.Model):
    """Tournament - the highest level e.g. Football World Cup 2024"""

    name = EmptyStringToNoneField(max_length=50, unique=True)

    first_place = models.ForeignKey(
        "Participant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        primary_key=False,
        related_name="tournament_first_place",
    )
    second_place = models.ForeignKey(
        "Participant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        primary_key=False,
        related_name="tournament_second_place",
    )
    third_place = models.ForeignKey(
        "Participant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        primary_key=False,
        related_name="tournament_third_place",
    )

    @property
    def first_match_time(self):
        """get the time of the first tournament match for the property is_editable"""
        return (
            Match.objects.filter(Q(team_a__group__tournament__pk=self.pk) | Q(team_b__group__tournament__pk=self.pk))
            .order_by("match_time")
            .first()
            .match_time
        )

    @property
    def is_editable(self):
        """check if bet can still be placed or if first group match already started"""
        return settings.TIME_ZONE_OBJ.localize(datetime.datetime.now()) < self.first_match_time

    def __str__(self):
        """str print-out of model entry"""
        return f"{self.name}"

    def save(self, *args, **kwargs):
        """when saving also update the connected bets"""
        super(Tournament, self).save(*args, **kwargs)

        # Update bet points
        for bet in self.tournamentbet_set.all():
            bet_points = bet.get_points()
            setattr(bet, "points", bet_points)
            bet.save()

        # Update cached pages
        delete_dynamic_cached_pages(prefix_lst=["leaderboard_data", "predictions_nonmatch_"])


class Group(models.Model):
    """2nd highest level for grouping Tournament participants for group-phase"""

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=False, blank=False)
    name = EmptyStringToNoneField(max_length=30, unique=True)

    winner = models.ForeignKey(
        "Participant", on_delete=models.SET_NULL, null=True, blank=True, primary_key=False, related_name="group_winner"
    )

    @property
    def first_match_time(self):
        """get the time of the first group match for the property is_editable"""
        return (
            Match.objects.filter(Q(team_a__group__pk=self.pk) | Q(team_b__group__pk=self.pk))
            .order_by("match_time")
            .first()
            .match_time
        )

    @property
    def is_editable(self):
        """check if bet can still be placed or if first group match already started"""
        return settings.TIME_ZONE_OBJ.localize(datetime.datetime.now()) < self.first_match_time

    class Meta:
        unique_together = (
            "tournament",
            "name",
        )

    def __str__(self):
        """str print-out of model entry"""
        return f"{self.name}"

    def save(self, *args, **kwargs):
        """when saving also update the connected bets"""
        super(Group, self).save(*args, **kwargs)

        # Update bet points
        for bet in self.groupbet_set.all():
            bet_points = bet.get_points()
            setattr(bet, "points", bet_points)
            bet.save()

        # Update cached pages
        delete_dynamic_cached_pages(prefix_lst=["leaderboard_data", "predictions_nonmatch_"])


MATCH_PHASES_DICT = {
    "group": "Group Phase",
    "8": "Round of 16",
    "4": "Quarter Finals",
    "2": "Semi Finals",
    "1": "Finals",
}


MATCH_PHASES = [(k, v) for k, v in MATCH_PHASES_DICT.items()]

BROADCASTERS = [("BBC", "BBC"), ("ITV", "ITV"), ("BBC & ITV", "BBC & ITV"), ("tbc", "tbc")]
BROADCASTER_URLS = {
    "BBC": "https://www.bbc.co.uk/sport/football",
    "ITV": "https://www.itv.com/watch",
    "BBC & ITV": "https://www.bbc.co.uk/sport/football",
    "tbc": None,
    None: None,
}


class Participant(models.Model):
    """Tournament Participants e.g. countries like Germany, UK, France, etc."""

    name = EmptyStringToNoneField(max_length=40, unique=True)
    flag = models.URLField(max_length=300)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        """str print-out of model entry"""
        return f"{self.name}"


class Match(models.Model):
    """Scheduled Matches e.g. on Sunday at 6pm X plays against Y"""

    phase = EmptyStringToNoneField(max_length=5, choices=MATCH_PHASES, null=False, blank=False)
    match_time = models.DateTimeField(null=False, blank=False)
    tv_broadcaster = EmptyStringToNoneField(max_length=9, choices=BROADCASTERS, null=True, blank=True)

    team_a = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name="team_a")
    team_a_placeholder = EmptyStringToNoneField(max_length=40, null=True, blank=True)
    score_a = models.IntegerField(null=True, blank=True)
    team_b = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name="team_b")
    team_b_placeholder = EmptyStringToNoneField(max_length=40, null=True, blank=True)
    score_b = models.IntegerField(null=True, blank=True)

    api_match_id = models.IntegerField(null=True, blank=False)
    api_match_data = models.JSONField(null=True, blank=False)

    @property
    def is_editable(self):
        """check if bet can still be placed or if match already started"""
        return settings.TIME_ZONE_OBJ.localize(datetime.datetime.now()) < self.match_time

    def __str__(self):
        """str print-out of model entry"""
        return f"{self.match_time} ({self.phase.upper()}) {self.team_a_placeholder if self.team_a is None else self.team_a} - {self.team_b_placeholder if self.team_b is None else self.team_b}"

    def save(self, *args, **kwargs):
        """when saving also update the connected bets and placeholder team names"""
        # Update placeholder texts
        if self.team_a is not None:
            self.team_a_placeholder = self.team_a.name
        if self.team_b is not None:
            self.team_b_placeholder = self.team_b.name

        super(Match, self).save(*args, **kwargs)

        # Update bet points
        for bet in self.matchbet_set.all():
            bet_points = bet.get_points()
            setattr(bet, "points", bet_points)
            goal_difference = bet.get_goal_difference()
            setattr(bet, "goal_difference", goal_difference)
            bet.save()

        # Update cached pages
        delete_dynamic_cached_pages()


class MatchBet(models.Model):
    """Single bet placed by user X on match Y that the score will be A:B"""

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=False, blank=False, primary_key=False)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, null=False, blank=False, primary_key=False)

    score_a = models.IntegerField(null=True, blank=True)
    score_b = models.IntegerField(null=True, blank=True)

    points = models.IntegerField(null=True, blank=False)
    goal_difference = models.IntegerField(null=True, blank=False)

    class Meta:
        unique_together = (
            "user",
            "match",
        )

    def get_points(self):
        """Function to calculate points awareded from bet - i.e. how correct was the betted score"""
        # no match results
        if self.match.score_a is None or self.match.score_b is None:
            return None
        # no bet
        elif self.score_a is None or self.score_b is None:
            return 0
        # correct predicted score
        elif self.match.score_a == self.score_a and self.match.score_b == self.score_b:
            return 5
        # team a won and a was predicted
        elif self.match.score_a > self.match.score_b and self.score_a > self.score_b:
            return 3
        # team b won and b was predicted
        elif self.match.score_a < self.match.score_b and self.score_a < self.score_b:
            return 3
        # no team won and that was predicted
        elif self.match.score_a == self.match.score_b and self.score_a == self.score_b:
            return 3
        # no points
        else:
            return 0

    def get_goal_difference(self):
        """Function for leaderboard sorting of goal difference"""
        # Bet - Match Score
        return (
            (abs(self.score_a - self.match.score_a) + abs(self.score_b - self.match.score_b))
            if self.score_a is not None
            and self.score_b is not None
            and self.match.score_a is not None
            and self.match.score_b is not None
            else None
        )

    def save(self, *args, **kwargs):
        """when saving also update the scored points from the connected bets"""
        self.points = self.get_points()
        super(MatchBet, self).save(*args, **kwargs)


class GroupBet(models.Model):
    """Single bet placed by user X on winner of group Y"""

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=False, blank=False, primary_key=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=False, blank=False, primary_key=False)

    winner = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        primary_key=False,
        related_name="group_winner_bet",
    )

    points = models.IntegerField(null=True, blank=False)

    class Meta:
        unique_together = (
            "user",
            "group",
        )

    def get_points(self):
        """Function to calculate points awareded from bet - i.e. how correct was the betted score"""
        # no match results
        if self.group.winner is None:
            return None
        # correct bet
        elif self.winner == self.group.winner:
            return 8
        # no points
        else:
            return 0

    def save(self, *args, **kwargs):
        """when saving also update the scored points from the connected bets"""
        self.points = self.get_points()
        super(GroupBet, self).save(*args, **kwargs)


class TournamentBet(models.Model):
    """Bet who wins the tournament placed by user X"""

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=False, blank=False, primary_key=False)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=False, blank=False, primary_key=False)

    winner = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        primary_key=False,
        related_name="tournament_winner_bet",
    )
    charity = EmptyStringToNoneField(max_length=30, null=True, blank=True)

    points = models.IntegerField(null=True, blank=False)

    class Meta:
        unique_together = (
            "user",
            "tournament",
        )

    def get_points(self):
        """Function to calculate points awareded from bet - i.e. how correct was the betted score"""
        # no match results
        if self.tournament.first_place is None and self.tournament.second_place is None:
            return None
        # bet equals 1st place
        elif self.tournament.first_place is not None and self.winner == self.tournament.first_place:
            return 25
        # bet equals 2nd place
        elif self.tournament.second_place is not None and self.winner == self.tournament.second_place:
            return 15
        # # bet equals 3rd place
        # elif self.winner == self.tournament.third_place:
        #     return 10
        # no points
        else:
            return 0

    def save(self, *args, **kwargs):
        """when saving also update the scored points from the connected bets"""
        self.points = self.get_points()
        super(TournamentBet, self).save(*args, **kwargs)
