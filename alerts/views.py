"""
Alerts Views
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Alert, NotificationLog, AlertRule
from vehicle_tracking.models import Vehicle


@login_required
def alert_list(request):
    """List all alerts for user's vehicles"""
    # Get user's vehicles
    if request.user.role == 'owner':
        vehicles = Vehicle.objects.filter(owner=request.user)
    elif hasattr(request.user, 'vehicle') and request.user.vehicle:
        vehicles = Vehicle.objects.filter(id=request.user.vehicle.id)
    else:
        vehicles = Vehicle.objects.none()
    
    # Filter alerts
    alerts = Alert.objects.filter(vehicle__in=vehicles).order_by('-created_at')
    
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
    pending_alerts = alerts.filter(status='active').count()
    critical_alerts = alerts.filter(severity='critical', status__in=['active', 'sent']).count()
    
    # Add pagination
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'alerts': page_obj,  # Keep both for template compatibility
        'page_obj': page_obj,
        'total_alerts': total_alerts,
        'pending_alerts': pending_alerts,
        'critical_alerts': critical_alerts,
        'current_status': status,
        'current_severity': severity,
        'current_type': alert_type,
    }
    return render(request, 'alerts/alert_list.html', context)


@login_required
def alert_detail(request, alert_id):  # Changed from pk to alert_id
    """View alert details"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    # Check permission
    if request.user.role != 'owner' and (not hasattr(request.user, 'vehicle') or request.user.vehicle != alert.vehicle):
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
def acknowledge_alert(request, alert_id):  # Changed from pk to alert_id
    """Acknowledge an alert"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    # Check permission
    if request.user.role != 'owner' and (not hasattr(request.user, 'vehicle') or request.user.vehicle != alert.vehicle):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Permission denied'})
        messages.error(request, 'Permission denied')
        return redirect('alerts:alert_list')
    
    alert.status = 'acknowledged'
    alert.acknowledged_by = request.user
    alert.acknowledged_at = timezone.now()
    alert.save()
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Alert acknowledged successfully'
        })
    
    messages.success(request, 'Alert acknowledged successfully')
    return redirect('alerts:alert_detail', alert_id=alert_id)


@login_required
def alert_rules(request):
    """Manage alert rules"""
    # Get user's vehicles
    if request.user.role == 'owner':
        vehicles = Vehicle.objects.filter(owner=request.user)
    elif hasattr(request.user, 'vehicle') and request.user.vehicle:
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
    elif hasattr(request.user, 'vehicle') and request.user.vehicle:
        vehicles = Vehicle.objects.filter(id=request.user.vehicle.id)
    else:
        vehicles = Vehicle.objects.none()
    
    # Fix: Use sent_at instead of created_at (based on error message)
    logs = NotificationLog.objects.filter(alert__vehicle__in=vehicles).select_related(
        'alert', 'recipient'
    ).order_by('-sent_at')  # Changed from created_at to sent_at
    
    # Add pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'alerts/notification_logs.html', context)