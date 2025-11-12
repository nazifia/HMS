"""
Management command to set up default roles and permissions for HMS
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, ContentType
from accounts.models import Role
from accounts.permissions import ROLE_PERMISSIONS


class Command(BaseCommand):
    help = 'Set up default roles and permissions for HMS'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up default HMS roles and permissions...'))
        
        # Create or update roles
        for role_name, role_data in ROLE_PERMISSIONS.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={'description': role_data['description']}
            )
            
            if created:
                self.stdout.write(f'✓ Created role: {role_name}')
            else:
                role.description = role_data['description']
                role.save()
                self.stdout.write(f'✓ Updated role: {role_name}')
        
        self.stdout.write(self.style.SUCCESS('Default roles setup completed!'))
        
        # Note: In a real implementation, you would also need to map Django permissions
        # to the custom permissions defined above. This is a simplified version.
        
        self.stdout.write(self.style.WARNING(
            'Note: This is a basic role setup. Django permissions should be mapped '
            'to these roles in a production environment.'
        ))
