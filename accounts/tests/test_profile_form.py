from django.test import TestCase
from django.contrib.auth import get_user_model
from ..forms import UserProfileForm
from ..models import CustomUserProfile, Role

User = get_user_model()

class UserProfileFormTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            phone_number='+1234567890',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a role for testing
        self.role = Role.objects.create(name='Test Role')

    def test_clean_contact_phone_number_empty_string(self):
        """Test that empty string for contact_phone_number returns None"""
        form = UserProfileForm(
            data={
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'contact_phone_number': '',  # Empty string
            },
            instance=self.user,
            request_user=self.user
        )
        
        # Form should be valid
        self.assertTrue(form.is_valid())
        
        # Cleaned data should have None for contact_phone_number
        self.assertIsNone(form.cleaned_data.get('contact_phone_number'))

    def test_clean_contact_phone_number_whitespace_only(self):
        """Test that whitespace-only string for contact_phone_number returns None"""
        form = UserProfileForm(
            data={
                'first_name': 'Test',
                'last_name': 'User', 
                'email': 'test@example.com',
                'contact_phone_number': '   ',  # Whitespace only
            },
            instance=self.user,
            request_user=self.user
        )
        
        # Form should be valid
        self.assertTrue(form.is_valid())
        
        # Cleaned data should have None for contact_phone_number
        self.assertIsNone(form.cleaned_data.get('contact_phone_number'))

    def test_clean_contact_phone_number_none(self):
        """Test that None for contact_phone_number returns None"""
        form = UserProfileForm(
            data={
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'contact_phone_number': None,
            },
            instance=self.user,
            request_user=self.user
        )
        
        # Form should be valid
        self.assertTrue(form.is_valid())
        
        # Cleaned data should have None for contact_phone_number
        self.assertIsNone(form.cleaned_data.get('contact_phone_number'))

    def test_clean_contact_phone_number_valid_digits(self):
        """Test that valid digits for contact_phone_number are accepted"""
        form = UserProfileForm(
            data={
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'contact_phone_number': '1234567890',
            },
            instance=self.user,
            request_user=self.user
        )
        
        # Form should be valid
        self.assertTrue(form.is_valid())
        
        # Cleaned data should have the phone number
        self.assertEqual(form.cleaned_data.get('contact_phone_number'), '1234567890')

    def test_clean_contact_phone_number_non_digits(self):
        """Test that non-digit characters in contact_phone_number raise ValidationError"""
        form = UserProfileForm(
            data={
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'contact_phone_number': '123-456-7890',  # Contains dashes
            },
            instance=self.user,
            request_user=self.user
        )
        
        # Form should not be valid
        self.assertFalse(form.is_valid())
        
        # Should have validation error for contact_phone_number
        self.assertIn('contact_phone_number', form.errors)

    def test_save_with_empty_contact_phone_number(self):
        """Test that saving form with empty contact_phone_number works without IntegrityError"""
        form = UserProfileForm(
            data={
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'contact_phone_number': '',  # Empty string
            },
            instance=self.user,
            request_user=self.user
        )
        
        # Form should be valid
        self.assertTrue(form.is_valid())
        
        # Save should work without raising IntegrityError
        try:
            saved_user = form.save()
            self.assertIsNotNone(saved_user)
            
            # Check that profile.phone_number is None
            profile = saved_user.profile
            self.assertIsNone(profile.phone_number)
            
        except Exception as e:
            self.fail(f"Form.save() raised {e} unexpectedly!")

    def test_unique_constraint_with_multiple_null_values(self):
        """Test that multiple users can have NULL contact_phone_number without violating unique constraint"""
        # Create second user
        user2 = User.objects.create_user(
            username='testuser2',
            phone_number='+0987654321',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Edit first user with empty phone number and unique employee_id
        form1 = UserProfileForm(
            data={
                'first_name': 'Test1',
                'last_name': 'User1',
                'email': 'test1@example.com',
                'contact_phone_number': '',
                'employee_id': 'EMP001',  # Unique employee ID
            },
            instance=self.user,
            request_user=self.user
        )
        
        self.assertTrue(form1.is_valid())
        form1.save()
        
        # Edit second user with empty phone number and different unique employee_id
        form2 = UserProfileForm(
            data={
                'first_name': 'Test2',
                'last_name': 'User2',
                'email': 'test2@example.com',
                'contact_phone_number': '',
                'employee_id': 'EMP002',  # Different unique employee ID
            },
            instance=user2,
            request_user=user2
        )
        
        self.assertTrue(form2.is_valid())
        
        # This should not raise IntegrityError
        try:
            form2.save()
        except Exception as e:
            self.fail(f"Second form.save() with empty phone_number raised {e} unexpectedly!")
