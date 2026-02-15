"""
Hardware Authentication Service
Coordinates facial recognition, GPS, GSM, and relay control
"""
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.files.base import ContentFile
import cv2
import numpy as np

from .facial_recognition import get_facial_recognition_system
from .gps_module import get_gps_module
from .gsm_module import get_gsm_module, format_unauthorized_access_sms, format_engine_status_sms
from .relay_control import get_relay_controller


class HardwareAuthenticationService:
    """
    Main service coordinating all hardware components for authentication
    """
    
    def __init__(self, simulated=False):
        self.simulated = simulated
        self.facial_recognition = get_facial_recognition_system()
        self.gps = get_gps_module(simulated=simulated)
        self.gsm = get_gsm_module(simulated=simulated)
        self.relay = get_relay_controller(simulated=simulated)
        
        # Authentication lockout tracking
        self.last_failed_auth = {}
        
    def authenticate_driver(self, vehicle_id, image=None, capture_from_camera=False):
        """
        Perform complete driver authentication
        
        Args:
            vehicle_id: Vehicle ID to authenticate for
            image: Image to authenticate (optional)
            capture_from_camera: If True, capture from camera
            
        Returns:
            Dictionary with authentication result
        """
        from authentication.models import AuthenticationLog, User
        from vehicle_tracking.models import Vehicle, VehicleEvent
        from alerts.models import Alert
        
        # Get vehicle
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            return {
                'success': False,
                'message': 'Vehicle not found',
            }
        
        # Check if authentication is locked out
        if self._is_locked_out(vehicle_id):
            return {
                'success': False,
                'message': 'Authentication temporarily locked. Please wait.',
                'locked_until': self.last_failed_auth.get(vehicle_id)
            }
        
        # Get current location
        current_location = None
        if self.gps.connect():
            gps_data = self.gps.read_gps_data()
            if gps_data:
                current_location = gps_data
        
        # Capture or use provided image
        if capture_from_camera and not image:
            image = self.facial_recognition.capture_from_camera()
            if image is None:
                return {
                    'success': False,
                    'message': 'Failed to capture image from camera',
                }
        
        if image is None:
            return {
                'success': False,
                'message': 'No image provided',
            }
        
        # Perform facial recognition
        is_authenticated, user_id, confidence, face_image = self.facial_recognition.authenticate_face(
            image, vehicle_id
        )
        
        # Save face image
        face_image_file = None
        if face_image is not None:
            _, buffer = cv2.imencode('.jpg', face_image)
            face_image_file = ContentFile(buffer.tobytes(), name='face.jpg')
        
        # Get authenticated user
        authenticated_user = None
        if is_authenticated and user_id:
            try:
                authenticated_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                is_authenticated = False
        
        # Create authentication log
        auth_log = AuthenticationLog.objects.create(
            user=authenticated_user,
            vehicle=vehicle,
            status='success' if is_authenticated else 'unauthorized',
            confidence_score=confidence,
            captured_image=face_image_file,
            location_latitude=current_location['latitude'] if current_location else None,
            location_longitude=current_location['longitude'] if current_location else None,
        )
        
        if is_authenticated:
            # Authentication successful
            # Enable engine
            self.relay.enable_engine()
            vehicle.engine_enabled = True
            vehicle.save()
            
            # Log event
            VehicleEvent.objects.create(
                vehicle=vehicle,
                event_type='auth_success',
                description=f'Successful authentication by {authenticated_user.get_full_name()}',
                user=authenticated_user,
            )
            
            # Clear lockout
            if vehicle_id in self.last_failed_auth:
                del self.last_failed_auth[vehicle_id]
            
            return {
                'success': True,
                'message': f'Welcome, {authenticated_user.get_full_name()}!',
                'user': authenticated_user,
                'confidence': confidence,
                'engine_enabled': True,
            }
        
        else:
            # Authentication failed
            # Disable engine
            self.relay.disable_engine()
            vehicle.engine_enabled = False
            vehicle.save()
            
            # Set lockout
            self._set_lockout(vehicle_id)
            
            # Log event
            VehicleEvent.objects.create(
                vehicle=vehicle,
                event_type='unauthorized_access',
                description='Unauthorized access attempt detected',
            )
            
            # Create alert
            alert = Alert.objects.create(
                vehicle=vehicle,
                alert_type='unauthorized_access',
                severity='critical',
                title='Unauthorized Access Attempt',
                message=f'Unauthorized access attempt detected at {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}',
                related_image=face_image_file,
            )
            
            # Send SMS notification
            if current_location:
                sms_message = format_unauthorized_access_sms(
                    vehicle.registration_number,
                    current_location,
                    timezone.now()
                )
                
                # Send to vehicle owner
                if vehicle.owner.phone_number:
                    self.gsm.send_sms(vehicle.owner.phone_number, sms_message)
            
            return {
                'success': False,
                'message': 'Authentication failed. Unauthorized access detected.',
                'confidence': confidence,
                'engine_enabled': False,
                'alert_created': True,
            }
    
    def remote_control_engine(self, vehicle_id, enable, user):
        """
        Remote engine control
        
        Args:
            vehicle_id: Vehicle ID
            enable: Boolean (True = enable, False = disable)
            user: User performing action
            
        Returns:
            Dictionary with result
        """
        from vehicle_tracking.models import Vehicle, VehicleEvent
        
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            return {'success': False, 'message': 'Vehicle not found'}
        
        # Control relay
        if enable:
            self.relay.enable_engine()
            event_type = 'remote_enable'
            message = f'Engine remotely enabled by {user.get_full_name()}'
        else:
            self.relay.disable_engine()
            event_type = 'remote_immobilize'
            message = f'Engine remotely disabled by {user.get_full_name()}'
        
        # Update vehicle
        vehicle.engine_enabled = enable
        vehicle.save()
        
        # Log event
        VehicleEvent.objects.create(
            vehicle=vehicle,
            event_type=event_type,
            description=message,
            user=user,
        )
        
        # Send SMS notification
        if vehicle.owner.phone_number:
            sms_message = format_engine_status_sms(
                vehicle.registration_number,
                enable,
                user.get_full_name()
            )
            self.gsm.send_sms(vehicle.owner.phone_number, sms_message)
        
        return {
            'success': True,
            'message': message,
            'engine_enabled': enable,
        }
    
    def update_vehicle_location(self, vehicle_id):
        """
        Update vehicle location from GPS
        
        Returns:
            Location data dictionary or None
        """
        from vehicle_tracking.models import Vehicle, VehicleLocation
        
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            return None
        
        if not self.gps.connect():
            return None
        
        gps_data = self.gps.read_gps_data()
        if not gps_data:
            return None
        
        # Save location
        location = VehicleLocation.objects.create(
            vehicle=vehicle,
            latitude=gps_data['latitude'],
            longitude=gps_data['longitude'],
            altitude=gps_data.get('altitude'),
            speed=gps_data.get('speed'),
            heading=gps_data.get('heading'),
        )
        
        return gps_data
    
    def _is_locked_out(self, vehicle_id):
        """Check if authentication is locked out"""
        from django.conf import settings
        
        if vehicle_id not in self.last_failed_auth:
            return False
        
        lockout_time = self.last_failed_auth[vehicle_id]
        timeout = settings.HARDWARE_CONFIG.get('AUTHENTICATION_TIMEOUT', 30)
        
        return (datetime.now() - lockout_time).total_seconds() < timeout
    
    def _set_lockout(self, vehicle_id):
        """Set authentication lockout"""
        self.last_failed_auth[vehicle_id] = datetime.now()
    
    def cleanup(self):
        """Cleanup all hardware connections"""
        self.gps.disconnect()
        self.gsm.disconnect()
        self.relay.cleanup()


# Singleton instance
_hardware_service = None

def get_hardware_service(simulated=False):
    """Get or create hardware service instance"""
    global _hardware_service
    if _hardware_service is None:
        _hardware_service = HardwareAuthenticationService(simulated=simulated)
    return _hardware_service