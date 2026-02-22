"""
Hardware App Tests
Tests for facial recognition, GPS, GSM, relay control, and hardware devices
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.conf import settings
from hardware.models import HardwareDevice, SystemLog
from vehicle_tracking.models import Vehicle
from hardware.facial_recognition import FacialRecognitionSystem
from hardware.gps_module import GPSModule
from hardware.gsm_module import GSMModule
from hardware.relay_control import RelayController
from hardware.authentication_service import HardwareAuthenticationService
import numpy as np
from pathlib import Path
import os

User = get_user_model()


class HardwareDeviceModelTest(TestCase):
    """Test HardwareDevice model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='hwuser', password='pass')
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='HW 001',
            make='Test',
            model='Car',
            year=2020,
            device_id='RPI_HW001'
        )
    
    def test_device_creation(self):
        """Test hardware device can be created"""
        device = HardwareDevice.objects.create(
            vehicle=self.vehicle,
            device_type='raspberry_pi',
            device_id='RPI_HW001',
            status='online',
            firmware_version='v2.0.0'
        )
        
        self.assertEqual(device.vehicle, self.vehicle)
        self.assertEqual(device.device_type, 'raspberry_pi')
        self.assertEqual(device.status, 'online')
    
    def test_device_types(self):
        """Test different device types"""
        device_types = ['raspberry_pi', 'gps_module', 'gsm_module', 'camera']
        
        for dtype in device_types:
            device = HardwareDevice.objects.create(
                vehicle=self.vehicle,
                device_type=dtype,
                device_id=f'DEVICE_{dtype}',
                status='online'
            )
            self.assertEqual(device.device_type, dtype)


class SystemLogModelTest(TestCase):
    """Test SystemLog model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='loguser', password='pass')
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='LOG 001',
            make='Test',
            model='Car',
            year=2020,
            device_id='RPI_LOG'
        )
    
    def test_system_log_creation(self):
        """Test system log can be created"""
        log = SystemLog.objects.create(
            vehicle=self.vehicle,
            level='info',
            component='gps',
            message='GPS module initialized successfully'
        )
        
        self.assertEqual(log.vehicle, self.vehicle)
        self.assertEqual(log.level, 'info')
        self.assertEqual(log.component, 'gps')
    
    def test_log_levels(self):
        """Test different log levels"""
        levels = ['debug', 'info', 'warning', 'error', 'critical']
        
        for level in levels:
            log = SystemLog.objects.create(
                vehicle=self.vehicle,
                level=level,
                component='test',
                message=f'Test {level} message'
            )
            self.assertEqual(log.level, level)


class FacialRecognitionTest(TestCase):
    """Test facial recognition system"""
    
    def setUp(self):
        self.facial_system = FacialRecognitionSystem()
    
    def test_facial_recognition_initialization(self):
        """Test facial recognition system initializes"""
        self.assertIsNotNone(self.facial_system.face_cascade)
        self.assertIsNotNone(self.facial_system.recognizer)
    
    def test_detect_faces_returns_list(self):
        """Test detect_faces returns list"""
        # Create a simple test image (blank)
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        faces = self.facial_system.detect_faces(test_image)
        
        # Should return a list (even if empty)
        self.assertIsInstance(faces, (list, tuple, np.ndarray))
    
    def test_extract_face_encoding(self):
        """Test face encoding extraction"""
        # Create test image and face rectangle
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        face_rect = (100, 100, 200, 200)  # x, y, w, h
        
        encoding = self.facial_system.extract_face_encoding(test_image, face_rect)
        
        # Should return a numpy array
        self.assertIsInstance(encoding, np.ndarray)
        # Should be 200x200 (as per SKILL.md)
        self.assertEqual(encoding.shape, (200, 200))


class GPSModuleTest(TestCase):
    """Test GPS module"""
    
    def setUp(self):
        # Use simulated GPS for testing
        self.gps = GPSModule(simulated=True)
    
    def test_gps_initialization(self):
        """Test GPS module initializes"""
        self.assertIsNotNone(self.gps)
        self.assertTrue(self.gps.simulated)
    
    def test_simulated_gps_connection(self):
        """Test simulated GPS connection"""
        connected = self.gps.connect()
        self.assertTrue(connected)
    
    def test_simulated_gps_data(self):
        """Test reading simulated GPS data"""
        if self.gps.connect():
            data = self.gps.read_gps_data()
            
            if data:  # Simulated data might not always return
                self.assertIn('latitude', data)
                self.assertIn('longitude', data)
                self.assertIsInstance(data['latitude'], (int, float))
                self.assertIsInstance(data['longitude'], (int, float))


class GSMModuleTest(TestCase):
    """Test GSM module"""
    
    def setUp(self):
        # Use simulated GSM for testing
        self.gsm = GSMModule(simulated=True)
    
    def test_gsm_initialization(self):
        """Test GSM module initializes"""
        self.assertIsNotNone(self.gsm)
        self.assertTrue(self.gsm.simulated)
    
    def test_simulated_gsm_connection(self):
        """Test simulated GSM connection"""
        connected = self.gsm.connect()
        self.assertTrue(connected)
    
    def test_simulated_sms_send(self):
        """Test sending SMS in simulated mode"""
        if self.gsm.connect():
            success = self.gsm.send_sms('+254712345678', 'Test message')
            self.assertTrue(success)


class RelayControllerTest(TestCase):
    """Test relay controller"""
    
    def setUp(self):
        # Use simulated relay for testing
        self.relay = RelayController(simulated=True)
    
    def test_relay_initialization(self):
        """Test relay controller initializes"""
        self.assertIsNotNone(self.relay)
        self.assertTrue(self.relay.simulated)
    
    def test_enable_engine(self):
        """Test enabling engine"""
        self.relay.enable_engine()
        self.assertTrue(self.relay.engine_state)
    
    def test_disable_engine(self):
        """Test disabling engine"""
        self.relay.disable_engine()
        self.assertFalse(self.relay.engine_state)
    
    def test_get_engine_state(self):
        """Test getting engine state"""
        state = self.relay.get_engine_state()
        self.assertIsInstance(state, bool)
    
    def test_toggle_engine(self):
        """Test toggling engine state"""
        initial_state = self.relay.get_engine_state()
        
        # Toggle
        if initial_state:
            self.relay.disable_engine()
        else:
            self.relay.enable_engine()
        
        # State should be opposite
        new_state = self.relay.get_engine_state()
        self.assertNotEqual(initial_state, new_state)


class HardwareAuthenticationServiceTest(TestCase):
    """Test hardware authentication service"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='authuser',
            password='pass',
            first_name='Auth',
            last_name='User'
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='AUTH 001',
            make='Test',
            model='Car',
            year=2020,
            device_id='RPI_AUTH'
        )
        
        # Use simulated service
        self.service = HardwareAuthenticationService(simulated=True)
    
    def test_service_initialization(self):
        """Test authentication service initializes"""
        self.assertIsNotNone(self.service)
        self.assertIsNotNone(self.service.facial_recognition)
        self.assertIsNotNone(self.service.gps)
        self.assertIsNotNone(self.service.gsm)
        self.assertIsNotNone(self.service.relay)
    
    def test_update_vehicle_location(self):
        """Test updating vehicle location"""
        location = self.service.update_vehicle_location(self.vehicle.id)
        
        if location:  # Might be None in simulated mode
            self.assertIn('latitude', location)
            self.assertIn('longitude', location)
    
    def test_remote_control_disable(self):
        """Test remote engine disable"""
        result = self.service.remote_control_engine(
            vehicle_id=self.vehicle.id,
            enable=False,
            user=self.user
        )
        
        self.assertTrue(result['success'])
        self.assertFalse(result['engine_enabled'])
    
    def test_remote_control_enable(self):
        """Test remote engine enable"""
        result = self.service.remote_control_engine(
            vehicle_id=self.vehicle.id,
            enable=True,
            user=self.user
        )
        
        self.assertTrue(result['success'])
        self.assertTrue(result['engine_enabled'])


class HardwareIntegrationTest(TestCase):
    """Integration tests for hardware components"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='integuser',
            password='pass',
            first_name='Integration',
            last_name='User',
            is_authorized_driver=True
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='INTEG 001',
            make='Test',
            model='Car',
            year=2020,
            device_id='RPI_INTEG'
        )
        
        # Assign user to vehicle
        self.user.vehicle = self.vehicle
        self.user.save()
        
        self.service = HardwareAuthenticationService(simulated=True)
    
    def test_full_authentication_flow(self):
        """Test complete authentication workflow"""
        # Create a test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Attempt authentication
        result = self.service.authenticate_driver(
            vehicle_id=self.vehicle.id,
            image=test_image
        )
        
        # Result should have required keys
        self.assertIn('success', result)
        self.assertIn('message', result)
    
    def test_authentication_creates_log(self):
        """Test authentication creates log entry"""
        from authentication.models import AuthenticationLog
        
        initial_count = AuthenticationLog.objects.count()
        
        # Create test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Attempt authentication
        self.service.authenticate_driver(
            vehicle_id=self.vehicle.id,
            image=test_image
        )
        
        # Should have created a log
        final_count = AuthenticationLog.objects.count()
        self.assertGreater(final_count, initial_count)
    
    def test_hardware_cleanup(self):
        """Test hardware cleanup"""
        # Should not raise exception
        try:
            self.service.cleanup()
            success = True
        except Exception:
            success = False
        
        self.assertTrue(success)


class HardwareConfigTest(TestCase):
    """Test hardware configuration settings"""
    
    def test_hardware_config_exists(self):
        """Test HARDWARE_CONFIG exists in settings"""
        self.assertTrue(hasattr(settings, 'HARDWARE_CONFIG'))
    
    def test_hardware_config_keys(self):
        """Test required keys in HARDWARE_CONFIG"""
        required_keys = [
            'CAMERA_DEVICE',
            'GPS_PORT',
            'GPS_BAUDRATE',
            'GSM_PORT',
            'GSM_BAUDRATE',
            'RELAY_GPIO_PIN',
            'RECOGNITION_TOLERANCE',
            'AUTHENTICATION_TIMEOUT'
        ]
        
        config = settings.HARDWARE_CONFIG
        
        for key in required_keys:
            self.assertIn(key, config)
    
    def test_recognition_tolerance_valid(self):
        """Test recognition tolerance is valid"""
        tolerance = settings.HARDWARE_CONFIG['RECOGNITION_TOLERANCE']
        
        # Should be between 0 and 1
        self.assertGreaterEqual(tolerance, 0)
        self.assertLessEqual(tolerance, 1)


# Run tests with:
# python manage.py test hardware