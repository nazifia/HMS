from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile

class Command(BaseCommand):
    help = 'Update the superuser with a phone number for authentication'

    def add_arguments(self, parser):
        parser.add_argument('phone_number', type=str, help='Phone number to assign to the superuser')
        parser.add_argument('--username', type=str, help='Username of the superuser to update (default: first superuser)')

    def handle(self, *args, **options):
        phone_number = options['phone_number']
        username = options.get('username')

        # Validate phone number format (basic validation)
        if not phone_number or len(phone_number) < 10:
            self.stdout.write(self.style.ERROR('Please provide a valid phone number (at least 10 digits)'))
            return

        # Get the superuser to update
        if username:
            try:
                superuser = User.objects.get(username=username, is_superuser=True)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Superuser with username "{username}" not found'))
                return
        else:
            # Get the first superuser
            superusers = User.objects.filter(is_superuser=True)
            if not superusers.exists():
                self.stdout.write(self.style.ERROR('No superuser found in the database'))
                return
            superuser = superusers.first()

        # Check if the phone number is already in use
        if UserProfile.objects.filter(phone_number=phone_number).exclude(user=superuser).exists():
            self.stdout.write(self.style.ERROR(f'Phone number "{phone_number}" is already in use by another user'))
            return

        # Update the superuser's profile
        profile = superuser.profile
        old_phone = profile.phone_number or 'None'
        profile.phone_number = phone_number
        
        # If the role is not set, set it to 'admin'
        if not profile.role:
            profile.role = 'admin'
            
        profile.save()

        self.stdout.write(self.style.SUCCESS(
            f'Successfully updated superuser "{superuser.username}" phone number from "{old_phone}" to "{phone_number}"'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'You can now log in using the phone number "{phone_number}" and your password'
        ))
