from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class ClearEyeUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Google sign-in', {'fields': ('google_sub',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile', {'fields': ('email', 'first_name', 'last_name')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
