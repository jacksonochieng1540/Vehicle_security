"""
Alerts URL Configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.alert_list, name='alert_list'),
    path('<int:alert_id>/', views.alert_detail, name='alert_detail'),
    path('<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('rules/', views.alert_rules, name='alert_rules'),
    path('logs/', views.notification_logs, name='notification_logs'),
]