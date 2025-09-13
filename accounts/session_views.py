"""
Session management views for handling session timeout, extension, and activity tracking.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


@require_POST
@csrf_protect
@login_required
def extend_session(request):
    """
    AJAX endpoint to extend user session.
    Resets the session timeout and updates last activity time.
    """
    try:
        # Update last activity time in session
        now = timezone.now()
        request.session['last_activity'] = now.timestamp()
        
        # Reset session start time to extend the timeout
        request.session['session_start_time'] = now.timestamp()
        
        # Mark session as modified to ensure it's saved
        request.session.modified = True
        
        # Get session timeout for response
        timeout_seconds = get_timeout_for_user(request.user)
        
        logger.info(f"Session extended for user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Session extended successfully',
            'new_timeout': timeout_seconds,
            'timestamp': now.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error extending session for user {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to extend session',
            'message': str(e)
        }, status=500)


@require_POST
@csrf_protect
@login_required
def activity_ping(request):
    """
    AJAX endpoint to record user activity without extending full session.
    This helps track user engagement and can be used for analytics.
    """
    try:
        # Update last activity time
        now = timezone.now()
        request.session['last_activity'] = now.timestamp()
        
        # Don't extend full session, just update activity
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'timestamp': now.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error recording activity ping for user {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to record activity'
        }, status=500)


@login_required
def session_status(request):
    """
    Get current session status including time remaining and warnings.
    """
    try:
        now = timezone.now()
        
        # Get session times
        session_start = request.session.get('session_start_time')
        last_activity = request.session.get('last_activity')
        
        if not session_start or not last_activity:
            return JsonResponse({
                'success': False,
                'error': 'Invalid session data'
            }, status=400)
        
        session_start_time = timezone.datetime.fromtimestamp(session_start, tz=timezone.get_current_timezone())
        last_activity_time = timezone.datetime.fromtimestamp(last_activity, tz=timezone.get_current_timezone())
        
        # Calculate timeouts
        timeout_seconds = get_timeout_for_user(request.user)
        time_since_activity = (now - last_activity_time).total_seconds()
        time_remaining = max(0, timeout_seconds - time_since_activity)
        
        warning_threshold = getattr(settings, 'SESSION_TIMEOUT_WARNING', 300)
        show_warning = time_since_activity > (timeout_seconds - warning_threshold)
        
        status = {
            'success': True,
            'session_start': session_start_time.isoformat(),
            'last_activity': last_activity_time.isoformat(),
            'current_time': now.isoformat(),
            'timeout_seconds': timeout_seconds,
            'time_since_activity': time_since_activity,
            'time_remaining': time_remaining,
            'warning_threshold': warning_threshold,
            'show_warning': show_warning,
            'is_expired': time_remaining <= 0,
            'user_type': get_user_type(request.user)
        }
        
        return JsonResponse(status)
        
    except Exception as e:
        logger.error(f"Error getting session status for user {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to get session status'
        }, status=500)


def get_timeout_for_user(user):
    """
    Get appropriate timeout period based on user type.
    This duplicates logic from SessionTimeoutMiddleware for consistency.
    """
    # Check if user is a patient (has patient portal access)
    if hasattr(user, 'patient_profile') or 'patient_portal' in user.groups.values_list('name', flat=True):
        return getattr(settings, 'PATIENT_SESSION_TIMEOUT', 1200)  # 20 minutes
    
    # Staff members get longer sessions
    return getattr(settings, 'STAFF_SESSION_TIMEOUT', 1200)  # 20 minutes


def get_user_type(user):
    """
    Determine user type for session management purposes.
    """
    if user.is_superuser:
        return 'superuser'
    elif user.is_staff:
        return 'staff'
    elif hasattr(user, 'patient_profile') or 'patient_portal' in user.groups.values_list('name', flat=True):
        return 'patient'
    else:
        return 'regular'