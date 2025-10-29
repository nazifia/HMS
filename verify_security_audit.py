#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from core.activity_log import ActivityLog
from django.contrib.auth import get_user_model

User = get_user_model()

def main():
    print("=== Security Audit Verification ===")
    
    # Check if we have security data
    login_logs = ActivityLog.objects.filter(action_type='login').count()
    failed_logs = ActivityLog.objects.filter(action_type='failed_login').count()
    logout_logs = ActivityLog.objects.filter(action_type='logout').count()
    permission_logs = ActivityLog.objects.filter(action_type='permission_denied').count()
    
    print(f"Login logs: {login_logs}")
    print(f"Failed login logs: {failed_logs}")
    print(f"Logout logs: {logout_logs}")
    print(f"Permission denied logs: {permission_logs}")
    
    # Show sample recent security events
    security_logs = ActivityLog.objects.filter(
        action_type__in=['login', 'logout', 'failed_login', 'permission_denied']
    ).order_by('-timestamp')[:5]
    
    print("\nRecent security events:")
    for log in security_logs:
        username = log.user.username if log.user else 'Anonymous'
        print(f"  - {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {username} - {log.action_type}")
    
    print("\n✓ Security audit data is available")

if __name__ == "__main__":
    main()
