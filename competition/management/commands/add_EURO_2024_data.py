# -*- coding: utf-8 -*-
from django.core.management import BaseCommand

from competition.models import Tournament, Group, Participant, Match


class Command(BaseCommand):
    """Add EURO 2024 match data"""

    # Show this when the user types help
    help = "Adds EURO 2024 match data"

    def handle(self, *args, **options):
        """Actual Commandline executed function when manage.py command is called"""
        tournament_obj = Tournament(name="UEFA EURO 2024")
        tournament_obj.save()

        group_obj_dict = {}
        for grp_i in ["A", "B", "C", "D", "E", "F"]:
            group_obj = Group(tournament=tournament_obj, name=f"Group {grp_i}")
            group_obj.save()

            group_obj_dict[grp_i] = group_obj

        participant_data = [
            {"name": "Albania", "flag": "https://img.uefa.com/imgml/flags/50x50/ALB.png", "group": group_obj_dict["B"]},
            {"name": "Austria", "flag": "https://img.uefa.com/imgml/flags/50x50/AUT.png", "group": group_obj_dict["D"]},
            {"name": "Belgium", "flag": "https://img.uefa.com/imgml/flags/50x50/BEL.png", "group": group_obj_dict["E"]},
            {"name": "Croatia", "flag": "https://img.uefa.com/imgml/flags/50x50/CRO.png", "group": group_obj_dict["B"]},
            {"name": "Czechia", "flag": "https://img.uefa.com/imgml/flags/50x50/CZE.png", "group": group_obj_dict["F"]},
            {"name": "Denmark", "flag": "https://img.uefa.com/imgml/flags/50x50/DEN.png", "group": group_obj_dict["C"]},
            {"name": "England", "flag": "https://img.uefa.com/imgml/flags/50x50/ENG.png", "group": group_obj_dict["C"]},
            {"name": "France", "flag": "https://img.uefa.com/imgml/flags/50x50/FRA.png", "group": group_obj_dict["D"]},
            {"name": "Georgia", "flag": "https://img.uefa.com/imgml/flags/50x50/GEO.png", "group": group_obj_dict["F"]},
            {"name": "Germany", "flag": "https://img.uefa.com/imgml/flags/50x50/GER.png", "group": group_obj_dict["A"]},
            {"name": "Hungary", "flag": "https://img.uefa.com/imgml/flags/50x50/HUN.png", "group": group_obj_dict["A"]},
            {"name": "Italy", "flag": "https://img.uefa.com/imgml/flags/50x50/ITA.png", "group": group_obj_dict["B"]},
            {
                "name": "Netherlands",
                "flag": "https://img.uefa.com/imgml/flags/50x50/NED.png",
                "group": group_obj_dict["D"],
            },
            {"name": "Poland", "flag": "https://img.uefa.com/imgml/flags/50x50/POL.png", "group": group_obj_dict["D"]},
            {
                "name": "Portugal",
                "flag": "https://img.uefa.com/imgml/flags/50x50/POR.png",
                "group": group_obj_dict["F"],
            },
            {"name": "Romania", "flag": "https://img.uefa.com/imgml/flags/50x50/ROU.png", "group": group_obj_dict["E"]},
            {
                "name": "Scotland",
                "flag": "https://img.uefa.com/imgml/flags/50x50/SCO.png",
                "group": group_obj_dict["A"],
            },
            {"name": "Serbia", "flag": "https://img.uefa.com/imgml/flags/50x50/SRB.png", "group": group_obj_dict["C"]},
            {
                "name": "Slovakia",
                "flag": "https://img.uefa.com/imgml/flags/50x50/SVK.png",
                "group": group_obj_dict["E"],
            },
            {
                "name": "Slovenia",
                "flag": "https://img.uefa.com/imgml/flags/50x50/SVN.png",
                "group": group_obj_dict["C"],
            },
            {"name": "Spain", "flag": "https://img.uefa.com/imgml/flags/50x50/ESP.png", "group": group_obj_dict["B"]},
            {
                "name": "Switzerland",
                "flag": "https://img.uefa.com/imgml/flags/50x50/SUI.png",
                "group": group_obj_dict["A"],
            },
            {"name": "Türkiye", "flag": "https://img.uefa.com/imgml/flags/50x50/TUR.png", "group": group_obj_dict["F"]},
            {"name": "Ukraine", "flag": "https://img.uefa.com/imgml/flags/50x50/UKR.png", "group": group_obj_dict["E"]},
        ]

        participant_obj_dict = {}
        for part_i in participant_data:
            participant_obj = Participant(**part_i)
            participant_obj.save()

            participant_obj_dict[part_i["name"]] = participant_obj

        match_data = [
            #### 14th ####
            {
                "phase": "group",
                "match_time": "2024-06-14T20:00+01:00",
                "team_a": participant_obj_dict["Germany"],
                "team_b": participant_obj_dict["Scotland"],
                "tv_broadcaster": "ITV",
            },
            #### 15th ####
            {
                "phase": "group",
                "match_time": "2024-06-15T14:00+01:00",
                "team_a": participant_obj_dict["Hungary"],
                "team_b": participant_obj_dict["Switzerland"],
                "tv_broadcaster": "ITV",
            },
            {
                "phase": "group",
                "match_time": "2024-06-15T17:00+01:00",
                "team_a": participant_obj_dict["Spain"],
                "team_b": participant_obj_dict["Croatia"],
                "tv_broadcaster": "ITV",
            },
            {
                "phase": "group",
                "match_time": "2024-06-15T20:00+01:00",
                "team_a": participant_obj_dict["Italy"],
                "team_b": participant_obj_dict["Albania"],
                "tv_broadcaster": "BBC",
            },
            #### 16th ####
            {
                "phase": "group",
                "match_time": "2024-06-16T14:00+01:00",
                "team_a": participant_obj_dict["Poland"],
                "team_b": participant_obj_dict["Netherlands"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-16T17:00+01:00",
                "team_a": participant_obj_dict["Slovenia"],
                "team_b": participant_obj_dict["Denmark"],
                "tv_broadcaster": "ITV",
            },
            {
                "phase": "group",
                "match_time": "2024-06-16T20:00+01:00",
                "team_a": participant_obj_dict["Serbia"],
                "team_b": participant_obj_dict["England"],
                "tv_broadcaster": "BBC",
            },
            #### 17th ####
            {
                "phase": "group",
                "match_time": "2024-06-17T14:00+01:00",
                "team_a": participant_obj_dict["Romania"],
                "team_b": participant_obj_dict["Ukraine"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-17T17:00+01:00",
                "team_a": participant_obj_dict["Belgium"],
                "team_b": participant_obj_dict["Slovakia"],
                "tv_broadcaster": "ITV",
            },
            {
                "phase": "group",
                "match_time": "2024-06-17T20:00+01:00",
                "team_a": participant_obj_dict["Austria"],
                "team_b": participant_obj_dict["France"],
                "tv_broadcaster": "ITV",
            },
            #### 18th ####
            {
                "phase": "group",
                "match_time": "2024-06-18T17:00+01:00",
                "team_a": participant_obj_dict["Türkiye"],
                "team_b": participant_obj_dict["Georgia"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-18T20:00+01:00",
                "team_a": participant_obj_dict["Portugal"],
                "team_b": participant_obj_dict["Czechia"],
                "tv_broadcaster": "BBC",
            },
            #### 19th ####
            {
                "phase": "group",
                "match_time": "2024-06-19T14:00+01:00",
                "team_a": participant_obj_dict["Croatia"],
                "team_b": participant_obj_dict["Albania"],
                "tv_broadcaster": "ITV",
            },
            {
                "phase": "group",
                "match_time": "2024-06-19T17:00+01:00",
                "team_a": participant_obj_dict["Germany"],
                "team_b": participant_obj_dict["Hungary"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-19T20:00+01:00",
                "team_a": participant_obj_dict["Scotland"],
                "team_b": participant_obj_dict["Switzerland"],
                "tv_broadcaster": "BBC",
            },
            #### 20th ####
            {
                "phase": "group",
                "match_time": "2024-06-20T14:00+01:00",
                "team_a": participant_obj_dict["Slovenia"],
                "team_b": participant_obj_dict["Serbia"],
                "tv_broadcaster": "ITV",
            },
            {
                "phase": "group",
                "match_time": "2024-06-20T17:00+01:00",
                "team_a": participant_obj_dict["Denmark"],
                "team_b": participant_obj_dict["England"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-20T20:00+01:00",
                "team_a": participant_obj_dict["Spain"],
                "team_b": participant_obj_dict["Italy"],
                "tv_broadcaster": "ITV",
            },
            #### 21st ####
            {
                "phase": "group",
                "match_time": "2024-06-21T14:00+01:00",
                "team_a": participant_obj_dict["Slovakia"],
                "team_b": participant_obj_dict["Ukraine"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-21T17:00+01:00",
                "team_a": participant_obj_dict["Poland"],
                "team_b": participant_obj_dict["Austria"],
                "tv_broadcaster": "ITV",
            },
            {
                "phase": "group",
                "match_time": "2024-06-21T20:00+01:00",
                "team_a": participant_obj_dict["Netherlands"],
                "team_b": participant_obj_dict["France"],
                "tv_broadcaster": "BBC",
            },
            #### 22nd ####
            {
                "phase": "group",
                "match_time": "2024-06-22T14:00+01:00",
                "team_a": participant_obj_dict["Georgia"],
                "team_b": participant_obj_dict["Czechia"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-22T17:00+01:00",
                "team_a": participant_obj_dict["Türkiye"],
                "team_b": participant_obj_dict["Portugal"],
                "tv_broadcaster": "ITV",
            },
            {
                "phase": "group",
                "match_time": "2024-06-22T20:00+01:00",
                "team_a": participant_obj_dict["Belgium"],
                "team_b": participant_obj_dict["Romania"],
                "tv_broadcaster": "ITV",
            },
            #### 23rd ####
            {
                "phase": "group",
                "match_time": "2024-06-23T20:00+01:00",
                "team_a": participant_obj_dict["Switzerland"],
                "team_b": participant_obj_dict["Germany"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-23T20:00+01:00",
                "team_a": participant_obj_dict["Scotland"],
                "team_b": participant_obj_dict["Hungary"],
                "tv_broadcaster": "BBC",
            },
            #### 24th ####
            {
                "phase": "group",
                "match_time": "2024-06-24T20:00+01:00",
                "team_a": participant_obj_dict["Albania"],
                "team_b": participant_obj_dict["Spain"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-24T20:00+01:00",
                "team_a": participant_obj_dict["Croatia"],
                "team_b": participant_obj_dict["Italy"],
                "tv_broadcaster": "BBC",
            },
            #### 25th ####
            {
                "phase": "group",
                "match_time": "2024-06-25T17:00+01:00",
                "team_a": participant_obj_dict["Netherlands"],
                "team_b": participant_obj_dict["Austria"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-25T17:00+01:00",
                "team_a": participant_obj_dict["France"],
                "team_b": participant_obj_dict["Poland"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-25T20:00+01:00",
                "team_a": participant_obj_dict["England"],
                "team_b": participant_obj_dict["Slovenia"],
                "tv_broadcaster": "ITV",
            },
            {
                "phase": "group",
                "match_time": "2024-06-25T20:00+01:00",
                "team_a": participant_obj_dict["Denmark"],
                "team_b": participant_obj_dict["Serbia"],
                "tv_broadcaster": "ITV",
            },
            #### 26th ####
            {
                "phase": "group",
                "match_time": "2024-06-26T17:00+01:00",
                "team_a": participant_obj_dict["Slovakia"],
                "team_b": participant_obj_dict["Romania"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-26T17:00+01:00",
                "team_a": participant_obj_dict["Ukraine"],
                "team_b": participant_obj_dict["Belgium"],
                "tv_broadcaster": "BBC",
            },
            {
                "phase": "group",
                "match_time": "2024-06-26T20:00+01:00",
                "team_a": participant_obj_dict["Georgia"],
                "team_b": participant_obj_dict["Portugal"],
                "tv_broadcaster": "ITV",
            },
            {
                "phase": "group",
                "match_time": "2024-06-26T20:00+01:00",
                "team_a": participant_obj_dict["Czechia"],
                "team_b": participant_obj_dict["Türkiye"],
                "tv_broadcaster": "ITV",
            },
            #### 29th - Group Finals ####
            {
                "phase": "8",
                "match_time": "2024-06-29T17:00+01:00",
                "team_a_placeholder": "2nd Group A",
                "team_b_placeholder": "2nd Group B",
                "tv_broadcaster": "tbc",
            },
            {
                "phase": "8",
                "match_time": "2024-06-29T20:00+01:00",
                "team_a_placeholder": "1st Group A",
                "team_b_placeholder": "2nd Group C",
                "tv_broadcaster": "tbc",
            },
            #### 30th - Group Finals ####
            {
                "phase": "8",
                "match_time": "2024-06-30T17:00+01:00",
                "team_a_placeholder": "1st Group C",
                "team_b_placeholder": "3rd Group D/E/F",
                "tv_broadcaster": "tbc",
            },
            {
                "phase": "8",
                "match_time": "2024-06-30T20:00+01:00",
                "team_a_placeholder": "1st Group B",
                "team_b_placeholder": "3rd Group A/D/E/F",
                "tv_broadcaster": "tbc",
            },
            #### 1st - Group Finals ####
            {
                "phase": "8",
                "match_time": "2024-07-01T17:00+01:00",
                "team_a_placeholder": "2nd Group D",
                "team_b_placeholder": "2nd Group E",
                "tv_broadcaster": "tbc",
            },
            {
                "phase": "8",
                "match_time": "2024-07-01T20:00+01:00",
                "team_a_placeholder": "1st Group F",
                "team_b_placeholder": "3rd Group A/B/C",
                "tv_broadcaster": "tbc",
            },
            #### 2nd - Group Finals ####
            {
                "phase": "8",
                "match_time": "2024-07-02T17:00+01:00",
                "team_a_placeholder": "1st Group E",
                "team_b_placeholder": "3rd Group A/B/C/D",
                "tv_broadcaster": "tbc",
            },
            {
                "phase": "8",
                "match_time": "2024-07-02T20:00+01:00",
                "team_a_placeholder": "1st Group D",
                "team_b_placeholder": "2nd Group F",
                "tv_broadcaster": "tbc",
            },
            #### 5th - Quarter Finals ####
            {
                "phase": "4",
                "match_time": "2024-07-05T17:00+01:00",
                "team_a_placeholder": "W39",
                "team_b_placeholder": "W37",
                "tv_broadcaster": "tbc",
            },
            {
                "phase": "4",
                "match_time": "2024-07-05T20:00+01:00",
                "team_a_placeholder": "W41",
                "team_b_placeholder": "W42",
                "tv_broadcaster": "tbc",
            },
            #### 6th - Quarter Finals ####
            {
                "phase": "4",
                "match_time": "2024-07-06T17:00+01:00",
                "team_a_placeholder": "W40",
                "team_b_placeholder": "W38",
                "tv_broadcaster": "tbc",
            },
            {
                "phase": "4",
                "match_time": "2024-07-06T20:00+01:00",
                "team_a_placeholder": "W43",
                "team_b_placeholder": "W44",
                "tv_broadcaster": "tbc",
            },
            #### 9th - Semi Finals ####
            {
                "phase": "2",
                "match_time": "2024-07-09T20:00+01:00",
                "team_a_placeholder": "W45",
                "team_b_placeholder": "W46",
                "tv_broadcaster": "tbc",
            },
            #### 10th - Semi Finals ####
            {
                "phase": "2",
                "match_time": "2024-07-10T20:00+01:00",
                "team_a_placeholder": "W47",
                "team_b_placeholder": "W48",
                "tv_broadcaster": "tbc",
            },
            #### 14th - Finals ####
            {
                "phase": "1",
                "match_time": "2024-07-14T20:00+01:00",
                "team_a_placeholder": "W49",
                "team_b_placeholder": "W50",
                "tv_broadcaster": "BBC & ITV",
            },
        ]

        for match_i in match_data:
            match_obj = Match(**match_i)
            match_obj.save()
