"""
Core Celery tasks for system maintenance and session management.
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.conf import settings
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_sessions():
    """
    Clean up expired sessions from the database.
    This task runs every hour to maintain database performance.
    """
    try:
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        count = expired_sessions.count()
        
        if count > 0:
            expired_sessions.delete()
            logger.info(f"Cleaned up {count} expired sessions")
        else:
            logger.info("No expired sessions to clean up")
            
        return {'cleaned_sessions': count}
        
    except Exception as exc:
        logger.error(f"Error cleaning up expired sessions: {str(exc)}")
        return {'error': str(exc)}


@shared_task
def cleanup_old_session_data():
    """
    Additional cleanup for session-related data that might not be automatically cleaned.
    This runs daily to ensure optimal performance.
    """
    try:
        # Clean up sessions older than the maximum age
        max_age_days = getattr(settings, 'SESSION_MAX_AGE_DAYS', 30)
        cutoff_date = timezone.now() - timedelta(days=max_age_days)
        
        old_sessions = Session.objects.filter(expire_date__lt=cutoff_date)
        count = old_sessions.count()
        
        if count > 0:
            old_sessions.delete()
            logger.info(f"Cleaned up {count} old sessions (older than {max_age_days} days)")
        else:
            logger.info(f"No old sessions to clean up (older than {max_age_days} days)")
            
        return {'cleaned_old_sessions': count}
        
    except Exception as exc:
        logger.error(f"Error cleaning up old session data: {str(exc)}")
        return {'error': str(exc)}


@shared_task
def monitor_active_sessions():
    """
    Monitor active sessions and generate statistics.
    This can be used for administrative monitoring and security purposes.
    """
    try:
        now = timezone.now()
        
        # Count active sessions
        active_sessions = Session.objects.filter(expire_date__gt=now)
        total_active = active_sessions.count()
        
        # Count sessions by age
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        one_week_ago = now - timedelta(weeks=1)
        
        recent_sessions = active_sessions.filter(expire_date__gte=one_hour_ago).count()
        daily_sessions = active_sessions.filter(expire_date__gte=one_day_ago).count()
        weekly_sessions = active_sessions.filter(expire_date__gte=one_week_ago).count()
        
        stats = {
            'total_active_sessions': total_active,
            'recent_sessions_1h': recent_sessions,
            'active_sessions_24h': daily_sessions,
            'active_sessions_7d': weekly_sessions,
            'timestamp': now.isoformat()
        }
        
        logger.info(f"Session statistics: {stats}")
        return stats
        
    except Exception as exc:
        logger.error(f"Error monitoring active sessions: {str(exc)}")
        return {'error': str(exc)}


@shared_task
def generate_session_security_report():
    """
    Generate a security report for session management.
    This can help identify potential security issues or unusual patterns.
    """
    try:
        now = timezone.now()
        
        # Get session statistics
        total_sessions = Session.objects.count()
        active_sessions = Session.objects.filter(expire_date__gt=now).count()
        expired_sessions = total_sessions - active_sessions
        
        # Detect unusually long sessions (potentially suspicious)
        long_session_threshold = getattr(settings, 'SESSION_SECURITY_LONG_THRESHOLD', 7200)  # 2 hours
        suspicious_sessions = Session.objects.filter(
            expire_date__gt=now + timedelta(seconds=long_session_threshold)
        ).count()
        
        report = {
            'timestamp': now.isoformat(),
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'expired_sessions': expired_sessions,
            'potentially_suspicious_sessions': suspicious_sessions,
            'recommendations': []
        }
        
        # Add recommendations based on findings
        if suspicious_sessions > 0:
            report['recommendations'].append(
                f"Found {suspicious_sessions} unusually long sessions. Consider reviewing session timeout settings."
            )
        
        if expired_sessions > total_sessions * 0.5:
            report['recommendations'].append(
                "High number of expired sessions. Consider running cleanup more frequently."
            )
        
        logger.info(f"Session security report generated: {report}")
        return report
        
    except Exception as exc:
        logger.error(f"Error generating session security report: {str(exc)}")
        return {'error': str(exc)}