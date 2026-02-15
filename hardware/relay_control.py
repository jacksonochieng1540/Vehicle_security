"""
Relay Control Module
Controls vehicle engine immobilization via GPIO
"""
import time


class RelayController:
    """
    Relay control for engine immobilization
    Uses Raspberry Pi GPIO to control relay module
    """
    
    def __init__(self, pin=None):
        """
        Initialize relay controller
        
        Args:
            pin: GPIO pin number (BCM numbering)
        """
        from django.conf import settings
        self.pin = pin or settings.HARDWARE_CONFIG.get('RELAY_GPIO_PIN', 17)
        self.gpio_initialized = False
        self.engine_state = False
        
        self._init_gpio()
    
    def _init_gpio(self):
        """Initialize GPIO"""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, GPIO.LOW)  # Start with engine disabled
            self.gpio_initialized = True
            print(f"GPIO initialized on pin {self.pin}")
        except Exception as e:
            print(f"GPIO initialization error: {e}")
            print("Relay controller will run in simulation mode")
    
    def enable_engine(self):
        """
        Enable vehicle engine (activate relay)
        
        Returns:
            Boolean success status
        """
        try:
            if self.gpio_initialized:
                import RPi.GPIO as GPIO
                GPIO.output(self.pin, GPIO.HIGH)
            
            self.engine_state = True
            print("Engine ENABLED")
            return True
        except Exception as e:
            print(f"Enable engine error: {e}")
            return False
    
    def disable_engine(self):
        """
        Disable vehicle engine (deactivate relay)
        
        Returns:
            Boolean success status
        """
        try:
            if self.gpio_initialized:
                import RPi.GPIO as GPIO
                GPIO.output(self.pin, GPIO.LOW)
            
            self.engine_state = False
            print("Engine DISABLED")
            return True
        except Exception as e:
            print(f"Disable engine error: {e}")
            return False
    
    def get_engine_state(self):
        """
        Get current engine state
        
        Returns:
            Boolean (True = enabled, False = disabled)
        """
        return self.engine_state
    
    def pulse_relay(self, duration=1.0):
        """
        Pulse the relay (on then off)
        
        Args:
            duration: Pulse duration in seconds
        """
        self.enable_engine()
        time.sleep(duration)
        self.disable_engine()
    
    def cleanup(self):
        """Cleanup GPIO on exit"""
        if self.gpio_initialized:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup(self.pin)
            except Exception as e:
                print(f"GPIO cleanup error: {e}")


class SimulatedRelayController(RelayController):
    """
    Simulated relay controller for testing without Raspberry Pi
    """
    
    def _init_gpio(self):
        """Simulated GPIO initialization"""
        self.gpio_initialized = True
        print(f"Simulated relay controller initialized on pin {self.pin}")
    
    def enable_engine(self):
        """Simulate engine enable"""
        self.engine_state = True
        print("[SIMULATION] Engine ENABLED (Relay activated)")
        return True
    
    def disable_engine(self):
        """Simulate engine disable"""
        self.engine_state = False
        print("[SIMULATION] Engine DISABLED (Relay deactivated)")
        return True


# Factory function
def get_relay_controller(simulated=False):
    """
    Get relay controller instance
    
    Args:
        simulated: If True, return simulated controller
    """
    if simulated:
        return SimulatedRelayController()
    
    # Try to use real GPIO, fall back to simulation if not available
    try:
        import RPi.GPIO
        return RelayController()
    except ImportError:
        print("RPi.GPIO not available, using simulated relay controller")
        return SimulatedRelayController()