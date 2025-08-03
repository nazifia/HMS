
"""
System Health Check for HMS
"""
import json
import time
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from django.contrib.auth import get_user_model

def system_health_check(request):
    """Comprehensive system health check"""
    health_status = {
        'timestamp': time.time(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = {'status': 'healthy', 'response_time': 'fast'}
    except Exception as e:
        health_status['checks']['database'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    # User model check
    try:
        User = get_user_model()
        user_count = User.objects.count()
        health_status['checks']['user_model'] = {'status': 'healthy', 'user_count': user_count}
    except Exception as e:
        health_status['checks']['user_model'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Settings check
    try:
        debug_mode = settings.DEBUG
        health_status['checks']['settings'] = {'status': 'healthy', 'debug_mode': debug_mode}
    except Exception as e:
        health_status['checks']['settings'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    return JsonResponse(health_status)
