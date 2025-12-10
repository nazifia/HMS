from django.core.management.base import BaseCommand
from accounts.models import Department


class Command(BaseCommand):
    help = 'Setup basic hospital departments'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up basic hospital departments...'))
        
        # Basic hospital departments
        departments_data = [
            {
                'name': 'Administration',
                'description': 'Hospital administration and management',
            },
            {
                'name': 'Medical',
                'description': 'Medical and clinical services',
            },
            {
                'name': 'Nursing',
                'description': 'Nursing and patient care services',
            },
            {
                'name': 'Pharmacy',
                'description': 'Pharmacy and medication dispensing',
            },
            {
                'name': 'Laboratory',
                'description': 'Laboratory and diagnostic services',
            },
            {
                'name': 'Radiology',
                'description': 'Medical imaging and radiology',
            },
            {
                'name': 'Billing',
                'description': 'Patient billing and payment processing',
            },
            {
                'name': 'Accounting',
                'description': 'Financial accounting and reporting',
            },
            {
                'name': 'IT',
                'description': 'Information Technology and support services',
            },
            {
                'name': 'Records',
                'description': 'Health records and documentation',
            },
            {
                'name': 'Emergency',
                'description': 'Emergency and trauma care',
            },
            {
                'name': 'Support Services',
                'description': 'Support services and facilities management',
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                name=dept_data['name'],
                defaults={
                    'description': dept_data['description']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created department: {dept_data["name"]}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Department already exists: {dept_data["name"]}')
                )
        
        total_departments = Department.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nDepartment setup complete:\n'
                f'  Created: {created_count} departments\n'
                f'  Updated: {updated_count} departments\n'
                f'  Total departments: {total_departments}'
            )
        )
