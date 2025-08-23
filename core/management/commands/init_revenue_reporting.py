"""
Management command to initialize Revenue Point Breakdown integration
with the existing reporting system.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from core.reporting_integration import initialize_revenue_reporting

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize Revenue Point Breakdown integration with reporting system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of reports and dashboard even if they exist',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating it',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Initializing Revenue Point Breakdown Reporting Integration...')
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
            self._show_what_would_be_created()
            return
        
        try:
            # Check if system user exists
            system_user = self._get_or_create_system_user()
            
            # Initialize reporting integration
            result = initialize_revenue_reporting()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully initialized revenue reporting integration:\n'
                        f'  - Created {result["reports_created"]} reports\n'
                        f'  - Dashboard created: {result["dashboard_created"]}\n'
                    )
                )
                
                self._show_next_steps()
            else:
                raise CommandError(f'Initialization failed: {result["error"]}')
                
        except Exception as e:
            raise CommandError(f'Error during initialization: {str(e)}')
    
    def _get_or_create_system_user(self):
        """Get or create system user for reports"""
        try:
            system_user = User.objects.get(username='system')
        except User.DoesNotExist:
            # Check if we have any superuser to assign as creator
            superuser = User.objects.filter(is_superuser=True).first()
            if superuser:
                self.stdout.write(
                    self.style.WARNING(
                        f'Using existing superuser {superuser.username} as system user'
                    )
                )
                return superuser
            else:
                self.stdout.write(
                    self.style.WARNING(
                        'No system user or superuser found. Creating basic system user.'
                    )
                )
                system_user = User.objects.create_user(
                    username='system',
                    email='system@hms.local',
                    first_name='System',
                    last_name='User',
                    is_staff=True
                )
        
        return system_user
    
    def _show_what_would_be_created(self):
        """Show what would be created in dry run mode"""
        self.stdout.write('\n' + self.style.HTTP_INFO('Reports that would be created:'))
        reports = [
            'Revenue Point Breakdown Summary',
            'Clinical Services Revenue Analysis', 
            'Specialty Departments Performance',
            'Revenue Trends Analysis',
            'Payment Method Distribution',
            'Department Comparison Report'
        ]
        
        for report in reports:
            self.stdout.write(f'  - {report}')
        
        self.stdout.write('\n' + self.style.HTTP_INFO('Dashboard that would be created:'))
        self.stdout.write('  - Revenue Point Analysis Dashboard')
        
        self.stdout.write('\n' + self.style.HTTP_INFO('Widgets that would be created:'))
        widgets = [
            'Total Revenue Summary (Table)',
            'Revenue Distribution (Pie Chart)',
            'Monthly Trends (Line Chart)',
            'Top Departments (Bar Chart)',
            'Clinical Services Breakdown (Table)'
        ]
        
        for widget in widgets:
            self.stdout.write(f'  - {widget}')
    
    def _show_next_steps(self):
        """Show next steps after successful initialization"""
        self.stdout.write('\n' + self.style.HTTP_INFO('Next Steps:'))
        self.stdout.write(
            '1. Access the reporting dashboard at /reporting/dashboard/\n'
            '2. Look for "Revenue Point Analysis Dashboard"\n'
            '3. Access individual reports at /reporting/reports/\n'
            '4. Access dedicated revenue dashboard at /core/revenue/dashboard/\n'
            '5. Configure user permissions for revenue reports if needed\n'
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                '\nRevenue Point Breakdown integration is now ready to use!'
            )
        )