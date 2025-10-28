"""
Script to create sample activity logs for testing
"""
import os
import sys
import django
from datetime import datetime, timedelta
import random
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from core.activity_log import ActivityLog

User = get_user_model()

def create_sample_activities():
    """Create sample activity log entries"""
    
    # Get or create a test user if none exists
    user = User.objects.first()
    if not user:
        print("No users found. Please create a user first.")
        return
    
    # Sample activities data
    sample_activities = [
        {
            'user': user,
            'category': 'authentication',
            'action_type': 'login',
            'description': 'User logged in successfully',
            'ip_address': '192.168.1.100',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'success': True,
            'level': 'info'
        },
        {
            'user': user,
            'category': 'patient_management',
            'action_type': 'view',
            'description': 'Viewed patient record for John Doe',
            'ip_address': '192.168.1.100',
            'success': True,
            'level': 'info'
        },
        {
            'user': user,
            'category': 'pharmacy',
            'action_type': 'dispense',
            'description': 'Dispensed medication: Paracetamol 500mg',
            'ip_address': '192.168.1.100',
            'success': True,
            'level': 'info'
        },
        {
            'user': user,
            'category': 'billing',
            'action_type': 'create',
            'description': 'Created new invoice for consultation fee',
            'ip_address': '192.168.1.100',
            'success': True,
            'level': 'info'
        },
        {
            'user': user,
            'category': 'laboratory',
            'action_type': 'view',
            'description': 'Viewed lab results for patient',
            'ip_address': '192.168.1.100',
            'success': True,
            'level': 'info'
        },
        {
            'user': None,
            'category': 'security',
            'action_type': 'failed_login',
            'description': 'Failed login attempt for user test@example.com',
            'ip_address': '192.168.1.105',
            'success': False,
            'level': 'warning'
        },
        {
            'user': user,
            'category': 'admin_action',
            'action_type': 'update',
            'description': 'Updated user permissions',
            'ip_address': '192.168.1.100',
            'success': True,
            'level': 'info'
        },
        {
            'user': user,
            'category': 'system',
            'action_type': 'export',
            'description': 'Exported patient data to CSV',
            'ip_address': '192.168.1.100',
            'success': True,
            'level': 'info'
        },
        {
            'user': user,
            'category': 'appointment',
            'action_type': 'create',
            'description': 'Scheduled new appointment',
            'ip_address': '192.168.1.100',
            'success': True,
            'level': 'info'
        },
        {
            'user': user,
            'category': 'inpatient',
            'action_type': 'admit',
            'description': 'Patient admitted to ward',
            'ip_address': '192.168.1.100',
            'success': True,
            'level': 'info'
        }
    ]
    
    # Create activities with different timestamps
    activities_created = 0
    for i, activity_data in enumerate(sample_activities):
        # Vary timestamps over the last 7 days
        days_ago = random.randint(0, 7)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        
        timestamp = timezone.now() - timedelta(
            days=days_ago,
            hours=hours_ago,
            minutes=minutes_ago
        )
        
        activity = ActivityLog.objects.create(
            timestamp=timestamp,
            **activity_data
        )
        activities_created += 1
        print(f"Created activity: {activity.action_type} - {activity.description[:50]}")
    
    print(f"\nTotal activities created: {activities_created}")
    
    # Verify creation
    total_logs = ActivityLog.objects.count()
    print(f"Total activity logs in database: {total_logs}")

if __name__ == '__main__':
    create_sample_activities()
