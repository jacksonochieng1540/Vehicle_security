"""
Alerts Models
"""
from django.db import models
from django.conf import settings


class Alert(models.Model):
    """Alert notifications"""
    
    ALERT_TYPES = (
        ('unauthorized_access', 'Unauthorized Access'),
        ('auth_failure', 'Authentication Failure'),
        ('geofence_breach', 'Geofence Breach'),
        ('speed_alert', 'Speed Alert'),
        ('engine_disabled', 'Engine Disabled'),
        ('low_battery', 'Low Battery'),
        ('system_error', 'System Error'),
        ('theft_attempt', 'Theft Attempt'),
    )
    
    ALERT_SEVERITY = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    ALERT_STATUS = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('acknowledged', 'Acknowledged'),
    )
    
    vehicle = models.ForeignKey('vehicle_tracking.Vehicle', on_delete=models.CASCADE,
                               related_name='alerts')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=ALERT_SEVERITY, default='medium')
    status = models.CharField(max_length=20, choices=ALERT_STATUS, default='pending')
    title = models.CharField(max_length=200)
    message = models.TextField()
    location = models.ForeignKey('vehicle_tracking.VehicleLocation', on_delete=models.SET_NULL,
                                null=True, blank=True)
    related_image = models.ImageField(upload_to='alert_images/', null=True, blank=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['vehicle', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.vehicle.registration_number} ({self.severity})"


class NotificationLog(models.Model):
    """Log all notification attempts"""
    
    NOTIFICATION_TYPES = (
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('cloud', 'Cloud Platform'),
    )
    
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    recipient_address = models.CharField(max_length=200, help_text="Phone number or email address")
    message_content = models.TextField()
    is_successful = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
    
    def __str__(self):
        status = 'Sent' if self.is_successful else 'Failed'
        return f"{self.notification_type} to {self.recipient.username} - {status}"


class AlertRule(models.Model):
    """Define custom alert rules"""
    
    vehicle = models.ForeignKey('vehicle_tracking.Vehicle', on_delete=models.CASCADE,
                               related_name='alert_rules')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # Rule conditions
    trigger_on_unauthorized_access = models.BooleanField(default=True)
    trigger_on_failed_auth = models.BooleanField(default=True)
    trigger_on_geofence_breach = models.BooleanField(default=True)
    trigger_on_speed_limit = models.BooleanField(default=False)
    speed_limit_threshold = models.IntegerField(null=True, blank=True, 
                                               help_text="Speed in km/h")
    
    # Notification preferences
    send_sms = models.BooleanField(default=True)
    send_email = models.BooleanField(default=False)
    send_push = models.BooleanField(default=False)
    
    # Recipients
    notify_owner = models.BooleanField(default=True)
    additional_recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
                                                  related_name='alert_rule_subscriptions')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Alert Rule'
        verbose_name_plural = 'Alert Rules'
    
    def __str__(self):
        return f"{self.name} ({self.vehicle.registration_number})"