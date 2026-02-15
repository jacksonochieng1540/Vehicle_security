"""
Custom User Model for Vehicle Security System
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """Extended User model with additional fields"""
    
    USER_ROLES = (
        ('owner', 'Vehicle Owner'),
        ('driver', 'Authorized Driver'),
        ('admin', 'System Administrator'),
    )
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+254712345678'"
    )
    
    role = models.CharField(max_length=20, choices=USER_ROLES, default='driver')
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    facial_encoding = models.BinaryField(null=True, blank=True, editable=False)
    is_authorized_driver = models.BooleanField(default=False)
    vehicle = models.ForeignKey('vehicle_tracking.Vehicle', on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='users')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip() or self.username


class AuthenticationLog(models.Model):
    """Log all authentication attempts"""
    
    STATUS_CHOICES = (
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('unauthorized', 'Unauthorized'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                           related_name='auth_logs')
    vehicle = models.ForeignKey('vehicle_tracking.Vehicle', on_delete=models.CASCADE,
                               related_name='auth_logs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    captured_image = models.ImageField(upload_to='authentication_logs/', null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    location_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Authentication Log'
        verbose_name_plural = 'Authentication Logs'
    
    def __str__(self):
        user_info = self.user.username if self.user else 'Unknown'
        return f"{user_info} - {self.status} at {self.timestamp}"