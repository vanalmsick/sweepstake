from django.contrib import admin

from .models import Tournament, Group, Participant, Match

# Register your models here.
class GroupsInline(admin.TabularInline):

    model = Group
    fk_name = "tournament"
    extra = 0


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):

    list_display = [
        "name",
    ]
    inlines = [
        GroupsInline,
    ]


@admin.register(Participant)
class ParticipantsAdmin(admin.ModelAdmin):

    list_display = [
        "name",
        "group",
    ]
    ordering = ("name",)


@admin.register(Match)
class MatchesAdmin(admin.ModelAdmin):

    list_display = [
        "phase",
        "match_time",
        "team_a_placeholder",
        "team_b_placeholder",
    ]
    ordering = ("match_time",)





