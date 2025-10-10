"""
Test the dashboard URL resolution issue in isolation
"""
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import User
from django.urls import reverse

def test_dashboard_access():
    """Test dashboard access with proper authentication"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Get or create a test user
    try:
        user = User.objects.get(username='testuser')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
    
    print(f"Testing dashboard access for user: {user.username}")
    
    # Test with client
    client = Client()
    client.login(username='testuser', password='testpass123')
    
    try:
        response = client.get('/dashboard/')
        print(f"Dashboard access successful: {response.status_code}")
        return True
    except Exception as e:
        print(f"Dashboard access failed: {e}")
        print(f"Error type: {type(e)}")
        return False

if __name__ == "__main__":
    test_dashboard_access()
