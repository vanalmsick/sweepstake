# -*- coding: utf-8 -*-
from django import forms
from django.forms import formset_factory
import datetime
import random
from django.conf import settings

# from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Match, MatchBet, Group, GroupBet, Participant, TournamentBet, Tournament, MATCH_PHASES_DICT


def __days_hours_minutes(td):
    """Convert datetime timedelta into day, hour, minute ints"""
    return td.days, td.seconds // 3600, (td.seconds // 60) % 60


def __random_score_generator(tie=True):
    """Function that generates reasonable match scores"""
    while True:
        population = {
            "0-0": 7.5,
            "1-0": 20.0,
            "1-1": 10.0,
            "2-0": 20.0,
            "2-1": 15.0,
            "3-0": 10.0,
            "3-1": 5.0,
            "2-2": 10.0,
            "4-0": 2.5,
        }
        result = random.choices(list(population.keys()), weights=list(population.values()), k=1)[0]
        result_a, result_b = result.split("-")
        if tie or result_a != result_b:
            direction = random.randint(0, 1)
            return (int(result_a), int(result_b)) if direction == 0 else (int(result_b), int(result_a))


class GroupBetForm(forms.Form):
    """Single group bet form e.g. X will win group Y"""

    def __init__(self, *args, **kwargs):
        super(GroupBetForm, self).__init__(*args, **kwargs)
        ADDITIONAL_CHOICES = (
            [
                (i.pk, i.name)
                for i in Participant.objects.filter(group_id=kwargs["initial"]["group_id"]).order_by("name")
            ]
            if "initial" in kwargs
            else []
        )
        self.fields["bet"] = forms.CharField(
            label=False, widget=forms.Select(choices=[("", "--- Select Favorite ---")] + ADDITIONAL_CHOICES)
        )
        self.fields["bet"].widget.attrs.update({"class": "form-control", "style": "text-align:center;"})

    group_id = forms.IntegerField(label=False)
    group_name = forms.CharField(label=False, required=False)
    first_match_time = forms.CharField(label=False, required=False)

    flag_1 = forms.URLField(label=False, required=False)
    flag_2 = forms.URLField(label=False, required=False)
    flag_3 = forms.URLField(label=False, required=False)
    flag_4 = forms.URLField(label=False, required=False)

    bet = forms.CharField(label=False, widget=forms.Select(choices=[("", "---------")]))
    winner = forms.CharField(label=False, required=False)

    text = forms.CharField(label=False, required=False)
    editable = forms.BooleanField(label=False, required=False)

    group_id.widget.attrs.update({"style": "display: none;visibility: hidden; height: 0; width: 0;"})
    bet.widget.attrs.update({"class": "form-control", "style": "text-align:center;"})


GroupBetFormSet = formset_factory(GroupBetForm, extra=0)


def getGroupBetFormSet(user, prefix=None, only_not_editable=False):
    """Formset creator to list all groups to bet on"""
    data = Group.objects.all().order_by("name")
    now = settings.TIME_ZONE_OBJ.localize(datetime.datetime.now())
    formset_data = []

    for data_i in data:
        editable = now < data_i.first_match_time
        if only_not_editable is False or editable is False:
            bet_i = GroupBet.objects.filter(group=data_i, user=user).first()
            bet_placed = bet_i is not None and bet_i.winner is not None
            bet_winner = (
                (None if editable else "-/-") if bet_i is None else (bet_i.winner.pk if editable else bet_i.winner.name)
            )
            points = None if bet_i is None else bet_i.points

            if editable:
                remaining_days, remaining_hours, remaining_minutes = __days_hours_minutes(data_i.first_match_time - now)
                if remaining_days > 1:
                    text = f"{remaining_days} days left to place bet"
                elif remaining_days > 0:
                    text = "1 day left to place bet"
                elif remaining_hours > 1:
                    text = f"{remaining_hours} hours left to place bet"
                elif remaining_hours > 0:
                    text = f"1h {remaining_minutes}min left to place bet"
                else:
                    text = f"{remaining_minutes} minutes left to place bet"
            else:
                if points is None:
                    if bet_placed:
                        text = "Finger crossing 🤞"
                    else:
                        text = "No bet placed"
                else:
                    text = f"Points earned: {points}"

            flags = data_i.participant_set.all().order_by("name").values_list("flag")
            formset_data.append(
                {
                    "group_id": data_i.pk,
                    "group_name": data_i.name,
                    "first_match_time": data_i.first_match_time.astimezone(settings.TIME_ZONE_OBJ).strftime(
                        "%a %d %B - %H:%M"
                    ),
                    "bet": bet_winner,
                    "winner": data_i.winner,
                    "text": text,
                    "editable": editable,
                    "flag_1": flags[0][0],
                    "flag_2": flags[1][0],
                    "flag_3": flags[2][0],
                    "flag_4": flags[3][0],
                }
            )

    return GroupBetFormSet(initial=formset_data, prefix=prefix)


class MatchBetForm(forms.Form):
    """Single match bet form e.g. X plays against Y what does score does user Z predict"""

    match_id = forms.IntegerField(label=False)
    match_time = forms.CharField(label=False, required=False)
    phase = forms.CharField(label=False, required=False)
    tv_broadcaster = forms.CharField(label=False, required=False)

    flag_a = forms.URLField(label=False, required=False)
    team_a = forms.CharField(label=False, required=False)
    bet_a = forms.IntegerField(label=False)  # , validators=[MinValueValidator(20), MinValueValidator(0)]
    score_a = forms.IntegerField(label=False, required=False)
    score_b = forms.IntegerField(label=False, required=False)
    bet_b = forms.IntegerField(label=False)  # , validators=[MinValueValidator(20), MinValueValidator(0)]
    team_b = forms.CharField(label=False, required=False)
    flag_b = forms.URLField(label=False, required=False)

    text = forms.CharField(label=False, required=False)
    editable = forms.BooleanField(label=False, required=False)

    match_id.widget.attrs.update({"style": "display: none;visibility: hidden; height: 0; width: 0;"})
    # match_time.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal fw-bold'})
    # team_a.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal', 'style': 'text-align:right;'})
    # team_b.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal', 'style': 'text-align:left;'})
    # score_a.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal', 'style': 'text-align:center;'})
    # score_b.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal', 'style': 'text-align:center;'})
    bet_a.widget.attrs.update({"class": "form-control", "style": "text-align:center;"})
    bet_b.widget.attrs.update({"class": "form-control", "style": "text-align:center;"})
    # my_points.widget.attrs.update({'readonly': True, 'class': 'w-100 input-normal fst-italic text-secondary', 'style': 'text-align:left;'})


MatchBetFormSet = formset_factory(MatchBetForm, extra=0)


def getMatchBetFormSet(user, random=False, prefix=None, only_not_editable=False):
    """Formset creator to list all matches to bet on"""
    data = Match.objects.all().order_by("match_time")
    now = settings.TIME_ZONE_OBJ.localize(datetime.datetime.now())
    if only_not_editable:
        data = data.filter(match_time__lte=now)
    missing_bets = len(data.filter(match_time__gte=now, matchbet__isnull=True))
    formset_data = []
    remaining_time_used = None
    for data_i in data:
        bet_i = MatchBet.objects.filter(match=data_i, user=user).first()
        editable = now < data_i.match_time
        bet_placed = bet_i is not None and bet_i.score_a is not None and bet_i.score_b is not None
        score_entered = data_i.score_a is not None and data_i.score_b is not None
        points = None if bet_i is None else bet_i.points

        if editable:
            if remaining_time_used is not None and remaining_time_used != data_i.match_time.date():
                text = ""
            else:
                remaining_days, remaining_hours, remaining_minutes = __days_hours_minutes(data_i.match_time - now)
                if remaining_days > 1:
                    text = f"{remaining_days} days left to place bet"
                elif remaining_days > 0:
                    text = "1 day left to place bet"
                elif remaining_hours > 1:
                    text = f"{remaining_hours} hours left to place bet"
                elif remaining_hours > 0:
                    text = f"1h {remaining_minutes}min left to place bet"
                else:
                    text = f"{remaining_minutes-1} minutes left to place bet"
                remaining_time_used = data_i.match_time.date()
        else:
            if points is None:
                if bet_placed:
                    if score_entered:
                        text = "ERROR"
                    else:
                        text = "Finger crossing 🤞"
                else:
                    text = "No bet placed"
            else:
                text = f"Points earned: {points}"

        bet_a = (None if editable else "-") if bet_i is None else bet_i.score_a
        bet_b = (None if editable else "-") if bet_i is None else bet_i.score_b
        if editable and random:
            if bet_placed is False:
                bet_a, bet_b = __random_score_generator(tie=data_i.phase == "group")
                MatchBet(match=data_i, user=user, score_a=bet_a, score_b=bet_b).save()
            elif missing_bets == 0:
                bet_a, bet_b = __random_score_generator(tie=data_i.phase == "group")
                setattr(bet_i, "score_a", bet_a)
                setattr(bet_i, "score_b", bet_b)
                bet_i.save()

        formset_data.append(
            {
                "match_id": data_i.pk,
                "match_time": data_i.match_time.astimezone(settings.TIME_ZONE_OBJ).strftime("%a %d %B - %H:%M"),
                "tv_broadcaster": data_i.tv_broadcaster,
                "phase": data_i.team_a.group.name if data_i.phase == "group" else MATCH_PHASES_DICT[data_i.phase],
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
                "bet_a": bet_a,
                "bet_b": bet_b,
                "text": text,
                "editable": editable,
            }
        )

    return MatchBetFormSet(initial=formset_data, prefix=prefix)


class ListTextWidget(forms.TextInput):
    """Input field with suggested options but free text too"""

    def __init__(self, data_list, name, *args, **kwargs):
        super(ListTextWidget, self).__init__(*args, **kwargs)
        self._name = name
        self._list = data_list
        self.attrs.update({"list": "list__%s" % self._name})

    def render(self, name, value, attrs=None, renderer=None):
        text_html = super(ListTextWidget, self).render(name, value, attrs=attrs)
        data_list = '<datalist id="list__%s">' % self._name
        for item in self._list:
            data_list += '<option value="%s">' % item
        data_list += "</datalist>"

        return text_html + data_list


CHARITY_SUGGESTIONS = [
    "The Felix Project",
    "Children With Cancer UK",
    "The Climate Group",
    "WWF (UK)",
    "Right to Succeed",
]


class TournamentBetForm(forms.Form):
    """Single Tournament bet form e.g. X will win the Tournament"""

    tournament_id = forms.IntegerField(label=False)
    tournament_name = forms.CharField(label=False, required=False)
    first_match_time = forms.CharField(label=False, required=False)

    bet = forms.ModelChoiceField(label=False, required=False, queryset=Participant.objects.all().order_by("name"))
    winner = forms.CharField(label=False, required=False)

    charity = forms.CharField(label=False, required=False)

    text = forms.CharField(label=False, required=False)
    editable = forms.BooleanField(label=False, required=False)

    tournament_id.widget.attrs.update({"style": "display: none;visibility: hidden; height: 0; width: 0;"})
    bet.widget.attrs.update({"class": "form-control", "style": "text-align:center;"})

    def __init__(self, *args, **kwargs):
        _charity_list = kwargs.pop("data_list", None)
        _charity_editable = kwargs.pop("charity_editable", True)
        _editable = kwargs.get("initial", {"editable": None})["editable"]
        super(TournamentBetForm, self).__init__(*args, **kwargs)

        # the "name" parameter will allow you to use the same widget more than once in the same
        # form, not setting this parameter differently will cuse all inputs display the
        # same list.
        self.fields["charity"].widget = ListTextWidget(data_list=_charity_list, name="charity-list")
        self.fields["charity"].widget.attrs.update({"class": "form-control", "style": "text-align:center;"})
        if _editable is False:
            self.fields["bet"].widget.attrs.update({"disabled": True})
        if _charity_editable is False:
            self.fields["charity"].widget.attrs.update({"disabled": True})


def getTournamentForm(user, charity_editable=True):
    """Form creator to get tournament winner prediction and charity option"""
    tournament = Tournament.objects.all().first()
    tournament_bet = TournamentBet.objects.filter(user=user).first()

    winner = None if tournament is None else tournament.first_place
    editable = tournament.is_editable

    bet_placed = tournament_bet is not None and tournament_bet.winner is not None
    points = None if tournament_bet is None else tournament_bet.points

    if editable:
        now = settings.TIME_ZONE_OBJ.localize(datetime.datetime.now())
        remaining_days, remaining_hours, remaining_minutes = __days_hours_minutes(tournament.first_match_time - now)
        if remaining_days > 1:
            text = f"{remaining_days} days left to place bet"
        elif remaining_days > 0:
            text = "1 day left to place bet"
        elif remaining_hours > 1:
            text = f"{remaining_hours} hours left to place bet"
        elif remaining_hours > 0:
            text = f"1h {remaining_minutes}min left to place bet"
        else:
            text = f"{remaining_minutes} minutes left to place bet"
    else:
        if points is None:
            if bet_placed:
                text = "Finger crossing 🤞"
            else:
                text = "No bet placed"
        else:
            text = f"Winner: {winner} / Points earned: {points}"

    form_data = {
        "tournament_id": tournament.pk,
        "tournament_name": tournament.name,
        "first_match_time": tournament.first_match_time.astimezone(settings.TIME_ZONE_OBJ).strftime("%a %d %B - %H:%M"),
        "bet": None if tournament_bet is None else tournament_bet.winner,
        "winner": winner,
        "charity": None if tournament_bet is None else tournament_bet.charity,
        "text": text,
        "editable": editable,
    }
    return TournamentBetForm(
        initial=form_data, data_list=CHARITY_SUGGESTIONS, charity_editable=charity_editable, prefix="tournament"
    )
