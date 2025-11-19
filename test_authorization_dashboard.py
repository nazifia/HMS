#!/usr/bin/env python
"""
Test script for NHIA Authorization Dashboard functionality
"""
import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from patients.models import Patient
from nhia.models import NHIAPatient, AuthorizationCode
from core.models import InternalNotification
from consultations.models import Consultation
from accounts.models import CustomUserProfile
from datetime import datetime, timedelta

User = get_user_model()

def create_test_data():
    """Create test data for authorization dashboard"""
    print("Creating test data...")
    
    # Create a desk office user
    user = User.objects.create_user(
        phone_number='9999999991',
        username='desk_office_test',
        email='desk@test.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )
    
    # Create profile (if it doesn't exist)
    profile, created = CustomUserProfile.objects.get_or_create(
        user=user,
        defaults={'role': 'desk_office'}
    )
    
    # Create NHIA patient
    patient = Patient.objects.create(
        first_name='Test',
        last_name='Patient',
        patient_id='TEST001',
        patient_type='nhia',
        phone_number='9876543210'
    )
    
    # Create NHIA info
    NHIAPatient.objects.create(
        patient=patient,
        nhia_reg_number='NHIA12345',
        is_active=True
    )
    
    # Create authorization code
    AuthorizationCode.objects.create(
        code='TEST-20231119-ABC123',
        patient=patient,
        service_type='general',
        amount=10000.00,
        expiry_date=datetime.now().date() + timedelta(days=30),
        status='active',
        generated_by=user,
        notes='Test authorization code'
    )
    
    # Create consultation
    doctor = User.objects.create_user(
        phone_number='9999999992',
        username='doctor_test',
        email='doctor@test.com',
        password='testpass123',
        first_name='Doctor',
        last_name='Test'
    )
    
    # Create profile (if it doesn't exist)
    doctor_profile, doctor_created = CustomUserProfile.objects.get_or_create(
        user=doctor,
        defaults={'role': 'doctor'}
    )
    
    # Create internal notification
    InternalNotification.objects.create(
        title='NHIA Authorization Request: Dental',
        message=f'Authorization request for NHIA Patient: {patient.get_full_name} (ID: {patient.id})\n\nModule: Dental\nRecord ID: DENT001\nRequested By: Dr. {doctor.get_full_name()}',
        sender=doctor,
        user=user,
        is_read=False
    )
    
    print("Test data created successfully")
    return user

def test_dashboard_access(user):
    """Test dashboard access"""
    client = Client()
    client.login(username='desk_office_test', password='testpass123')
    
    # Test dashboard page
    response = client.get(reverse('desk_office:authorization_dashboard'))
    print(f"Dashboard status: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Dashboard page accessible")
        
        # Check for key elements in template
        content = response.content.decode()
        if 'NHIA Authorization Dashboard' in content:
            print("✓ Page title found")
        else:
            print("✗ Page title not found")
            
        if 'patient-search' in content:
            print("✓ Patient search field found")
        else:
            print("✗ Patient search field not found")
            
        if 'medical-module-requests' in content:
            print("✓ Medical module requests section found")
        else:
            print("✗ Medical module requests section not found")
    else:
        print(f"✗ Dashboard access failed: {response.status_code}")
    
    return response

def test_patient_search(user):
    """Test patient search functionality"""
    client = Client()
    client.login(username='desk_office_test', password='testpass123')
    
    # Test patient search
    response = client.post(
        reverse('desk_office:authorization_dashboard'),
        {'search_patients': 'Test', 'search': 'Test', 'csrfmiddlewaretoken': 'test'}
    )
    
    # Note: This won't work without proper CSRF token handling in test
    print(f"Patient search status: {response.status_code}")
    
    # Test with GET parameter (pagination)
    response = client.get(f"{reverse('desk_office:authorization_dashboard')}?search=Test")
    print(f"Patient search GET status: {response.status_code}")
    
    return response

def test_delete_request(user):
    """Test delete medical module request functionality"""
    client = Client()
    client.login(username='desk_office_test', password='testpass123')
    
    # Find a notification to delete
    notification = InternalNotification.objects.filter(
        is_read=False,
        title__icontains='NHIA Authorization Request'
    ).first()
    
    if notification:
        print(f"Found notification to delete: {notification.id}")
        
        # Test DELETE request
        response = client.delete(
            reverse('desk_office:delete_medical_module_request', args=[notification.id])
        )
        print(f"Delete request status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Delete request successful")
        else:
            print(f"✗ Delete request failed: {response.status_code}")
            print(f"Response content: {response.content.decode()}")
    else:
        print("No notification found for deletion test")
    
    return notification

def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("Testing NHIA Authorization Dashboard")
    print("="*60)
    
    # Create test data
    user = create_test_data()
    
    # Run tests
    test_dashboard_access(user)
    test_patient_search(user)
    test_delete_request(user)
    
    print("="*60)
    print("Testing complete")
    print("="*60)

if __name__ == '__main__':
    run_all_tests()
