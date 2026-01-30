from django.core.management.base import BaseCommand
from accounts.models import Department

class Command(BaseCommand):
    help = 'Create missing specialty departments for HMS modules'

    def handle(self, *args, **kwargs):
        # List of departments to create
        departments_to_create = [
            'ANC',
            'Labor', 
            'SCBU',
            'ICU',
            'Family Planning',
            'Dental',
            'ENT',
            'Ophthalmic',
            'Oncology'
        ]
        
        created_count = 0
        existing_count = 0
        
        for dept_name in departments_to_create:
            dept, created = Department.objects.get_or_create(
                name=dept_name,
                defaults={
                    'description': f'{dept_name} Department'
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created department: {dept_name}')
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'Department already exists: {dept_name}')
                )
                existing_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: {created_count} departments created, {existing_count} already existed'
            )
        )
