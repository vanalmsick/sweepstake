# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser
from competition.models import MatchBet, GroupBet, TournamentBet


class MatchBetInline(admin.TabularInline):
    """Table of Match Bets to show in User detail view - i.e. all bets that user placed"""

    model = MatchBet
    fk_name = "user"
    extra = 0
    readonly_fields = ("points",)
    can_delete = False


class GroupBetInline(admin.TabularInline):
    """Table of Group Bets to show in User detail view - i.e. all bets that user placed"""

    model = GroupBet
    fk_name = "user"
    extra = 0
    readonly_fields = ("points",)
    can_delete = False


class TournamentBetInline(admin.TabularInline):
    """Table of Tournament Bets to show in User detail view - i.e. all bets that user placed"""

    model = TournamentBet
    fk_name = "user"
    extra = 0
    readonly_fields = ("points",)
    can_delete = False


class CustomUserAdmin(UserAdmin):
    """Amin view of Custom User model - needed to use email as login and a few more additional fields"""

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
    )
    list_filter = ("is_staff", "team")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password",
                    "first_name",
                    "last_name",
                    "team",
                )
            },
        ),
        (
            "Admin",
            {
                "fields": (
                    "has_paid",
                    "is_verified",
                    "is_staff",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active", "groups", "user_permissions"),
            },
        ),
    )
    inlines = [
        TournamentBetInline,
        GroupBetInline,
        MatchBetInline,
    ]
    search_fields = (
        "first_name",
        "last_name",
        "team",
    )
    ordering = ("email",)


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.unregister(Group)
# admin.site.unregister(Permission)
