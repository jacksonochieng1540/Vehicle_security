"""
Alerts Views
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Alert, NotificationLog, AlertRule
from vehicle_tracking.models import Vehicle


@login_required
def alert_list(request):
    """List all alerts for user's vehicles"""
    # Get user's vehicles
    if request.user.role == 'owner':
        vehicles = Vehicle.objects.filter(owner=request.user)
    elif request.user.vehicle:
        vehicles = Vehicle.objects.filter(id=request.user.vehicle.id)
    else:
        vehicles = Vehicle.objects.none()
    
    # Filter alerts
    alerts = Alert.objects.filter(vehicle__in=vehicles)
    
    # Apply filters from request
    status = request.GET.get('status')
    severity = request.GET.get('severity')
    alert_type = request.GET.get('type')
    
    if status:
        alerts = alerts.filter(status=status)
    if severity:
        alerts = alerts.filter(severity=severity)
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)
    
    # Count statistics
    total_alerts = alerts.count()
    pending_alerts = alerts.filter(status='pending').count()
    critical_alerts = alerts.filter(severity='critical', status__in=['pending', 'sent']).count()
    
    context = {
        'alerts': alerts,
        'total_alerts': total_alerts,
        'pending_alerts': pending_alerts,
        'critical_alerts': critical_alerts,
        'current_status': status,
        'current_severity': severity,
        'current_type': alert_type,
    }
    return render(request, 'alerts/alert_list.html', context)


@login_required
def alert_detail(request, alert_id):
    """View alert details"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    # Check permission
    if request.user.role != 'owner' and request.user.vehicle != alert.vehicle:
        messages.error(request, 'You do not have permission to view this alert.')
        return redirect('alerts:alert_list')
    
    # Get notification logs for this alert
    notification_logs = NotificationLog.objects.filter(alert=alert)
    
    context = {
        'alert': alert,
        'notification_logs': notification_logs,
    }
    return render(request, 'alerts/alert_detail.html', context)


@login_required
@require_http_methods(["POST"])
def acknowledge_alert(request, alert_id):
    """Acknowledge an alert"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    # Check permission
    if request.user.role != 'owner' and request.user.vehicle != alert.vehicle:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    alert.status = 'acknowledged'
    alert.acknowledged_by = request.user
    alert.acknowledged_at = timezone.now()
    alert.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Alert acknowledged successfully'
    })


@login_required
def alert_rules(request):
    """Manage alert rules"""
    # Get user's vehicles
    if request.user.role == 'owner':
        vehicles = Vehicle.objects.filter(owner=request.user)
    elif request.user.vehicle:
        vehicles = Vehicle.objects.filter(id=request.user.vehicle.id)
    else:
        vehicles = Vehicle.objects.none()
    
    rules = AlertRule.objects.filter(vehicle__in=vehicles)
    
    context = {
        'rules': rules,
        'vehicles': vehicles,
    }
    return render(request, 'alerts/alert_rules.html', context)


@login_required
def notification_logs(request):
    """View notification logs"""
    # Get user's vehicles
    if request.user.role == 'owner':
        vehicles = Vehicle.objects.filter(owner=request.user)
    elif request.user.vehicle:
        vehicles = Vehicle.objects.filter(id=request.user.vehicle.id)
    else:
        vehicles = Vehicle.objects.none()
    
    logs = NotificationLog.objects.filter(alert__vehicle__in=vehicles).select_related(
        'alert', 'recipient'
    )
    
    context = {
        'logs': logs,
    }
    return render(request, 'alerts/notification_logs.html', context)