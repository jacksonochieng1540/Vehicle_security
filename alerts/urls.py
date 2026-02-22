from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.alert_list, name='alert_list'),
    path('<int:alert_id>/', views.alert_detail, name='alert_detail'),  # Changed from pk to alert_id
    path('<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),  # Changed
    path('rules/', views.alert_rules, name='alert_rules'),
    path('logs/', views.notification_logs, name='notification_logs'),
]