"""
Celery configuration for HMS project.
This module configures Celery for handling asynchronous tasks and scheduled jobs.
"""

import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

app = Celery('hms')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Configuration for scheduled tasks
app.conf.beat_schedule = {
    'daily-admission-charges': {
        'task': 'inpatient.tasks.process_daily_admission_charges',
        'schedule': crontab(hour=0, minute=0),  # Run at 12:00 AM daily
    },
    'session-cleanup': {
        'task': 'core.tasks.cleanup_expired_sessions',
        'schedule': crontab(minute='*/60'),  # Run every hour
    },
    'wallet-balance-notifications': {
        'task': 'inpatient.tasks.send_low_balance_notifications',
        'schedule': crontab(minute='*/120'),  # Run every 2 hours
    },
    'old-session-cleanup': {
        'task': 'core.tasks.cleanup_old_session_data',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2:00 AM
    },
    'session-monitoring': {
        'task': 'core.tasks.monitor_active_sessions',
        'schedule': crontab(minute='*/30'),  # Run every 30 minutes
    },
}

app.conf.timezone = 'UTC'


@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery functionality"""
    print(f'Request: {self.request!r}')
