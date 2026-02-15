"""
Hardware Models
"""
from django.db import models


class HardwareDevice(models.Model):
    """Track hardware device information"""
    
    DEVICE_TYPES = (
        ('raspberry_pi', 'Raspberry Pi'),
        ('esp32_cam', 'ESP32-CAM'),
        ('gps', 'GPS Module'),
        ('gsm', 'GSM Module'),
        ('relay', 'Relay Module'),
    )
    
    DEVICE_STATUS = (
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
        ('maintenance', 'Maintenance'),
    )
    
    vehicle = models.ForeignKey('vehicle_tracking.Vehicle', on_delete=models.CASCADE,
                               related_name='hardware_devices')
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    device_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=DEVICE_STATUS, default='offline')
    firmware_version = models.CharField(max_length=50, blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Hardware Device'
        verbose_name_plural = 'Hardware Devices'
    
    def __str__(self):
        return f"{self.get_device_type_display()} - {self.device_id}"


class SystemLog(models.Model):
    """System operation logs"""
    
    LOG_LEVELS = (
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    )
    
    vehicle = models.ForeignKey('vehicle_tracking.Vehicle', on_delete=models.CASCADE,
                               related_name='system_logs', null=True, blank=True)
    level = models.CharField(max_length=20, choices=LOG_LEVELS, default='info')
    component = models.CharField(max_length=50)  # e.g., 'facial_recognition', 'gps', 'gsm'
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'System Log'
        verbose_name_plural = 'System Logs'
    
    def __str__(self):
        return f"[{self.level.upper()}] {self.component}: {self.message[:50]}"