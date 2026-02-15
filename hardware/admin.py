"""
Hardware Admin Configuration
"""
from django.contrib import admin
from .models import HardwareDevice, SystemLog


@admin.register(HardwareDevice)
class HardwareDeviceAdmin(admin.ModelAdmin):
    """Hardware Device admin"""
    list_display = ('device_id', 'device_type', 'vehicle', 'status', 'last_heartbeat')
    list_filter = ('device_type', 'status')
    search_fields = ('device_id', 'vehicle__registration_number')
    readonly_fields = ('last_heartbeat', 'created_at', 'updated_at')


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    """System Log admin"""
    list_display = ('timestamp', 'level', 'component', 'message_preview')
    list_filter = ('level', 'component', 'timestamp')
    search_fields = ('message', 'component')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    def message_preview(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'
    
    def has_add_permission(self, request):
        return False  # Logs are created automatically