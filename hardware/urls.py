"""
Hardware URL Configuration
"""
from django.urls import path
from . import api_views

urlpatterns = [
    path('api/authenticate/', api_views.authenticate_driver_api, name='api_authenticate'),
    path('api/location/', api_views.update_location_api, name='api_update_location'),
    path('api/heartbeat/', api_views.heartbeat_api, name='api_heartbeat'),
    path('api/vehicle/<int:vehicle_id>/status/', api_views.get_vehicle_status_api, name='api_vehicle_status'),
]