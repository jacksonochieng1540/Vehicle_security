"""
Vehicle Tracking Admin Configuration
"""
from django.contrib import admin
from .models import Vehicle, VehicleLocation, VehicleEvent, Geofence


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """Vehicle admin"""
    list_display = ('registration_number', 'make', 'model', 'year', 'owner', 'status', 'engine_enabled')
    list_filter = ('status', 'make', 'year')
    search_fields = ('registration_number', 'make', 'model', 'vin', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Vehicle Information', {
            'fields': ('owner', 'registration_number', 'make', 'model', 'year', 'color', 'vin')
        }),
        ('Status & Control', {
            'fields': ('status', 'engine_enabled', 'device_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(VehicleLocation)
class VehicleLocationAdmin(admin.ModelAdmin):
    """Vehicle Location admin"""
    list_display = ('vehicle', 'latitude', 'longitude', 'speed', 'timestamp')
    list_filter = ('vehicle', 'timestamp')
    search_fields = ('vehicle__registration_number',)
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # Locations are created automatically


@admin.register(VehicleEvent)
class VehicleEventAdmin(admin.ModelAdmin):
    """Vehicle Event admin"""
    list_display = ('vehicle', 'event_type', 'user', 'timestamp')
    list_filter = ('event_type', 'timestamp', 'vehicle')
    search_fields = ('vehicle__registration_number', 'description', 'user__username')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # Events are created automatically


@admin.register(Geofence)
class GeofenceAdmin(admin.ModelAdmin):
    """Geofence admin"""
    list_display = ('name', 'vehicle', 'radius', 'is_active', 'alert_on_entry', 'alert_on_exit')
    list_filter = ('is_active', 'alert_on_entry', 'alert_on_exit')
    search_fields = ('name', 'vehicle__registration_number')