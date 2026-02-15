"""
GSM Module Integration
Handles SMS communication via SIM800C module
"""
import serial
import time
from django.conf import settings


class GSMModule:
    """
    GSM module handler for SIM800C
    Sends SMS alerts and manages mobile communication
    """
    
    def __init__(self, port=None, baudrate=None):
        self.port = port or settings.GSM_CONFIG.get('GSM_PORT', '/dev/ttyUSB1')
        self.baudrate = baudrate or settings.GSM_CONFIG.get('GSM_BAUDRATE', 115200)
        self.serial_connection = None
        self.timeout = settings.GSM_CONFIG.get('SMS_TIMEOUT', 30)
        
    def connect(self):
        """Establish connection to GSM module"""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            time.sleep(2)  # Wait for module to initialize
            
            # Test connection
            if self.send_at_command('AT'):
                print("GSM module connected successfully")
                return True
            return False
        except Exception as e:
            print(f"GSM connection error: {e}")
            return False
    
    def disconnect(self):
        """Close GSM connection"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
    
    def send_at_command(self, command, wait_time=1):
        """
        Send AT command to GSM module
        
        Args:
            command: AT command string
            wait_time: Time to wait for response
            
        Returns:
            Response string or None
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            return None
        
        try:
            # Clear buffer
            self.serial_connection.reset_input_buffer()
            
            # Send command
            self.serial_connection.write((command + '\r\n').encode())
            time.sleep(wait_time)
            
            # Read response
            response = self.serial_connection.read(self.serial_connection.in_waiting).decode('utf-8', errors='ignore')
            return response
        except Exception as e:
            print(f"AT command error: {e}")
            return None
    
    def send_sms(self, phone_number, message):
        """
        Send SMS message
        
        Args:
            phone_number: Recipient phone number (format: +254712345678)
            message: SMS message text
            
        Returns:
            Boolean success status
        """
        if not self.serial_connection:
            if not self.connect():
                return False
        
        try:
            # Set SMS mode to text
            response = self.send_at_command('AT+CMGF=1', 1)
            if not response or 'OK' not in response:
                return False
            
            # Set phone number
            response = self.send_at_command(f'AT+CMGS="{phone_number}"', 2)
            if not response or '>' not in response:
                return False
            
            # Send message (Ctrl+Z = chr(26) to send)
            self.serial_connection.write((message + chr(26)).encode())
            time.sleep(3)
            
            # Read response
            response = self.serial_connection.read(self.serial_connection.in_waiting).decode('utf-8', errors='ignore')
            
            success = 'OK' in response or '+CMGS' in response
            return success
            
        except Exception as e:
            print(f"SMS send error: {e}")
            return False
    
    def check_signal_strength(self):
        """
        Check GSM signal strength
        
        Returns:
            Signal strength (0-31) or None
        """
        response = self.send_at_command('AT+CSQ')
        if response:
            # Parse response: +CSQ: <rssi>,<ber>
            try:
                parts = response.split(':')
                if len(parts) > 1:
                    rssi = int(parts[1].split(',')[0].strip())
                    return rssi
            except Exception:
                pass
        return None
    
    def get_network_registration(self):
        """
        Check network registration status
        
        Returns:
            Registration status string or None
        """
        response = self.send_at_command('AT+CREG?')
        if response:
            # Parse response: +CREG: <n>,<stat>
            try:
                if '+CREG:' in response:
                    parts = response.split(',')
                    if len(parts) > 1:
                        stat = int(parts[1].strip())
                        statuses = {
                            0: 'Not registered',
                            1: 'Registered (home)',
                            2: 'Searching',
                            3: 'Registration denied',
                            4: 'Unknown',
                            5: 'Registered (roaming)'
                        }
                        return statuses.get(stat, 'Unknown')
            except Exception:
                pass
        return None


class SimulatedGSMModule(GSMModule):
    """
    Simulated GSM module for testing without hardware
    """
    
    def __init__(self):
        super().__init__()
        self.sent_messages = []
        
    def connect(self):
        """Simulated connection always succeeds"""
        print("Simulated GSM module connected")
        return True
    
    def send_sms(self, phone_number, message):
        """
        Simulate SMS sending
        
        Args:
            phone_number: Recipient phone number
            message: SMS message text
            
        Returns:
            Always True (simulated success)
        """
        self.sent_messages.append({
            'phone_number': phone_number,
            'message': message,
            'timestamp': time.time()
        })
        print(f"[SIMULATED SMS] To: {phone_number}, Message: {message}")
        return True
    
    def check_signal_strength(self):
        """Return simulated signal strength"""
        return 25  # Good signal
    
    def get_network_registration(self):
        """Return simulated registration status"""
        return 'Registered (home)'


# SMS Template Functions
def format_unauthorized_access_sms(vehicle_reg, location, timestamp):
    """Format SMS for unauthorized access attempt"""
    message = (
        f"ALERT: Unauthorized access attempt on vehicle {vehicle_reg} "
        f"at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}. "
        f"Location: {location['latitude']:.6f}, {location['longitude']:.6f}. "
        f"Engine has been disabled."
    )
    return message[:160]  # SMS length limit


def format_engine_status_sms(vehicle_reg, enabled, user):
    """Format SMS for engine status change"""
    status = "enabled" if enabled else "disabled"
    message = (
        f"Vehicle {vehicle_reg} engine has been {status} "
        f"by {user}."
    )
    return message[:160]


def format_geofence_alert_sms(vehicle_reg, geofence_name, action):
    """Format SMS for geofence breach"""
    message = (
        f"ALERT: Vehicle {vehicle_reg} has {action} geofence '{geofence_name}'."
    )
    return message[:160]


# Factory function
def get_gsm_module(simulated=False):
    """
    Get GSM module instance
    
    Args:
        simulated: If True, return simulated GSM module
    """
    if simulated:
        return SimulatedGSMModule()
    return GSMModule()