"""Get test user credentials from database"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from accounts.models import CustomUser

print("\n" + "="*80)
print("AVAILABLE TEST USERS")
print("="*80 + "\n")

users = CustomUser.objects.filter(is_active=True)
for user in users[:10]:
    print(f"Username: {user.username}")
    print(f"Phone Number: {user.phone_number}")
    print(f"Email: {user.email}")
    print(f"First Name: {user.first_name}")
    print(f"Is Staff: {user.is_staff}")
    print(f"Is Superuser: {user.is_superuser}")
    print("-" * 80)

print("\n" + "="*80)
print("TEST USER CREDENTIALS FOR PLAYWRIGHT")
print("="*80)
print("""
For authentication, use:
  - Phone Number: (from the list above)
  - Password: (default is 'password123' for most users)

Example:
  Phone Number: +2348012345678
  Password: password123
""")
print("="*80 + "\n")
