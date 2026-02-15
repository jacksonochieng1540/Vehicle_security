"""
GPS Module Integration
Handles communication with Neo-6M GPS module via serial
"""
import serial
import pynmea2
from datetime import datetime
from django.conf import settings
import threading
import time


class GPSModule:
    """
    GPS module handler for Neo-6M GPS
    Communicates via serial port and parses NMEA sentences
    """
    
    def __init__(self, port=None, baudrate=None):
        self.port = port or settings.HARDWARE_CONFIG.get('GPS_PORT', '/dev/ttyUSB0')
        self.baudrate = baudrate or settings.HARDWARE_CONFIG.get('GPS_BAUDRATE', 9600)
        self.serial_connection = None
        self.is_running = False
        self.current_location = None
        self.last_update = None
        
    def connect(self):
        """Establish connection to GPS module"""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            return True
        except Exception as e:
            print(f"GPS connection error: {e}")
            return False
    
    def disconnect(self):
        """Close GPS connection"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.is_running = False
    
    def read_gps_data(self):
        """
        Read and parse GPS data from serial port
        
        Returns:
            Dictionary with GPS data or None
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            return None
        
        try:
            line = self.serial_connection.readline().decode('ascii', errors='replace')
            
            # Parse NMEA sentence
            if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
                msg = pynmea2.parse(line)
                
                # Extract relevant data based on message type
                if hasattr(msg, 'latitude') and msg.latitude:
                    location_data = {
                        'latitude': msg.latitude,
                        'longitude': msg.longitude,
                        'timestamp': datetime.utcnow(),
                        'altitude': getattr(msg, 'altitude', None),
                        'speed': getattr(msg, 'spd_over_grnd', None),
                        'heading': getattr(msg, 'true_course', None),
                        'num_satellites': getattr(msg, 'num_sats', None),
                    }
                    
                    self.current_location = location_data
                    self.last_update = datetime.now()
                    
                    return location_data
        except Exception as e:
            print(f"GPS read error: {e}")
        
        return None
    
    def get_current_location(self):
        """
        Get the most recent GPS location
        
        Returns:
            Dictionary with location data or None
        """
        return self.current_location
    
    def start_continuous_reading(self, callback=None, interval=10):
        """
        Start continuous GPS reading in background thread
        
        Args:
            callback: Function to call with each GPS update
            interval: Update interval in seconds
        """
        def read_loop():
            self.is_running = True
            while self.is_running:
                location = self.read_gps_data()
                if location and callback:
                    callback(location)
                time.sleep(interval)
        
        if not self.connect():
            return False
        
        thread = threading.Thread(target=read_loop, daemon=True)
        thread.start()
        return True
    
    def stop_continuous_reading(self):
        """Stop continuous GPS reading"""
        self.is_running = False
        self.disconnect()


class SimulatedGPSModule(GPSModule):
    """
    Simulated GPS module for testing without hardware
    Returns simulated GPS data around JKUAT location
    """
    
    def __init__(self):
        super().__init__()
        # JKUAT approximate coordinates
        self.base_lat = -1.0927
        self.base_lon = 37.0143
        self.variation = 0.001  # Simulate small movements
        
    def connect(self):
        """Simulated connection always succeeds"""
        return True
    
    def read_gps_data(self):
        """
        Generate simulated GPS data
        
        Returns:
            Dictionary with simulated GPS data
        """
        import random
        
        # Simulate small movements
        lat_offset = random.uniform(-self.variation, self.variation)
        lon_offset = random.uniform(-self.variation, self.variation)
        
        location_data = {
            'latitude': self.base_lat + lat_offset,
            'longitude': self.base_lon + lon_offset,
            'timestamp': datetime.utcnow(),
            'altitude': random.uniform(1600, 1650),  # JKUAT elevation
            'speed': random.uniform(0, 60),  # 0-60 km/h
            'heading': random.uniform(0, 360),
            'num_satellites': random.randint(4, 12),
        }
        
        self.current_location = location_data
        self.last_update = datetime.now()
        
        return location_data


# Factory function
def get_gps_module(simulated=False):
    """
    Get GPS module instance
    
    Args:
        simulated: If True, return simulated GPS module
    """
    if simulated:
        return SimulatedGPSModule()
    return GPSModule()