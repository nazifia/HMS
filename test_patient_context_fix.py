#!/usr/bin/env python3
"""
Test script to verify patient context clearing functionality.
This tests the fix for the "Error clearing patient context" issue.
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.test.utils import override_settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from patients.models import Patient
from accounts.models import CustomUser

class PatientContextTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        # Create a test patient
        self.patient = Patient.objects.create(
            patient_id='TEST001',
            first_name='John',
            last_name='Doe',
            phone_number='1234567890',
            email='john.doe@example.com',
            is_active=True
        )

        # Create test client
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_clear_patient_context_view(self):
        """Test that the clear_patient_context view works correctly"""
        # First, set a patient context in session
        session = self.client.session
        session['current_patient_id'] = self.patient.id
        session['current_patient_last_accessed'] = 1234567890.0
        session.save()

        # Verify patient context is set
        self.assertIn('current_patient_id', self.client.session)
        self.assertEqual(self.client.session['current_patient_id'], self.patient.id)

        # Test the clear context view
        response = self.client.post('/patients/clear-context/')

        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Patient context cleared successfully')

        # Verify patient context is cleared from session
        self.assertNotIn('current_patient_id', self.client.session)
        self.assertNotIn('current_patient_last_accessed', self.client.session)

    def test_clear_patient_context_invalid_method(self):
        """Test that GET requests are rejected"""
        response = self.client.get('/patients/clear-context/')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid request method')

    def test_clear_patient_context_no_context(self):
        """Test clearing context when no context exists"""
        # Ensure no patient context in session
        session = self.client.session
        if 'current_patient_id' in session:
            del session['current_patient_id']
        if 'current_patient_last_accessed' in session:
            del session['current_patient_last_accessed']
        session.save()

        # Test the clear context view
        response = self.client.post('/patients/clear-context/')

        # Should still succeed even if no context exists
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

if __name__ == '__main__':
    # Run the tests
    print("Testing patient context clearing functionality...")

    # Create test instance
    test_case = PatientContextTestCase()
    test_case.setUp()

    try:
        # Test 1: Clear patient context
        print("1. Testing clear patient context view...")
        test_case.test_clear_patient_context_view()
        print("   ✓ PASSED")

        # Test 2: Invalid method
        print("2. Testing invalid request method...")
        test_case.test_clear_patient_context_invalid_method()
        print("   ✓ PASSED")

        # Test 3: No context
        print("3. Testing clear context when no context exists...")
        test_case.test_clear_patient_context_no_context()
        print("   ✓ PASSED")

        print("\n🎉 All tests passed! Patient context clearing functionality is working correctly.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)