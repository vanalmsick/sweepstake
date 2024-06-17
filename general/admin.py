# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export.admin import ExportMixin
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, EmailTemplates
from competition.models import MatchBet, GroupBet, TournamentBet
from sweepstake.celery import app


class MatchBetInline(admin.TabularInline):
    """Table of Match Bets to show in User detail view - i.e. all bets that user placed"""

    model = MatchBet
    fk_name = "user"
    extra = 0
    readonly_fields = (
        "points",
        "goal_difference",
    )
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


@admin.action(description="Send welcome email again to user")
def send_weclome_email_again(modeladmin, request, queryset):
    """admin action for users to re-send welcome email to user"""
    for user_obj in queryset:
        print(f"Sending welcome email again to {user_obj.username} triggered by {request.user.username}")
        app.send_task(
            "competition.tasks.welcome_email",
            args=[
                user_obj.pk,
            ],
        )


@admin.action(description="Send final reminder email again to user")
def send_final_reminder_email_again(modeladmin, request, queryset):
    """admin action for users to re-send final reminder email to user"""
    for user_obj in queryset:
        print(f"Sending final remindeer email again to {user_obj.username} triggered by {request.user.username}")
        app.send_task(
            "competition.tasks.last_admission_email",
            args=[
                user_obj.pk,
            ],
        )


@admin.action(description="Send daily email again to user")
def send_daily_email_again(modeladmin, request, queryset):
    """admin action for users to re-send daily email to user"""
    for user_obj in queryset:
        print(f"Sending daily email again to {user_obj.username} triggered by {request.user.username}")
        app.send_task(
            "competition.tasks.daily_matchday_email",
            args=[
                user_obj.pk,
            ],
        )


@admin.action(description="Send payment reminder to user")
def send_payment_reminder_email(modeladmin, request, queryset):
    """admin action for users to send payment remidner email to user"""
    for user_obj in queryset:
        print(f"Sending payment reminder email to {user_obj.username} triggered by {request.user.username}")
        app.send_task(
            "competition.tasks.payment_reminder_email",
            args=[user_obj.pk, [request.user.pk]],
        )


class CustomUserAdmin(ExportMixin, UserAdmin):
    """Amin view of Custom User model - needed to use email as login and a few more additional fields"""

    add_form = CustomUserCreationForm
    actions = [
        send_weclome_email_again,
        send_final_reminder_email_again,
        send_daily_email_again,
        send_payment_reminder_email,
    ]
    form = CustomUserChangeForm
    model = CustomUser
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "date_joined",
        "is_staff",
    )
    list_filter = ("is_staff", "has_paid", "team")
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
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "groups", "user_permissions"),
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

    def has_add_permission(self, request, obj=None):
        """no user can be added via admin view - user view is enough"""
        return False


@admin.action(description="Send test email to myself")
def send_test_email(modeladmin, request, queryset):
    """admin action for EmailTemplates to send test emails to user"""
    user_obj = request.user
    for test_template in queryset:
        print(f"Sending test email triggered by {user_obj.username}")
        if test_template.name == "daily_email":
            app.send_task(
                "competition.tasks.daily_matchday_email",
                args=[
                    user_obj.pk,
                    "2024-06-15",
                ],
            )
        elif test_template.name == "welcome_email":
            app.send_task(
                "competition.tasks.welcome_email",
                args=[
                    user_obj.pk,
                ],
            )
        elif test_template.name == "final_reminder":
            app.send_task(
                "competition.tasks.last_admission_email",
                args=[
                    user_obj.pk,
                ],
            )
        elif test_template.name == "payment_reminder":
            app.send_task(
                "competition.tasks.payment_reminder_email",
                args=[user_obj.pk, [user_obj.pk]],
            )


@admin.register(EmailTemplates)
class EmailTemplatesAdmin(admin.ModelAdmin):
    """Admin view to view for Email templates"""

    model = EmailTemplates
    list_display = [
        "name",
    ]
    ordering = ("name",)
    readonly_fields = ("name",)
    actions = [send_test_email]

    def has_add_permission(self, request, obj=None):
        """New email templates can't be added by admins"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Email templates can't be deleted by admins"""
        return False


admin.site.register(CustomUser, CustomUserAdmin)
# admin.site.unregister(Group)
# admin.site.unregister(Permission)
