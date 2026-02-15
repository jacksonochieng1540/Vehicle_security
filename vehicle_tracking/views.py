"""
Vehicle Tracking Views
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from .models import Vehicle, VehicleLocation, VehicleEvent, Geofence
from authentication.models import AuthenticationLog


@login_required
def dashboard_home(request):
    """Main dashboard view"""
    # Get user's vehicles
    if request.user.role == 'owner':
        vehicles = Vehicle.objects.filter(owner=request.user)
    elif request.user.vehicle:
        vehicles = Vehicle.objects.filter(id=request.user.vehicle.id)
    else:
        vehicles = Vehicle.objects.none()
    
    # Get recent events
    recent_events = VehicleEvent.objects.filter(
        vehicle__in=vehicles
    ).select_related('vehicle', 'user')[:10]
    
    # Get recent authentication logs
    recent_auth_logs = AuthenticationLog.objects.filter(
        vehicle__in=vehicles
    ).select_related('user', 'vehicle')[:10]
    
    # Count statistics
    total_vehicles = vehicles.count()
    active_vehicles = vehicles.filter(status='active').count()
    recent_alerts = VehicleEvent.objects.filter(
        vehicle__in=vehicles,
        event_type__in=['unauthorized_access', 'auth_failed', 'geofence_breach'],
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    context = {
        'vehicles': vehicles,
        'recent_events': recent_events,
        'recent_auth_logs': recent_auth_logs,
        'total_vehicles': total_vehicles,
        'active_vehicles': active_vehicles,
        'recent_alerts': recent_alerts,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def vehicle_list(request):
    """List all vehicles"""
    if request.user.role == 'owner':
        vehicles = Vehicle.objects.filter(owner=request.user)
    elif request.user.vehicle:
        vehicles = Vehicle.objects.filter(id=request.user.vehicle.id)
    else:
        vehicles = Vehicle.objects.none()
    
    context = {'vehicles': vehicles}
    return render(request, 'vehicle_tracking/vehicle_list.html', context)


@login_required
def vehicle_detail(request, vehicle_id):
    """View vehicle details and tracking"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    
    # Check permission
    if request.user.role != 'owner' and request.user.vehicle != vehicle:
        messages.error(request, 'You do not have permission to view this vehicle.')
        return redirect('dashboard:home')
    
    # Get current location
    current_location = vehicle.get_current_location()
    
    # Get recent locations for map
    recent_locations = VehicleLocation.objects.filter(vehicle=vehicle)[:50]
    
    # Get recent events
    recent_events = VehicleEvent.objects.filter(vehicle=vehicle)[:20]
    
    # Get geofences
    geofences = Geofence.objects.filter(vehicle=vehicle, is_active=True)
    
    context = {
        'vehicle': vehicle,
        'current_location': current_location,
        'recent_locations': recent_locations,
        'recent_events': recent_events,
        'geofences': geofences,
    }
    return render(request, 'vehicle_tracking/vehicle_detail.html', context)


@login_required
@require_http_methods(["POST"])
def vehicle_control(request, vehicle_id):
    """Remote vehicle control (enable/disable engine)"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    
    # Check permission
    if request.user.role != 'owner' and request.user.vehicle != vehicle:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    action = request.POST.get('action')
    
    if action == 'disable':
        vehicle.engine_enabled = False
        vehicle.save()
        
        # Log event
        VehicleEvent.objects.create(
            vehicle=vehicle,
            event_type='remote_immobilize',
            description=f'Engine remotely disabled by {request.user.get_full_name()}',
            user=request.user,
            location=vehicle.get_current_location()
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Engine disabled successfully',
            'engine_enabled': False
        })
        
    elif action == 'enable':
        vehicle.engine_enabled = True
        vehicle.save()
        
        # Log event
        VehicleEvent.objects.create(
            vehicle=vehicle,
            event_type='remote_enable',
            description=f'Engine remotely enabled by {request.user.get_full_name()}',
            user=request.user,
            location=vehicle.get_current_location()
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Engine enabled successfully',
            'engine_enabled': True
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid action'})


@login_required
def vehicle_location_api(request, vehicle_id):
    """API endpoint for real-time location updates"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    
    # Check permission
    if request.user.role != 'owner' and request.user.vehicle != vehicle:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    current_location = vehicle.get_current_location()
    
    if current_location:
        data = {
            'latitude': float(current_location.latitude),
            'longitude': float(current_location.longitude),
            'speed': float(current_location.speed) if current_location.speed else 0,
            'heading': float(current_location.heading) if current_location.heading else 0,
            'timestamp': current_location.timestamp.isoformat(),
            'engine_enabled': vehicle.engine_enabled,
            'status': vehicle.status,
        }
    else:
        data = {
            'error': 'No location data available'
        }
    
    return JsonResponse(data)


@login_required
def vehicle_tracking_history(request, vehicle_id):
    """View vehicle tracking history"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    
    # Check permission
    if request.user.role != 'owner' and request.user.vehicle != vehicle:
        messages.error(request, 'You do not have permission to view this vehicle.')
        return redirect('dashboard:home')
    
    # Get date range from request
    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)
    
    locations = VehicleLocation.objects.filter(
        vehicle=vehicle,
        timestamp__gte=start_date
    )
    
    context = {
        'vehicle': vehicle,
        'locations': locations,
        'days': days,
    }
    return render(request, 'vehicle_tracking/history.html', context)