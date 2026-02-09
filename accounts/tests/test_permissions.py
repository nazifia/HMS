"""
Test the new permission system
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import Role
from accounts.permissions import (
    user_has_permission, user_in_role, get_user_roles,
    permission_required, role_required
)
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


class PermissionSystemTest(TestCase):
    
    def setUp(self):
        # Create test roles
        self.admin_role = Role.objects.create(
            name='admin',
            description='System Administrator'
        )
        self.doctor_role = Role.objects.create(
            name='doctor',
            description='Medical Doctor'
        )
        self.nurse_role = Role.objects.create(
            name='nurse',
            description='Registered Nurse'
        )
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin',
            phone_number='+2348012345678',
            password='testpass123'
        )
        self.admin_user.is_superuser = True
        self.admin_user.save()
        
        self.doctor_user = User.objects.create_user(
            username='doctor',
            phone_number='+2348012345679',
            password='testpass123'
        )
        self.doctor_user.roles.add(self.doctor_role)
        
        self.nurse_user = User.objects.create_user(
            username='nurse',
            phone_number='+2348012345680',
            password='testpass123'
        )
        self.nurse_user.roles.add(self.nurse_role)
        
        self.regular_user = User.objects.create_user(
            username='regular',
            phone_number='+2348012345681',
            password='testpass123'
        )
    
    def test_superuser_has_all_permissions(self):
        """Test that superusers have all permissions"""
        self.assertTrue(user_has_permission(self.admin_user, 'patients.view'))
        self.assertTrue(user_has_permission(self.admin_user, 'medical.edit'))
        self.assertTrue(user_has_permission(self.admin_user, 'billing.delete'))
    
    def test_role_based_permissions(self):
        """Test role-based permission checking"""
        # Doctor should have medical permissions
        self.assertTrue(user_in_role(self.doctor_user, 'doctor'))
        self.assertFalse(user_in_role(self.doctor_user, 'nurse'))
        
        # Nurse should have nursing permissions
        self.assertTrue(user_in_role(self.nurse_user, 'nurse'))
        self.assertFalse(user_in_role(self.nurse_user, 'doctor'))
    
    def test_user_without_roles(self):
        """Test user with no roles"""
        self.assertFalse(user_in_role(self.regular_user, 'admin'))
        self.assertFalse(user_in_role(self.regular_user, 'doctor'))
        self.assertFalse(user_in_role(self.regular_user, 'nurse'))
    
    def test_get_user_roles(self):
        """Test getting user roles"""
        admin_roles = get_user_roles(self.admin_user)
        self.assertIn('admin', admin_roles)
        
        doctor_roles = get_user_roles(self.doctor_user)
        self.assertIn('doctor', doctor_roles)
        
        regular_roles = get_user_roles(self.regular_user)
        self.assertEqual(len(regular_roles), 0)
    
    def test_anonymous_user_permissions(self):
        """Test that anonymous users have no permissions"""
        anonymous = AnonymousUser()
        self.assertFalse(user_has_permission(anonymous, 'patients.view'))
        self.assertFalse(user_in_role(anonymous, 'admin'))
        self.assertEqual(len(get_user_roles(anonymous)), 0)
    
    def test_multiple_roles(self):
        """Test user with multiple roles"""
        self.doctor_user.roles.add(self.nurse_role)
        
        self.assertTrue(user_in_role(self.doctor_user, 'doctor'))
        self.assertTrue(user_in_role(self.doctor_user, 'nurse'))
        self.assertTrue(user_in_role(self.doctor_user, ['doctor', 'nurse']))
        
        roles = get_user_roles(self.doctor_user)
        self.assertIn('doctor', roles)
        self.assertIn('nurse', roles)


class PermissionDecoratorTest(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            phone_number='+2348012345682',
            password='testpass123'
        )
    
    def test_permission_required_decorator(self):
        """Test the permission_required decorator"""
        from django.http import HttpResponse
        from django.test import RequestFactory

        @permission_required('test.permission', raise_exception=True)
        def test_view(request):
            return HttpResponse('Success')

        request = self.factory.get('/')
        request.user = self.user

        # Should return 403 response (not raise exception)
        response = test_view(request)
        self.assertEqual(response.status_code, 403)
    
    def test_role_required_decorator(self):
        """Test the role_required decorator"""
        from django.http import HttpResponse

        @role_required('admin', raise_exception=True)
        def test_view(request):
            return HttpResponse('Success')

        request = self.factory.get('/')
        request.user = self.user

        # Should return 403 response (not raise exception)
        response = test_view(request)
        self.assertEqual(response.status_code, 403)


class TemplateTagTest(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='templateuser',
            phone_number='+2348012345683',
            password='testpass123'
        )
        self.admin_role = Role.objects.create(name='admin')
        self.user.roles.add(self.admin_role)
    
    def test_has_permission_template_tag(self):
        """Test the has_permission template tag"""
        from accounts.templatetags.permission_tags import has_permission
        
        # Test with admin role
        self.assertTrue(has_permission(self.user, 'patients.view'))
        self.assertTrue(has_permission(self.user, 'medical.edit'))
        
        # Test with regular user
        regular_user = User.objects.create_user(
            username='regularuser',
            phone_number='+2348012345684',
            password='testpass123'
        )
        self.assertFalse(has_permission(regular_user, 'patients.view'))
    
    def test_in_role_template_tag(self):
        """Test the in_role template tag"""
        from accounts.templatetags.permission_tags import in_role
        
        self.assertTrue(in_role(self.user, 'admin'))
        self.assertFalse(in_role(self.user, 'doctor'))
        self.assertTrue(in_role(self.user, ['admin', 'doctor']))
    
    def test_get_user_roles_list_template_tag(self):
        """Test the get_user_roles_list template tag"""
        from accounts.templatetags.permission_tags import get_user_roles_list
        
        roles = get_user_roles_list(self.user)
        self.assertIn('admin', roles)
        self.assertEqual(len(roles), 1)
        
        # Test with user having no roles
        regular_user = User.objects.create_user(
            username='noroles',
            phone_number='+2348012345685',
            password='testpass123'
        )
        roles = get_user_roles_list(regular_user)
        self.assertEqual(len(roles), 0)
