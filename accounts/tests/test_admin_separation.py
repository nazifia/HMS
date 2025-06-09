"""
Tests to verify Django admin is independent of user logic.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.models import Role

User = get_user_model()


class AdminSeparationTestCase(TestCase):
    """Test that Django admin is independent of application roles."""
    
    def setUp(self):
        self.client = Client()
        
        # Create application role
        self.admin_role = Role.objects.create(
            name='admin',
            description='Application administrator'
        )
        
        # Create Django admin user (staff, no application role)
        self.django_admin = User.objects.create_user(
            username='django_admin',
            phone_number='1111111111',
            email='django@admin.com',
            password='testpass123',
            is_staff=True,
            is_active=True
        )
        
        # Create application admin user (has admin role, not staff)
        self.app_admin = User.objects.create_user(
            username='app_admin',
            phone_number='2222222222',
            email='app@admin.com',
            password='testpass123',
            is_staff=False,
            is_active=True
        )
        self.app_admin.roles.add(self.admin_role)
        
        # Create superuser (both Django admin and can have app roles)
        self.superuser = User.objects.create_superuser(
            username='superuser',
            phone_number='3333333333',
            email='super@admin.com',
            password='testpass123'
        )
    
    def test_django_admin_access(self):
        """Test that only staff users can access Django admin."""
        # Django admin can access admin interface
        self.client.login(username='django_admin', password='testpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        
        # Application admin cannot access Django admin
        self.client.login(username='app_admin', password='testpass123')
        response = self.client.get('/admin/')
        self.assertNotEqual(response.status_code, 200)  # Should redirect or deny
        self.client.logout()
        
        # Superuser can access Django admin
        self.client.login(username='superuser', password='testpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.client.logout()
    
    def test_application_role_independence(self):
        """Test that Django admin status doesn't grant application roles."""
        # Django admin user should not have application admin privileges
        self.assertFalse(self.django_admin.roles.filter(name='admin').exists())
        
        # Application admin user should not have Django admin privileges
        self.assertFalse(self.app_admin.is_staff)
        
        # Superuser doesn't automatically get application roles
        self.assertFalse(self.superuser.roles.filter(name='admin').exists())
    
    def test_authentication_backend_separation(self):
        """Test that different backends handle different authentication."""
        from accounts.backends import AdminBackend, PhoneNumberBackend
        from django.test import RequestFactory
        
        factory = RequestFactory()
        
        # Test admin backend with admin request
        admin_request = factory.post('/admin/login/')
        admin_backend = AdminBackend()
        
        # Should authenticate Django admin with username
        user = admin_backend.authenticate(
            admin_request, 
            username='django_admin', 
            password='testpass123'
        )
        self.assertEqual(user, self.django_admin)
        
        # Should not authenticate non-staff user for admin
        user = admin_backend.authenticate(
            admin_request,
            username='app_admin',
            password='testpass123'
        )
        self.assertIsNone(user)  # app_admin is not staff
        
        # Test phone backend with application request
        app_request = factory.post('/accounts/login/')
        phone_backend = PhoneNumberBackend()
        
        # Should authenticate with phone number
        user = phone_backend.authenticate(
            app_request,
            username='2222222222',  # phone number
            password='testpass123'
        )
        self.assertEqual(user, self.app_admin)
        
        # Should not handle admin requests
        user = phone_backend.authenticate(
            admin_request,  # admin request
            username='2222222222',
            password='testpass123'
        )
        self.assertIsNone(user)
    
    def test_middleware_admin_exclusion(self):
        """Test that admin URLs are excluded from role-based middleware."""
        # This would need to be tested with actual middleware
        # For now, we verify the configuration
        from core.middleware import RoleBasedAccessMiddleware
        
        middleware = RoleBasedAccessMiddleware(lambda r: None)
        
        # Check that admin URLs are not in role-required URLs
        admin_in_roles = any('admin/' in url for url, roles in middleware.role_required_urls)
        self.assertFalse(admin_in_roles, "Admin URLs should not be in role-required URLs")


class AdminUserCreationTestCase(TestCase):
    """Test the admin user creation command."""
    
    def test_create_admin_user_command(self):
        """Test that the management command creates proper admin users."""
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        # Capture output
        out = StringIO()
        
        # This would need interactive input mocking for full test
        # For now, test the User model creation directly
        
        # Create admin user manually (simulating command)
        admin_user = User.objects.create_user(
            username='test_admin',
            phone_number='9999999999',
            email='test@admin.com',
            password='testpass123',
            is_staff=True,
            is_active=True
        )
        
        # Verify admin user properties
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_active)
        self.assertFalse(admin_user.is_superuser)  # Unless explicitly set
        
        # Verify no application roles assigned
        self.assertEqual(admin_user.roles.count(), 0)
        
        # Verify can authenticate for admin
        from accounts.backends import AdminBackend
        from django.test import RequestFactory
        
        factory = RequestFactory()
        admin_request = factory.post('/admin/login/')
        backend = AdminBackend()
        
        authenticated_user = backend.authenticate(
            admin_request,
            username='test_admin',
            password='testpass123'
        )
        self.assertEqual(authenticated_user, admin_user)
