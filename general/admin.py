from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser
from competition.models import Bet

class BetInline(admin.TabularInline):

    model = Bet
    fk_name = "user"
    extra = 0
    readonly_fields = ('points',)
    can_delete = False


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("username", "email", "first_name", "last_name", "is_staff",)
    list_filter = ("is_staff",)
    fieldsets = (
        (None, {"fields": ("email", "password","first_name", "last_name",)}),
        ('Admin', {"fields": ("has_paid", "is_verified", "is_staff",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", "password1", "password2", "is_staff",
                "is_active", "groups", "user_permissions"
            )}
        ),
    )
    inlines = [BetInline, ]
    search_fields = ("email", "first_name", "last_name",)
    ordering = ("email",)


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.unregister(Group)
#admin.site.unregister(Permission)
