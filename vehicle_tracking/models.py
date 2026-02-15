"""
Vehicle Tracking Models
"""
from django.db import models
from django.conf import settings


class Vehicle(models.Model):
    """Vehicle model"""
    
    VEHICLE_STATUS = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
        ('stolen', 'Stolen'),
    )
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                            related_name='owned_vehicles')
    registration_number = models.CharField(max_length=20, unique=True)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField()
    color = models.CharField(max_length=30)
    vin = models.CharField(max_length=17, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=VEHICLE_STATUS, default='active')
    engine_enabled = models.BooleanField(default=True)
    device_id = models.CharField(max_length=100, unique=True, help_text="Raspberry Pi device ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
    
    def __str__(self):
        return f"{self.make} {self.model} ({self.registration_number})"
    
    def get_current_location(self):
        """Get the most recent location"""
        return self.locations.first()


class VehicleLocation(models.Model):
    """GPS location tracking"""
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='locations')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    altitude = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    speed = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, 
                               help_text="Speed in km/h")
    heading = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                 help_text="Direction in degrees")
    accuracy = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                  help_text="GPS accuracy in meters")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Vehicle Location'
        verbose_name_plural = 'Vehicle Locations'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['vehicle', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.vehicle.registration_number} - {self.timestamp}"
    
    @property
    def coordinates(self):
        """Return coordinates as tuple"""
        return (float(self.latitude), float(self.longitude))


class VehicleEvent(models.Model):
    """Track vehicle events"""
    
    EVENT_TYPES = (
        ('engine_start', 'Engine Started'),
        ('engine_stop', 'Engine Stopped'),
        ('auth_success', 'Authentication Success'),
        ('auth_failed', 'Authentication Failed'),
        ('unauthorized_access', 'Unauthorized Access'),
        ('remote_immobilize', 'Remote Immobilization'),
        ('remote_enable', 'Remote Enable'),
        ('speed_alert', 'Speed Alert'),
        ('geofence_breach', 'Geofence Breach'),
        ('low_battery', 'Low Battery'),
        ('system_error', 'System Error'),
    )
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    description = models.TextField()
    location = models.ForeignKey(VehicleLocation, on_delete=models.SET_NULL, 
                                null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                           null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Vehicle Event'
        verbose_name_plural = 'Vehicle Events'
    
    def __str__(self):
        return f"{self.vehicle.registration_number} - {self.get_event_type_display()} at {self.timestamp}"


class Geofence(models.Model):
    """Define geographical boundaries for alerts"""
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='geofences')
    name = models.CharField(max_length=100)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius = models.IntegerField(help_text="Radius in meters")
    is_active = models.BooleanField(default=True)
    alert_on_entry = models.BooleanField(default=False)
    alert_on_exit = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Geofence'
        verbose_name_plural = 'Geofences'
    
    def __str__(self):
        return f"{self.name} ({self.vehicle.registration_number})"