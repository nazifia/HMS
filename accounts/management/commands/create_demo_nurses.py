from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from accounts.models import Department, CustomUserProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates demo nurse users for testing the nursing note functionality'

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
        
        self.stdout.write('Creating demo nurse users...')
        
        try:
            with transaction.atomic():
                # Ensure Nursing department exists
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
                
                # Demo nurses to create
                demo_nurses = [
                    {
                        'username': 'nurse1',
                        'phone_number': '08012345671',
                        'first_name': 'Sarah',
                        'last_name': 'Johnson',
                        'email': 'sarah.johnson@hospital.com',
                        'employee_id': 'NUR001'
                    },
                    {
                        'username': 'nurse2',
                        'phone_number': '08012345672',
                        'first_name': 'Mary',
                        'last_name': 'Williams',
                        'email': 'mary.williams@hospital.com',
                        'employee_id': 'NUR002'
                    },
                    {
                        'username': 'nurse3',
                        'phone_number': '08012345673',
                        'first_name': 'Jennifer',
                        'last_name': 'Brown',
                        'email': 'jennifer.brown@hospital.com',
                        'employee_id': 'NUR003'
                    }
                ]
                
                created_count = 0
                for nurse_data in demo_nurses:
                    # Check if user already exists
                    if User.objects.filter(
                        phone_number=nurse_data['phone_number']
                    ).exists():
                        self.stdout.write(
                            f'User with phone {nurse_data["phone_number"]} already exists'
                        )
                        continue
                    
                    if User.objects.filter(
                        username=nurse_data['username']
                    ).exists():
                        self.stdout.write(
                            f'User with username {nurse_data["username"]} already exists'
                        )
                        continue
                    
                    if not dry_run:
                        # Create the user
                        user = User.objects.create_user(
                            username=nurse_data['username'],
                            phone_number=nurse_data['phone_number'],
                            first_name=nurse_data['first_name'],
                            last_name=nurse_data['last_name'],
                            email=nurse_data['email'],
                            password='nurse123',  # Default password
                            is_active=True
                        )
                        
                        # Check if employee_id already exists
                        employee_id = nurse_data['employee_id']
                        if CustomUserProfile.objects.filter(employee_id=employee_id).exists():
                            # Generate a unique employee_id
                            counter = 1
                            base_id = employee_id
                            while CustomUserProfile.objects.filter(employee_id=employee_id).exists():
                                employee_id = f"{base_id}_{counter}"
                                counter += 1

                        # Create or update the profile
                        profile, profile_created = CustomUserProfile.objects.get_or_create(
                            user=user,
                            defaults={
                                'department': nursing_dept,
                                'role': 'nurse',
                                'employee_id': employee_id,
                                'qualification': 'Registered Nurse',
                                'phone_number': nurse_data['phone_number']
                            }
                        )

                        if not profile_created:
                            # Update existing profile
                            profile.department = nursing_dept
                            profile.role = 'nurse'
                            if not profile.employee_id:
                                profile.employee_id = employee_id
                            profile.qualification = 'Registered Nurse'
                            profile.save()
                        
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created nurse: {user.get_full_name()} '
                                f'(username: {user.username}, phone: {user.phone_number})'
                            )
                        )
                    else:
                        created_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'Would create nurse: {nurse_data["first_name"]} {nurse_data["last_name"]} '
                                f'(username: {nurse_data["username"]}, phone: {nurse_data["phone_number"]})'
                            )
                        )
                
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f'Would create {created_count} demo nurses')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {created_count} demo nurses')
                    )
                
                # Show current nursing staff count
                current_nurses = CustomUserProfile.objects.filter(
                    department=nursing_dept,
                    role='nurse'
                ).count()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Nursing department now has {current_nurses} nurses'
                    )
                )
                
                if not dry_run and created_count > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            'Default password for all demo nurses is: nurse123'
                        )
                    )
                
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error creating demo nurses: {e}')
            )
            raise
