"""
Test script to simulate the API call and see what data is returned
"""
import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'hms.settings'
django.setup()

from accounts.models import CustomUser as User

print("=" * 80)
print("TESTING API ENDPOINT LOGIC")
print("=" * 80)

users = User.objects.select_related('profile').all()
users_data = []
print(f"\nFound {users.count()} users in database\n")

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
        print(f"✓ {user.username:20} - {user.get_full_name():30} - Roles: {user_roles}")
    except Exception as user_error:
        print(f"✗ {user.username:20} - ERROR: {user_error}")
        continue

print(f"\n{'=' * 80}")
print(f"Successfully processed: {len(users_data)} out of {users.count()} users")
print(f"{'=' * 80}\n")

if len(users_data) < users.count():
    print("⚠ WARNING: Some users failed to process!")
    print(f"Missing: {users.count() - len(users_data)} users\n")
else:
    print("✓ All users processed successfully!\n")

# Print summary
print("SUMMARY:")
print(f"- Total users in DB: {users.count()}")
print(f"- Users in API response: {len(users_data)}")
print(f"- Users with roles: {sum(1 for u in users_data if u['roles'])}")
print(f"- Users without roles: {sum(1 for u in users_data if not u['roles'])}")

