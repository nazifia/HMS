#!/usr/bin/env python
"""
Script to check how many users are in the database and test the API endpoint logic
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HMS.settings')
django.setup()

from accounts.models import CustomUser

print("=" * 60)
print("CHECKING USERS IN DATABASE")
print("=" * 60)

users = CustomUser.objects.select_related('profile').all()
print(f"\nTotal users in database: {users.count()}\n")

for i, user in enumerate(users, 1):
    print(f"{i}. Username: {user.username}")
    print(f"   Full Name: {user.get_full_name()}")
    print(f"   Email: {user.email}")
    print(f"   Active: {user.is_active}")
    print(f"   Has Profile: {hasattr(user, 'profile')}")
    
    # Check roles
    try:
        if hasattr(user, 'roles'):
            user_roles = list(user.roles.values_list('name', flat=True))
            print(f"   Roles: {user_roles if user_roles else 'No roles'}")
        else:
            print(f"   Roles: No roles attribute")
    except Exception as e:
        print(f"   Roles: Error - {e}")
    
    print()

print("=" * 60)
print("SIMULATING API ENDPOINT LOGIC")
print("=" * 60)

users_data = []
for user in users:
    try:
        user_roles = list(user.roles.values_list('name', flat=True)) if hasattr(user, 'roles') else []
        
        # Get department data properly
        department = None
        if hasattr(user, 'profile') and hasattr(user.profile, 'department') and user.profile.department:
            department = {
                'id': user.profile.department.id,
                'name': user.profile.department.name
            }
        
        user_dict = {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'get_full_name': user.get_full_name(),
            'email': user.email,
            'phone_number': getattr(user.profile, 'phone_number', '') if hasattr(user, 'profile') else '',
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'roles': user_roles,
            'profile': {
                'department': department,
                'profile_picture': getattr(user.profile, 'profile_picture', None) if hasattr(user, 'profile') else None,
            }
        }
        users_data.append(user_dict)
        print(f"✓ Successfully processed: {user.username}")
    except Exception as e:
        print(f"✗ Error processing {user.username}: {e}")

print(f"\nTotal users successfully processed: {len(users_data)}")
print(f"Expected: {users.count()}")

if len(users_data) < users.count():
    print("\n⚠ WARNING: Some users failed to process!")
else:
    print("\n✓ All users processed successfully!")

