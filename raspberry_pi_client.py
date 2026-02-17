#!/usr/bin/env python3
"""
Raspberry Pi Client Script for Vehicle Security System
This script runs on the Raspberry Pi and communicates with the Django backend
"""

import time
import requests
import cv2
import json
from datetime import datetime

# Configuration
DJANGO_SERVER = "http://localhost:8000"  # Change to your server IP
VEHICLE_ID = 1  # Change to your vehicle ID
DEVICE_ID = "RPI_001"  # Unique device identifier

# Hardware initialization flags
USE_REAL_HARDWARE = False  # Set to True when using actual hardware


class VehicleSecurityClient:
    """Main client for Raspberry Pi vehicle security"""
    
    def __init__(self, server_url, vehicle_id, device_id):
        self.server_url = server_url
        self.vehicle_id = vehicle_id
        self.device_id = device_id
        self.camera = None
        
    def initialize_camera(self):
        """Initialize camera for facial recognition"""
        try:
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                print("✓ Camera initialized successfully")
                return True
            else:
                print("✗ Failed to initialize camera")
                return False
        except Exception as e:
            print(f"✗ Camera error: {e}")
            return False
    
    def capture_image(self):
        """Capture image from camera"""
        if not self.camera or not self.camera.isOpened():
            print("Camera not initialized")
            return None
        
        # Allow camera to warm up
        time.sleep(0.5)
        
        # Capture frame
        ret, frame = self.camera.read()
        
        if ret:
            print("✓ Image captured")
            return frame
        else:
            print("✗ Failed to capture image")
            return None
    
    def authenticate_driver(self):
        """
        Authenticate driver using facial recognition
        """
        print("\n" + "="*50)
        print("Starting Driver Authentication...")
        print("="*50)
        
        # Capture image
        image = self.capture_image()
        if image is None:
            print("✗ Authentication failed: No image captured")
            return False
        
        # Save image temporarily for debugging
        cv2.imwrite('/tmp/auth_attempt.jpg', image)
        print("✓ Image saved to /tmp/auth_attempt.jpg")
        
        # Send authentication request to Django backend
        try:
            url = f"{self.server_url}/hardware/api/authenticate/"
            data = {
                'vehicle_id': self.vehicle_id,
                'capture_camera': True
            }
            
            print(f"Sending authentication request to {url}...")
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    print("\n" + "✓"*25)
                    print("AUTHENTICATION SUCCESSFUL!")
                    print("✓"*25)
                    print(f"User: {result.get('message')}")
                    print(f"Confidence: {result.get('confidence', 0):.2%}")
                    print(f"Engine Status: {'ENABLED' if result.get('engine_enabled') else 'DISABLED'}")
                    return True
                else:
                    print("\n" + "✗"*25)
                    print("AUTHENTICATION FAILED!")
                    print("✗"*25)
                    print(f"Reason: {result.get('message')}")
                    print(f"Alert Created: {result.get('alert_created', False)}")
                    return False
            else:
                print(f"✗ Server error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Communication error: {e}")
            return False
    
    def update_gps_location(self, latitude, longitude, speed=0, altitude=None):
        """
        Send GPS location update to server
        """
        try:
            url = f"{self.server_url}/hardware/api/location/"
            data = {
                'vehicle_id': self.vehicle_id,
                'latitude': latitude,
                'longitude': longitude,
                'speed': speed,
                'altitude': altitude
            }
            
            response = requests.post(url, json=data, timeout=5)
            
            if response.status_code == 200:
                print(f"✓ Location updated: {latitude:.6f}, {longitude:.6f}")
                return True
            else:
                print(f"✗ Location update failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Location update error: {e}")
            return False
    
    def send_heartbeat(self):
        """Send device heartbeat to server"""
        try:
            url = f"{self.server_url}/hardware/api/heartbeat/"
            data = {
                'device_id': self.device_id,
                'status': 'online'
            }
            
            response = requests.post(url, json=data, timeout=5)
            
            if response.status_code == 200:
                return True
            return False
                
        except Exception as e:
            print(f"Heartbeat error: {e}")
            return False
    
    def get_vehicle_status(self):
        """Get current vehicle status from server"""
        try:
            url = f"{self.server_url}/hardware/api/vehicle/{self.vehicle_id}/status/"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            return None
                
        except Exception as e:
            print(f"Status check error: {e}")
            return None
    
    def run(self):
        """Main loop"""
        print("\n" + "="*50)
        print("VEHICLE SECURITY SYSTEM - RASPBERRY PI CLIENT")
        print("="*50)
        print(f"Server: {self.server_url}")
        print(f"Vehicle ID: {self.vehicle_id}")
        print(f"Device ID: {self.device_id}")
        print("="*50 + "\n")
        
        # Initialize camera
        if not self.initialize_camera():
            print("Warning: Running without camera")
        
        # Check vehicle status
        print("Checking vehicle status...")
        status = self.get_vehicle_status()
        if status:
            print(f"✓ Vehicle: {status.get('registration_number')}")
            print(f"✓ Engine: {'ENABLED' if status.get('engine_enabled') else 'DISABLED'}")
        
        try:
            while True:
                print("\n" + "-"*50)
                print("Options:")
                print("1. Authenticate Driver")
                print("2. Update GPS Location (Simulated)")
                print("3. Check Vehicle Status")
                print("4. Send Heartbeat")
                print("5. Exit")
                print("-"*50)
                
                choice = input("Enter choice (1-5): ").strip()
                
                if choice == '1':
                    self.authenticate_driver()
                    
                elif choice == '2':
                    # Simulated GPS location (JKUAT area)
                    lat = -1.0927
                    lon = 37.0143
                    speed = 45.5
                    self.update_gps_location(lat, lon, speed)
                    
                elif choice == '3':
                    status = self.get_vehicle_status()
                    if status:
                        print(json.dumps(status, indent=2))
                    
                elif choice == '4':
                    if self.send_heartbeat():
                        print("✓ Heartbeat sent")
                    else:
                        print("✗ Heartbeat failed")
                    
                elif choice == '5':
                    print("Exiting...")
                    break
                    
                else:
                    print("Invalid choice")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        
        finally:
            if self.camera:
                self.camera.release()
            print("Goodbye!")


def main():
    """Entry point"""
    client = VehicleSecurityClient(
        server_url=DJANGO_SERVER,
        vehicle_id=VEHICLE_ID,
        device_id=DEVICE_ID
    )
    
    client.run()


if __name__ == "__main__":
    main()