from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Department, CustomUser, CustomUserProfile

class Command(BaseCommand):
    help = 'Creates the Nursing department and assigns nurses to it'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in dry-run mode. No changes will be made.'))
        
        self.stdout.write('Creating Nursing department and assigning nurses...')
        
        try:
            with transaction.atomic():
                # Create or get the Nursing department
                nursing_dept, created = Department.objects.get_or_create(
                    name='Nursing',
                    defaults={
                        'description': 'Department for nursing staff and patient care'
                    }
                )
                
                if created:
                    if dry_run:
                        self.stdout.write(self.style.WARNING('Would create Nursing department'))
                    else:
                        self.stdout.write(self.style.SUCCESS('Created Nursing department'))
                else:
                    self.stdout.write('Nursing department already exists')
                
                # Find users with nurse role but no department or wrong department
                nurse_profiles = CustomUserProfile.objects.filter(
                    role='nurse'
                ).exclude(
                    department=nursing_dept
                )
                
                nurses_updated = 0
                for profile in nurse_profiles:
                    if not dry_run:
                        profile.department = nursing_dept
                        profile.save()
                    nurses_updated += 1
                    
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Would assign {profile.user.get_full_name()} to Nursing department'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Assigned {profile.user.get_full_name()} to Nursing department'
                            )
                        )
                
                # Also check for users who might have 'Nursing' in their profile but not the FK
                nursing_string_profiles = CustomUserProfile.objects.filter(
                    department__isnull=True
                ).filter(
                    user__first_name__icontains='nurse'
                ) | CustomUserProfile.objects.filter(
                    department__isnull=True
                ).filter(
                    user__last_name__icontains='nurse'
                )
                
                for profile in nursing_string_profiles:
                    if not dry_run:
                        profile.department = nursing_dept
                        profile.role = 'nurse'  # Ensure role is set
                        profile.save()
                    nurses_updated += 1
                    
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Would assign {profile.user.get_full_name()} to Nursing department (detected by name)'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Assigned {profile.user.get_full_name()} to Nursing department (detected by name)'
                            )
                        )
                
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f'Would update {nurses_updated} nurse profiles')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated {nurses_updated} nurse profiles')
                    )
                
                # Show current nursing department staff count
                current_nurses = CustomUserProfile.objects.filter(
                    department=nursing_dept
                ).count()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Nursing department now has {current_nurses} staff members'
                    )
                )
                
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error creating nursing department: {e}')
            )
            raise
