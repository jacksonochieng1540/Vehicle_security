"""
Vehicle Tracking URL Configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/<int:vehicle_id>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicles/<int:vehicle_id>/control/', views.vehicle_control, name='vehicle_control'),
    path('vehicles/<int:vehicle_id>/location/', views.vehicle_location_api, name='vehicle_location_api'),
    path('vehicles/<int:vehicle_id>/history/', views.vehicle_tracking_history, name='vehicle_history'),
]