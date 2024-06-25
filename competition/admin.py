# -*- coding: utf-8 -*-
from django.contrib import admin

from sweepstake.celery import app
from .models import Tournament, Group, Participant, Match
from .tasks import update_api_match_ids


# Register your models here.
class GroupsInline(admin.TabularInline):
    """Table of Groups to show in Tournament detail view - 2nd highest level for grouping Tournament participants for group-phase"""

    model = Group
    fk_name = "tournament"
    can_delete = False
    extra = 0


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """Admin view of Tournament - the highest level e.g. Football World Cup 2024"""

    def has_delete_permission(self, request, obj=None):
        """Block admins form deleting a Tournament"""
        return False

    list_display = [
        "name",
    ]
    inlines = [
        GroupsInline,
    ]


@admin.register(Participant)
class ParticipantsAdmin(admin.ModelAdmin):
    """Admin view of Tournament Participants e.g. countries like Germany, UK, France, etc."""

    list_display = [
        "name",
        "group",
    ]
    ordering = ("name",)
    list_filter = ("group",)
    search_fields = ("name",)


@admin.action(description="Fetch match stats via API")
def api_fetch_match_stats(modeladmin, request, queryset):
    """admin action for users to manually trigger match stats fetching via API"""
    for match in queryset:
        print(f"Fetching match stats for {match} via API triggered by {request.user.username}")
        app.send_task(
            "competition.tasks.api_match_score_request",
            args=[
                match.id,
                match.api_match_id,
                True,
            ],
        )


@admin.action(description="Fetch match ids via API")
def api_fetch_match_ids(modeladmin, request, _):
    """admin action for users to manually trigger match id fetching via API"""
    print(f"Fetching match ids from API triggered by {request.user.username}")
    update_api_match_ids()


@admin.register(Match)
class MatchesAdmin(admin.ModelAdmin):
    """Admin view to view the scheduled Matches e.g. on Sunday at 6pm X plays against Y"""

    list_display = [
        "phase",
        "match_time",
        "team_a_placeholder",
        "score_a",
        "score_b",
        "team_b_placeholder",
    ]
    ordering = ("match_time",)
    list_filter = ("phase",)
    search_fields = (
        "team_a_placeholder",
        "team_b_placeholder",
    )
    readonly_fields = ("api_match_id", "api_match_data")
    actions = [
        api_fetch_match_stats,
        api_fetch_match_ids,
    ]
