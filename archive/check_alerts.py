import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from accounts.models import ActivityAlert, UserActivity, UserSession

def check_alerts():
    """Check the database for alerts and create some sample data if needed"""
    
    print("Checking ActivityAlert table...")
    
    # Check if table exists
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts_activityalert'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("ActivityAlert table does not exist!")
            return
    
    # Check if there are any alerts
    alert_count = ActivityAlert.objects.count()
    print(f"Total alerts in database: {alert_count}")
    
    if alert_count > 0:
        # Show sample alerts
        alerts = ActivityAlert.objects.all()[:5]
        for alert in alerts:
            print(f"  - {alert.alert_type} ({alert.severity}) - {alert.user} - {alert.created_at}")
    else:
        print("No alerts found. Creating some sample alerts for testing...")
        
        # Check if we have users
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(is_superuser=True).all()[:3]
        
        if not users:
            print("No users found. Please create some users first.")
            return
        
        # Create sample alerts
        import random
        from django.utils import timezone
        
        alert_types = [choice[0] for choice in ActivityAlert.ALERT_TYPES]
        severity_levels = [choice[0] for choice in ActivityAlert.SEVERITY_LEVELS]
        
        for i, user in enumerate(users):
            for j in range(3):
                ActivityAlert.objects.create(
                    user=user,
                    alert_type=random.choice(alert_types),
                    severity=random.choice(severity_levels),
                    message=f"Sample alert {j+1} for {user.username}",
                    ip_address=f"192.168.1.{100+i}",
                    metadata={"sample": True, "generated": True}
                )
        
        print(f"Created {len(users) * 3} sample alerts")
        
        # Check alerts again
        alert_count = ActivityAlert.objects.count()
        print(f"Total alerts after creation: {alert_count}")
    
    # Check UserActivity count
    activity_count = UserActivity.objects.count()
    print(f"Total user activities: {activity_count}")
    
    # Check UserSession count
    session_count = UserSession.objects.count()
    print(f"Total user sessions: {session_count}")

if __name__ == "__main__":
    check_alerts()
