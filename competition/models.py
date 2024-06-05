# -*- coding: utf-8 -*-
from django.db import models
from django.db.models import Q

from general.models import CustomUser


# Create your models here.
class Tournament(models.Model):
    """Tournament - the highest level e.g. Football World Cup 2024"""

    name = models.CharField(max_length=30)

    first_match_time = models.DateTimeField(null=True, blank=True)  # type: ignore

    @property  # type: ignore
    def first_match_time(self):
        return (
            Match.objects.filter(Q(team_a__group__tournament__pk=self.pk) | Q(team_b__group__tournament__pk=self.pk))
            .order_by("match_time")
            .first()
            .match_time
        )

    def __str__(self):
        return f"{self.name}"


class Group(models.Model):
    """2nd highest level for grouping Tournament participants for group-phase"""

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=False, blank=False)
    name = models.CharField(max_length=30)

    first_match_time = models.DateTimeField(null=True, blank=True)  # type: ignore

    @property  # type: ignore
    def first_match_time(self):
        return (
            Match.objects.filter(Q(team_a__group__pk=self.pk) | Q(team_b__group__pk=self.pk))
            .order_by("match_time")
            .first()
            .match_time
        )

    def __str__(self):
        return f"{self.name}"


MATCH_PHASES = [
    ("group", "Group Phase"),
    ("8", "Group Finals"),
    ("4", "Quarter Finals"),
    ("2", "Semi Finals"),
    ("1", "Finals"),
]


class Participant(models.Model):
    """Tournament Participants e.g. countries like Germany, UK, France, etc."""

    name = models.CharField(max_length=30)
    flag = models.URLField(max_length=300)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name}"


class Match(models.Model):
    """Scheduled Matches e.g. on Sunday at 6pm X plays against Y"""

    phase = models.CharField(max_length=5, choices=MATCH_PHASES, null=False, blank=False)
    match_time = models.DateTimeField(null=False, blank=False)

    team_a = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name="team_a")
    team_a_placeholder = models.CharField(max_length=30, null=True, blank=True)
    score_a = models.IntegerField(null=True, blank=True)
    team_b = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name="team_b")
    team_b_placeholder = models.CharField(max_length=30, null=True, blank=True)
    score_b = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.match_time} ({self.phase.upper()}) {self.team_a_placeholder if self.team_a is None else self.team_a} - {self.team_b_placeholder if self.team_b is None else self.team_b}"

    def save(self, *args, **kwargs):
        # Update placeholder texts
        if self.team_a is not None:
            self.team_a_placeholder = self.team_a.name
        if self.team_b is not None:
            self.team_b_placeholder = self.team_b.name

        super(Match, self).save(*args, **kwargs)

        # Update bet points
        for bet in self.bet_set.all():
            bet_points = bet.get_points()
            setattr(bet, "points", bet_points)
            bet.save()


class Bet(models.Model):
    """Single bet placed by user X on match Y that the score will be A:B"""

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=False, blank=False, primary_key=False)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, null=False, blank=False, primary_key=False)

    score_a = models.IntegerField(null=True, blank=True)
    score_b = models.IntegerField(null=True, blank=True)

    points = models.IntegerField(null=True, blank=False)

    def get_points(self):
        """FUnction to calculate points awareded from bet - i.e. how correct was the betted score"""
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
        # no team won and taht was predicted
        elif self.match.score_a == self.match.score_b and self.score_a == self.score_b:
            return 3
        # no points
        else:
            return 0

    def save(self, *args, **kwargs):
        self.points = self.get_points()
        super(Bet, self).save(*args, **kwargs)
