"""
Authentication Admin Configuration
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AuthenticationLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_authorized_driver', 'vehicle')
    list_filter = ('role', 'is_authorized_driver', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'profile_image', 'is_authorized_driver', 'vehicle')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'profile_image', 'is_authorized_driver', 'vehicle')
        }),
    )


@admin.register(AuthenticationLog)
class AuthenticationLogAdmin(admin.ModelAdmin):
    """Authentication Log admin"""
    list_display = ('user', 'vehicle', 'status', 'confidence_score', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('user__username', 'vehicle__registration_number', 'notes')
    readonly_fields = ('timestamp', 'captured_image')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # Logs are created automatically