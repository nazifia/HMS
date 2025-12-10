from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.activity_log import ActivityLog
from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'Create sample activity log entries for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of activity log entries to create'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing activity logs before creating new ones'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear_existing = options['clear']

        if clear_existing:
            deleted_count = ActivityLog.objects.count()
            ActivityLog.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f'Cleared {deleted_count} existing activity log entries')
            )

        # Get a user for the logs
        try:
            user = CustomUser.objects.filter(is_superuser=True).first()
            if not user:
                self.stdout.write(
                    self.style.ERROR('No superuser found. Please create a superuser first.')
                )
                return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error getting user: {e}')
            )
            return

        # Sample activity types
        sample_activities = [
            ('login', 'authentication', 'User logged in successfully', 'info', True),
            ('view', 'patient_management', 'Viewed patient list', 'info', True),
            ('create', 'patient_management', 'Created new patient record', 'info', True),
            ('update', 'billing', 'Updated invoice record', 'info', True),
            ('failed_login', 'security', 'Failed login attempt detected', 'warning', False),
            ('permission_denied', 'security', 'Access denied to restricted area', 'warning', False),
            ('export', 'billing', 'Exported billing report', 'info', True),
            ('delete', 'patient_management', 'Deleted patient record', 'warning', True),
            ('search', 'patient_management', 'Searched for patient records', 'info', True),
            ('logout', 'authentication', 'User logged out', 'info', True),
        ]

        created_count = 0
        for i in range(min(count, len(sample_activities))):
            activity = sample_activities[i % len(sample_activities)]
            timestamp = timezone.now() - timedelta(hours=i*2)
            
            try:
                ActivityLog.objects.create(
                    user=user,
                    action_type=activity[0],
                    category=activity[1],
                    description=activity[2],
                    level=activity[3],
                    success=activity[4],
                    timestamp=timestamp,
                    ip_address='127.0.0.1',
                    user_agent='Mozilla/5.0 (Test Management Command)',
                )
                created_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to create activity log: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} activity log entries')
        )
        self.stdout.write(
            self.style.WARNING(f'Total activity log entries: {ActivityLog.objects.count()}')
        )
