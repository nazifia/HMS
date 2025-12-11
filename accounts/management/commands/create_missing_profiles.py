#!/usr/bin/env python
"""
Management command to create missing profiles for users.
This command identifies users without profiles and creates them.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import CustomUserProfile


class Command(BaseCommand):
    help = 'Create missing profiles for users who do not have them'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Find users without profiles
        users_without_profiles = []
        for user in User.objects.all():
            try:
                # Try to access the profile
                user.profile
            except CustomUserProfile.DoesNotExist:
                users_without_profiles.append(user)
        
        if not users_without_profiles:
            self.stdout.write(self.style.SUCCESS('All users have profiles. No action needed.'))
            return
        
        self.stdout.write(self.style.WARNING(f'Found {len(users_without_profiles)} users without profiles.'))
        
        # Create profiles for users without them
        created_count = 0
        for user in users_without_profiles:
            try:
                profile = CustomUserProfile.objects.create(user=user)
                self.stdout.write(self.style.SUCCESS(f'Created profile for user {user.username} (ID: {user.id})'))
                created_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to create profile for user {user.username}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} profiles.'))
        
        if created_count < len(users_without_profiles):
            self.stdout.write(self.style.WARNING(f'Failed to create {len(users_without_profiles) - created_count} profiles.'))
