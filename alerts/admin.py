"""
Alerts Admin Configuration
"""
from django.contrib import admin
from .models import Alert, NotificationLog, AlertRule


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Alert admin"""
    list_display = ('vehicle', 'alert_type', 'severity', 'status', 'created_at')
    list_filter = ('alert_type', 'severity', 'status', 'created_at')
    search_fields = ('vehicle__registration_number', 'title', 'message')
    readonly_fields = ('created_at', 'acknowledged_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('vehicle', 'alert_type', 'severity', 'title', 'message')
        }),
        ('Status', {
            'fields': ('status', 'acknowledged_by', 'acknowledged_at')
        }),
        ('Additional Data', {
            'fields': ('location', 'related_image'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Notification Log admin"""
    list_display = ('alert', 'recipient', 'notification_type', 'is_successful', 'sent_at')
    list_filter = ('notification_type', 'is_successful', 'sent_at')
    search_fields = ('alert__title', 'recipient__username', 'recipient_address')
    readonly_fields = ('sent_at',)
    date_hierarchy = 'sent_at'
    
    def has_add_permission(self, request):
        return False  # Logs are created automatically


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    """Alert Rule admin"""
    list_display = ('name', 'vehicle', 'is_active', 'send_sms', 'notify_owner')
    list_filter = ('is_active', 'send_sms', 'send_email', 'notify_owner')
    search_fields = ('name', 'vehicle__registration_number')
    filter_horizontal = ('additional_recipients',)