# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin # Rename import
from .models import User

@admin.register(User) # <--- THIS REGISTERS THE MODEL
class CustomUserAdmin(BaseUserAdmin): # <--- Rename to CustomUserAdmin
    model = User

    ordering = ('email',)
    list_display = (
        'email', 
        'username',
        'phone_number', 
        'user_type', 
        'user_status', 
        'is_active', 
        'is_staff',
    )

    # Required: Autocomplete needs search_fields to work in other admins
    search_fields = ('email', 'username', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'username', 'phone_number', 'company_name')}),
        ('Location', {'fields': ('address', 'city', 'state', 'postal_code')}),
        ('Proxy Settings', {'fields': ('proxy_ip', 'proxy_port', 'proxy_username', 'proxy_password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Status & Types', {'fields': ('user_type', 'user_status', 'balance', 'credit_limit')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password', 'user_type'),
        }),
    )