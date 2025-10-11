"""
URL patterns for User Activity Monitoring
"""
from django.urls import path
from . import activity_views, forms_activity

app_name = 'accounts'

urlpatterns = [
    # Activity Dashboard
    path('activity-dashboard/', activity_views.activity_dashboard, name='activity_dashboard'),
    
    # User Activities
    path('activities/', activity_views.user_activity_list, name='user_activity_list'),
    path('activities/<int:activity_id>/', activity_views.activity_detail, name='activity_detail'),
    path('activities/export/', activity_views.export_activities, name='export_activities'),
    
    # Activity Alerts
    path('alerts/', activity_views.activity_alerts, name='activity_alerts'),
    path('alerts/<int:alert_id>/resolve/', activity_views.resolve_alert, name='resolve_alert'),
    
    # User Sessions
    path('sessions/', activity_views.user_sessions, name='user_sessions'),
    path('sessions/<str:session_key>/', activity_views.session_detail, name='session_detail'),
    
    # Statistics and Reports
    path('activity-statistics/', activity_views.activity_statistics, name='activity_statistics'),
    path('live-monitor/', activity_views.live_activity_monitor, name='live_monitor'),
    
    # API Endpoints for live updates
    path('api/recent-activities/', activity_views.api_recent_activities, name='api_recent_activities'),
    path('api/system-status/', activity_views.api_system_status, name='api_system_status'),
]
