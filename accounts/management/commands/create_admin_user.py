"""
Management command to create Django admin users independently of application roles.
This separates admin user creation from regular user management.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
import getpass

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a Django admin user independent of application roles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Admin username',
        )
        parser.add_argument(
            '--phone',
            type=str,
            help='Admin phone number',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Admin email address',
        )
        parser.add_argument(
            '--superuser',
            action='store_true',
            help='Create as superuser',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        phone = options.get('phone')
        email = options.get('email')
        is_superuser = options.get('superuser', False)

        # Interactive input if not provided
        if not username:
            username = input('Admin username: ')
        
        if not phone:
            phone = input('Admin phone number: ')
        
        if not email:
            email = input('Admin email: ')

        # Validate inputs
        if not username or not phone or not email:
            raise CommandError('Username, phone, and email are required.')

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User with username "{username}" already exists.')
        
        if User.objects.filter(phone_number=phone).exists():
            raise CommandError(f'User with phone number "{phone}" already exists.')

        # Get password
        password = getpass.getpass('Password: ')
        password_confirm = getpass.getpass('Password (again): ')
        
        if password != password_confirm:
            raise CommandError('Passwords do not match.')

        try:
            with transaction.atomic():
                # Create admin user
                user = User.objects.create_user(
                    username=username,
                    phone_number=phone,
                    email=email,
                    password=password,
                    is_staff=True,
                    is_active=True
                )
                
                if is_superuser:
                    user.is_superuser = True
                    user.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created admin user "{username}" '
                        f'{"(superuser)" if is_superuser else "(staff)"}'
                    )
                )
                
                self.stdout.write(
                    self.style.WARNING(
                        'Note: This admin user is independent of application roles. '
                        'They can access Django admin but not application features '
                        'unless assigned an application role separately.'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error creating admin user: {e}')
