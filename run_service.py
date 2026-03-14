#!/usr/bin/env python3
"""
Smart Vehicle Security - Hardware Service
Main service script that runs on Raspberry Pi
Controls GPS, GSM, Relay, and Facial Recognition
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
import django

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartVehicleProject.settings')
django.setup()

# Import Django models and hardware modules
from django.utils import timezone
from authentication.models import User, AuthenticationLog
from vehicle_tracking.models import Vehicle, VehicleLocation, VehicleEvent
from alerts.models import Alert

from hardware.gps_module import get_gps_module
from hardware.gsm_module import get_gsm_module
from hardware.relay_control import get_relay_controller
from hardware.facial_recognition import get_facial_recognition_system

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/vehicle_security.log')
    ]
)
logger = logging.getLogger(__name__)


class VehicleSecurityService:
    """Main hardware control service"""
    
    def __init__(self):
        logger.info("=" * 70)
        logger.info("🚀 SMART VEHICLE SECURITY - HARDWARE SERVICE")
        logger.info("=" * 70)
        
        # Load configuration
        from django.conf import settings
        self.config = settings.HARDWARE_CONFIG
        self.device_id = self.config['DEVICE_ID']
        self.simulated = self.config['SIMULATED_HARDWARE']
        
        logger.info(f"📋 Device ID: {self.device_id}")
        logger.info(f"🔧 Mode: {'SIMULATED' if self.simulated else 'REAL HARDWARE'}")
        
        # Get vehicle from database
        try:
            self.vehicle = Vehicle.objects.get(device_id=self.device_id)
            logger.info(f"🚗 Vehicle: {self.vehicle.registration_number}")
            logger.info(f"👤 Owner: {self.vehicle.owner.get_full_name()}")
        except Vehicle.DoesNotExist:
            logger.error(f"❌ No vehicle found with device_id: {self.device_id}")
            logger.error("   Please create a vehicle in Django admin with this device_id!")
            sys.exit(1)
        
        # Initialize hardware modules
        logger.info("\n🔌 Initializing hardware modules...")
        self.gps = get_gps_module(simulated=self.simulated)
        self.gsm = get_gsm_module(simulated=self.simulated)
        self.relay = get_relay_controller(simulated=self.simulated)
        self.facial_recognition = get_facial_recognition_system()
        
        # Connect hardware
        if self.gps.connect():
            logger.info("✅ GPS connected")
        else:
            logger.warning("⚠️  GPS connection failed")
        
        if self.gsm.connect():
            logger.info("✅ GSM connected")
        else:
            logger.warning("⚠️  GSM connection failed")
        
        logger.info("✅ Relay controller initialized")
        logger.info("✅ Facial recognition initialized\n")
        
        self.running = True
        self.loop_count = 0
    
    def update_gps_location(self):
        """Read GPS data and save to database"""
        try:
            location_data = self.gps.read_gps_data()
            
            if location_data:
                # Save to database
                VehicleLocation.objects.create(
                    vehicle=self.vehicle,
                    latitude=location_data['latitude'],
                    longitude=location_data['longitude'],
                    altitude=location_data.get('altitude', 0),
                    speed=location_data.get('speed', 0),
                    heading=location_data.get('heading', 0)
                )
                
                logger.info(
                    f"📍 GPS: {location_data['latitude']:.6f}, "
                    f"{location_data['longitude']:.6f} "
                    f"(Satellites: {location_data.get('num_satellites', 0)})"
                )
            else:
                logger.debug("GPS: Waiting for fix...")
                
        except Exception as e:
            logger.error(f"GPS update error: {e}")
    
    def check_remote_control(self):
        """Check for remote engine control commands from database"""
        try:
            # Refresh vehicle data from database
            self.vehicle.refresh_from_db()
            
            # Check current relay status
            current_relay_state = self.relay.get_status()
            should_be_enabled = self.vehicle.engine_enabled
            
            # Compare database state with hardware state
            if should_be_enabled and not current_relay_state:
                # Database says enable, but relay is off
                logger.info("🔓 Remote ENABLE command detected")
                self.relay.enable_engine()
                
                # Log event
                VehicleEvent.objects.create(
                    vehicle=self.vehicle,
                    event_type='engine_start',
                    description='Engine enabled via remote command'
                )
                
            elif not should_be_enabled and current_relay_state:
                # Database says disable, but relay is on
                logger.warning("🔒 Remote DISABLE command detected")
                self.relay.disable_engine()
                
                # Log event
                VehicleEvent.objects.create(
                    vehicle=self.vehicle,
                    event_type='engine_stop',
                    description='Engine disabled via remote command'
                )
                
                # Send SMS alert
                if self.vehicle.owner.phone_number:
                    message = (
                        f"ALERT: Vehicle {self.vehicle.registration_number} "
                        f"has been immobilized remotely at {timezone.now().strftime('%H:%M:%S')}"
                    )
                    self.gsm.send_sms(self.vehicle.owner.phone_number, message)
                    logger.info(f"📱 SMS alert sent to {self.vehicle.owner.phone_number}")
                
        except Exception as e:
            logger.error(f"Remote control check error: {e}")
    
    def run(self):
        """Main service loop"""
        logger.info("🟢 SERVICE RUNNING")
        logger.info("Press Ctrl+C to stop\n")
        
        while self.running:
            try:
                # Every 5 seconds: Check remote control
                if self.loop_count % 5 == 0:
                    self.check_remote_control()
                
                # Every 10 seconds: Update GPS location
                if self.loop_count % 10 == 0:
                    self.update_gps_location()
                
                # Every 30 seconds: Heartbeat log
                if self.loop_count % 30 == 0:
                    logger.info(f"💓 Heartbeat (uptime: {self.loop_count}s)")
                
                # Sleep and increment
                time.sleep(1)
                self.loop_count += 1
                
            except KeyboardInterrupt:
                logger.info("\n⚠️  Service interrupted by user")
                break
            except Exception as e:
                logger.error(f"Service loop error: {e}")
                time.sleep(5)
        
        self.cleanup()
    
    def cleanup(self):
        """Clean shutdown"""
        logger.info("\n🔴 Shutting down service...")
        
        # Disable engine for safety
        self.relay.disable_engine()
        
        # Disconnect hardware
        self.gps.disconnect()
        self.gsm.disconnect()
        
        logger.info("✅ Service stopped cleanly")


if __name__ == "__main__":
    try:
        service = VehicleSecurityService()
        service.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)