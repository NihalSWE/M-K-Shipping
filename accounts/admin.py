# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    ordering = ('email',)
    list_display = (
        'email',
        'username',
        'user_type',
        'user_status',
        'is_active',
        'is_staff',
    )

    search_fields = (
        'email',
        'username',
        'first_name',
        'last_name',
    )