"""
Hardware API Views
API endpoints for Raspberry Pi to communicate with Django backend
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime

from .authentication_service import get_hardware_service
from vehicle_tracking.models import Vehicle, VehicleLocation
from authentication.models import User


@csrf_exempt
@require_http_methods(["POST"])
def authenticate_driver_api(request):
    """
    API endpoint for driver authentication from Raspberry Pi
    
    POST data:
        - vehicle_id: Vehicle ID
        - image_data: Base64 encoded image (optional)
        - capture_camera: Boolean (optional)
    """
    try:
        data = json.loads(request.body)
        vehicle_id = data.get('vehicle_id')
        
        if not vehicle_id:
            return JsonResponse({
                'success': False,
                'message': 'Vehicle ID required'
            }, status=400)
        
        # Get hardware service
        hardware_service = get_hardware_service(simulated=True)  # Use simulated for now
        
        # Perform authentication
        result = hardware_service.authenticate_driver(
            vehicle_id=vehicle_id,
            capture_from_camera=data.get('capture_camera', True)
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_location_api(request):
    """
    API endpoint for GPS location updates from Raspberry Pi
    
    POST data:
        - vehicle_id: Vehicle ID
        - latitude: Latitude
        - longitude: Longitude
        - altitude: Altitude (optional)
        - speed: Speed (optional)
        - heading: Heading (optional)
    """
    try:
        data = json.loads(request.body)
        vehicle_id = data.get('vehicle_id')
        
        if not vehicle_id:
            return JsonResponse({
                'success': False,
                'message': 'Vehicle ID required'
            }, status=400)
        
        # Get vehicle
        vehicle = Vehicle.objects.get(id=vehicle_id)
        
        # Create location record
        location = VehicleLocation.objects.create(
            vehicle=vehicle,
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            altitude=data.get('altitude'),
            speed=data.get('speed'),
            heading=data.get('heading'),
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Location updated',
            'location_id': location.id
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Vehicle not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def heartbeat_api(request):
    """
    API endpoint for device heartbeat
    
    POST data:
        - device_id: Device ID
        - status: Device status
    """
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        
        from .models import HardwareDevice
        
        device = HardwareDevice.objects.get(device_id=device_id)
        device.status = data.get('status', 'online')
        device.last_heartbeat = datetime.now()
        device.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Heartbeat received'
        })
        
    except HardwareDevice.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Device not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_vehicle_status_api(request, vehicle_id):
    """
    API endpoint to get vehicle status
    """
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        
        return JsonResponse({
            'success': True,
            'vehicle_id': vehicle.id,
            'registration_number': vehicle.registration_number,
            'engine_enabled': vehicle.engine_enabled,
            'status': vehicle.status,
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Vehicle not found'
        }, status=404)