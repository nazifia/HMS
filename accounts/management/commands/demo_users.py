from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Role, CustomUserProfile, Department
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Create demo users with different roles for HMS system demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--assign-existing',
            action='store_true',
            help='Assign roles to existing users',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating demo users for HMS...'))
        
        # Assign roles to existing users if requested
        if options['assign_existing']:
            self.assign_existing_users()
        
        # Create demo users with different roles
        demo_users = [
            {
                'username': 'dr_smith',
                'phone_number': '+1234567890',
                'first_name': 'John',
                'last_name': 'Smith',
                'email': 'dr.smith@hospital.com',
                'role': 'doctor',
                'department': 'Cardiology',
                'employee_id': 'DOC001',
                'specialization': 'Cardiologist'
            },
            {
                'username': 'nurse_jane',
                'phone_number': '+1234567891',
                'first_name': 'Jane',
                'last_name': 'Doe',
                'email': 'jane.doe@hospital.com',
                'role': 'nurse',
                'department': 'Emergency',
                'employee_id': 'NUR001'
            },
            {
                'username': 'receptionist_mary',
                'phone_number': '+1234567892',
                'first_name': 'Mary',
                'last_name': 'Johnson',
                'email': 'mary.johnson@hospital.com',
                'role': 'receptionist',
                'department': 'Front Desk',
                'employee_id': 'REC001'
            },
            {
                'username': 'pharmacist_bob',
                'phone_number': '+1234567893',
                'first_name': 'Bob',
                'last_name': 'Wilson',
                'email': 'bob.wilson@hospital.com',
                'role': 'pharmacist',
                'department': 'Pharmacy',
                'employee_id': 'PHA001'
            },
            {
                'username': 'lab_tech_alice',
                'phone_number': '+1234567894',
                'first_name': 'Alice',
                'last_name': 'Brown',
                'email': 'alice.brown@hospital.com',
                'role': 'lab_technician',
                'department': 'Laboratory',
                'employee_id': 'LAB001'
            },
            {
                'username': 'accountant_david',
                'phone_number': '+1234567895',
                'first_name': 'David',
                'last_name': 'Lee',
                'email': 'david.lee@hospital.com',
                'role': 'accountant',
                'department': 'Finance',
                'employee_id': 'ACC001'
            }
        ]

        with transaction.atomic():
            for user_data in demo_users:
                # Check if user already exists
                if User.objects.filter(username=user_data['username']).exists():
                    self.stdout.write(
                        self.style.WARNING(f'User {user_data["username"]} already exists, skipping...')
                    )
                    continue

                # Create user
                user = User.objects.create_user(
                    username=user_data['username'],
                    phone_number=user_data['phone_number'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    email=user_data['email'],
                    password='demo123'  # Simple password for demo
                )

                # Get or create role
                role, _ = Role.objects.get_or_create(name=user_data['role'])
                user.roles.add(role)

                # Update profile
                profile = user.profile  # This will create the profile if it doesn't exist
                profile.department = user_data['department']
                profile.employee_id = user_data['employee_id']
                if 'specialization' in user_data:
                    profile.specialization = user_data['specialization']
                profile.save()

                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {user.username} with role: {role.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Demo users created successfully!')
        )
        
        # Display summary
        self.display_summary()

    def assign_existing_users(self):
        """Assign roles to existing users"""
        self.stdout.write('Assigning roles to existing users...')
        
        # Assign admin role to superuser
        try:
            superuser = User.objects.get(username='superuser')
            admin_role, _ = Role.objects.get_or_create(name='admin')
            superuser.roles.add(admin_role)
            self.stdout.write(f'Assigned admin role to {superuser.username}')
        except User.DoesNotExist:
            pass

        # Assign admin role to admin user
        try:
            admin_user = User.objects.get(username='admin')
            admin_role, _ = Role.objects.get_or_create(name='admin')
            admin_user.roles.add(admin_role)
            self.stdout.write(f'Assigned admin role to {admin_user.username}')
        except User.DoesNotExist:
            pass

    def display_summary(self):
        """Display a summary of users and their roles"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('HMS USERS AND ROLES SUMMARY')
        self.stdout.write('='*50)
        
        for role in Role.objects.all():
            users = role.customuser_roles.all()
            self.stdout.write(f'\n{role.name.upper()} ({users.count()} users):')
            for user in users:
                profile_info = ""
                if hasattr(user, 'profile') and user.profile:
                    profile_info = f" - {user.profile.department or 'No Dept'}"
                self.stdout.write(f'  • {user.get_full_name()} ({user.username}){profile_info}')
        
        total_users = User.objects.count()
        users_with_roles = User.objects.filter(roles__isnull=False).distinct().count()
        self.stdout.write(f'\nTotal Users: {total_users}')
        self.stdout.write(f'Users with Roles: {users_with_roles}')
        self.stdout.write(f'Users without Roles: {total_users - users_with_roles}')
