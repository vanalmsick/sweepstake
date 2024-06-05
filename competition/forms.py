# -*- coding: utf-8 -*-
from django import forms
from django.forms import formset_factory
import datetime
from django.conf import settings
from .models import Match, Bet


class BetForm(forms.Form):
    """Single match bet from e.g. X plays agains Y what does score does user Z predict"""

    match_id = forms.IntegerField(label=False)
    match_time = forms.CharField(label=False)

    flag_a = forms.URLField(label=False)
    team_a = forms.CharField(label=False)
    bet_a = forms.IntegerField(label=False)
    score_a = forms.IntegerField(label=False)
    score_b = forms.IntegerField(label=False)
    bet_b = forms.IntegerField(label=False)
    team_b = forms.CharField(label=False)
    flag_b = forms.URLField(label=False)

    text = forms.CharField(label=False)
    editable = forms.BooleanField(label=False)

    # match_id.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal'})
    # match_time.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal fw-bold'})
    # team_a.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal', 'style': 'text-align:right;'})
    # team_b.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal', 'style': 'text-align:left;'})
    # score_a.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal', 'style': 'text-align:center;'})
    # score_b.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal', 'style': 'text-align:center;'})
    bet_a.widget.attrs.update({"class": "form-control", "style": "text-align:center;"})
    bet_b.widget.attrs.update({"class": "form-control", "style": "text-align:center;"})
    # my_points.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal fst-italic text-secondary', 'style': 'text-align:left;'})


BetFormSet = formset_factory(BetForm, extra=0)


def __days_hours_minutes(td):
    """Convert datetime timedelta into day, hour, minute ints"""
    return td.days, td.seconds // 3600, (td.seconds // 60) % 60


def getBetFormSet(user):
    """Formset creator to list all matches to bet on"""
    data = Match.objects.all().order_by("match_time")
    formset_data = []
    remaining_time_used = False
    for data_i in data:
        bet_i = Bet.objects.filter(match=data_i, user=user).first()
        now = settings.TIME_ZONE_OBJ.localize(datetime.datetime.now())
        editable = now < data_i.match_time
        bet_placed = bet_i is not None and bet_i.score_a is not None and bet_i.score_b is not None
        score_entered = data_i.score_a is not None and data_i.score_b is not None
        points = None if bet_i is None else bet_i.points

        if editable:
            if remaining_time_used:
                text = ""
            else:
                remaining_days, remaining_hours, remaining_minutes = __days_hours_minutes(data_i.match_time - now)
                if remaining_days > 0:
                    text = f"{remaining_days} days left to place bet"
                elif remaining_hours > 0:
                    text = f"{remaining_hours} hours left to place bet"
                else:
                    text = f"{remaining_minutes} minutes left to place bet"
                remaining_time_used = True
        else:
            if points is None:
                if bet_placed:
                    if score_entered:
                        text = "ERROR"
                    else:
                        text = "Waiting for score"
                else:
                    text = "No bet placed"
            else:
                text = f"My Points: {points}"

        formset_data.append(
            {
                "match_id": data_i.pk,
                "match_time": data_i.match_time.strftime("%a %d %B - %H:%M"),
                "flag_a": "https://panenka.uefa.com/panenka/assets/ntc-generic-badge-02.svg"
                if data_i.team_a is None
                else data_i.team_a.flag,
                "team_a": data_i.team_a_placeholder if data_i.team_a is None else data_i.team_a,
                "score_a": data_i.score_a,
                "team_b": data_i.team_b_placeholder if data_i.team_b is None else data_i.team_b,
                "flag_b": "https://panenka.uefa.com/panenka/assets/ntc-generic-badge-04.svg"
                if data_i.team_b is None
                else data_i.team_b.flag,
                "score_b": data_i.score_b,
                "bet_a": (None if editable else "-") if bet_i is None else bet_i.score_a,
                "bet_b": (None if editable else "-") if bet_i is None else bet_i.score_b,
                "text": text,
                "editable": editable,
            }
        )

    formset_obj = BetFormSet(initial=formset_data)
    return formset_obj
