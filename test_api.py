#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from accounts.models import CustomUser
from django.test import Client

# Test database connection
print("Testing database connection...")
try:
    users = CustomUser.objects.all()
    print(f"Found {users.count()} users in database")
    
    for user in users[:3]:
        print(f"User: {user.username}, Email: {user.email}, Roles: {list(user.roles.values_list('name', flat=True))}")
        
except Exception as e:
    print(f"Database error: {e}")

# Test API endpoint
print("\nTesting API endpoint...")
try:
    client = Client()
    
    # Try to access API without authentication first
    response = client.get('/core/api/admin/users/')
    print(f"API response (no auth): {response.status_code}")
    
    # Check if we can get users from actual database
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            print(f"API returned {len(data)} users")
            if len(data) > 0:
                print(f"First user: {data[0]}")
            else:
                print("API returned empty list")
        else:
            print(f"API returned error: {data}")
    else:
        print(f"API error: {response.content}")
        
except Exception as e:
    print(f"API test error: {e}")
