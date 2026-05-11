# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin # Rename import
from django.contrib import admin, messages
from .models import User, UserProfile





@admin.action(description='Force delete selected users (and their passengers)')
def force_delete_users_and_passengers(modeladmin, request, queryset):
    # 1. Loop through selected users and delete their passenger records first
    
    for user in queryset:
        # Uses the related_name 'booking_passengers' from your model
        user.booking_passengers.all().delete()
        
    # 2. Now that the protected records are gone, delete the users
    deleted_count, _ = queryset.delete()
    
    # 3. Show a green success message in the admin panel
    modeladmin.message_user(
        request, 
        f"Successfully force-deleted {deleted_count} user(s) and their associated passenger records.",
        messages.SUCCESS
    )
    

@admin.register(User) # <--- THIS REGISTERS THE MODEL
class CustomUserAdmin(BaseUserAdmin): # <--- Rename to CustomUserAdmin
    model = User
    
    # --- ADD THIS LINE TO REGISTER THE ACTION ---
    actions = [force_delete_users_and_passengers]

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
    

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    # Fields to display in the main list view
    list_display = ('user_email', 'job_title', 'city', 'country', 'hire_date')
    
    # Enable filtering on the right sidebar
    list_filter = ('country', 'job_title', 'hire_date', 'gender')
    
    # Enable searching (user__email allows searching via the related User model)
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'job_title', 'skills')
    
    # Organize fields into logical sections (Fieldsets)
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'profile_picture')
        }),
        ('Personal Details', {
            'fields': ('date_of_birth', 'gender', 'biography')
        }),
        ('Professional Info', {
            'fields': ('job_title', 'hire_date', 'skills', 'linkedin_profile', 'github_profile')
        }),
        ('Contact & Location', {
            'fields': ('address', 'city', 'state', 'postal_code', 'country', 'timezone'),
            'classes': ('collapse',),  # This makes the section collapsible
        }),
    )

    # Helper method to show the user's email in list_display
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'