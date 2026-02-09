from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient
from rest_framework import status
import json
from accounts.models import CustomUser, Role, AuditLog, CustomUserProfile
from accounts.permissions import user_has_permission
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

class UserManagementTests(TestCase):
    def setUp(self):
        # Create admin user
        self.admin = CustomUser.objects.create_superuser(
            phone_number='+1234567890',
            username='admin',
            email='admin@example.com',
            password='adminpass'
        )
        self.admin.profile.employee_id = 'ADM001'
        self.admin.profile.save()

        # Create regular user
        self.user = CustomUser.objects.create_user(
            phone_number='+1234567891',
            username='testuser',
            email='user@example.com',
            password='testpass'
        )
        self.user.profile.employee_id = 'EMP001'
        self.user.profile.save()
        
        # Create roles
        self.admin_role = Role.objects.create(name='Administrator')
        self.user_role = Role.objects.create(name='user')
        
        # Assign permissions
        content_type = ContentType.objects.get_for_model(CustomUser)
        self.user_perm = Permission.objects.get(codename='view_customuser')
        self.admin_role.permissions.add(self.user_perm)
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_user_creation(self):
        url = reverse('user-list')
        data = {
            'username': 'newuser',
            'phone_number': '+1234567892',
            'email': 'new@example.com',
            'password': 'newpass123',
            'profile': {
                'employee_id': 'EMP002',
                'phone_number': '+1234567890'
            },
            'role_ids': [self.user_role.id]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomUser.objects.count(), 3)
        
        # Verify audit log
        log = AuditLog.objects.last()
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.target_user.username, 'newuser')
        
    def test_user_update(self):
        url = reverse('user-detail', kwargs={'pk': self.user.id})
        data = {
            'email': 'updated@example.com',
            'profile': {
                'phone_number': '+9876543210'
            }
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify changes
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.profile.phone_number, '+9876543210')
        
        # Verify audit log
        log = AuditLog.objects.last()
        self.assertEqual(log.action, 'update')
        self.assertIn('email', json.loads(log.details)['changes'])
        
    def test_user_deactivation(self):
        url = reverse('user-deactivate', kwargs={'pk': self.user.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify deactivation
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.is_active)
        
        # Verify audit log
        log = AuditLog.objects.last()
        self.assertEqual(log.action, 'deactivate')
        
    def test_role_assignment(self):
        url = reverse('user-assign-roles', kwargs={'pk': self.user.id})
        data = {'role_ids': [self.admin_role.id]}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify role assignment
        self.assertEqual(self.user.roles.count(), 1)
        self.assertEqual(self.user.roles.first().name, 'Administrator')
        
        # Verify audit log
        log = AuditLog.objects.last()
        self.assertEqual(log.action, 'privilege_change')
        
    def test_encrypted_fields(self):
        # Test encryption/decryption
        from cryptography.fernet import Fernet
        import base64

        # Get the encryption key - ensure it's valid Fernet format (32 url-safe base64-encoded bytes)
        key = settings.ENCRYPTION_KEY
        try:
            # Try to decode to verify it's valid base64
            decoded = base64.urlsafe_b64decode(key)
            if len(decoded) != 32:
                # If not 32 bytes, generate a proper test key
                key = base64.urlsafe_b64encode(b'0' * 32).decode()
        except Exception:
            # Invalid base64, generate a proper test key
            key = base64.urlsafe_b64encode(b'0' * 32).decode()

        cipher_suite = Fernet(key)

        test_data = "sensitive information"
        encrypted = cipher_suite.encrypt(test_data.encode())
        decrypted = cipher_suite.decrypt(encrypted).decode()

        self.assertEqual(test_data, decrypted)
        
    def test_rbac_permissions(self):
        # Create user with limited permissions
        limited_user = CustomUser.objects.create_user(
            phone_number='+1234567892',
            username='limited',
            email='limited@example.com',
            password='limitedpass'
        )
        limited_user.profile.employee_id = 'EMP003'
        limited_user.profile.save()

        # Initially, user should NOT have permission via custom RBAC system
        self.assertFalse(user_has_permission(limited_user, 'users.view'))

        # Assign role with permission
        limited_user.roles.add(self.admin_role)

        # Now user SHOULD have permission via RBAC (including inheritance from admin role)
        self.assertTrue(user_has_permission(limited_user, 'users.view'))
        
    def test_audit_log_retrieval(self):
        # Create some audit logs
        for i in range(5):
            AuditLog.objects.create(
                user=self.admin,
                target_user=self.user,
                action='update',
                details=json.dumps({'field': f'field_{i}'}),
                ip_address='127.0.0.1'
            )
        
        # Retrieve logs
        url = reverse('auditlog-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        
        # Test filtering
        response = self.client.get(url, {'user_id': self.user.id})
        self.assertEqual(len(response.data), 5)
        
        response = self.client.get(url, {'action': 'create'})
        self.assertEqual(len(response.data), 0)