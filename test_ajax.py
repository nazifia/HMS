#!/usr/bin/env python
import os
import sys
import django
import json
from django.test import Client
from django.contrib.auth.models import User

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription, PrescriptionItem, Medication, Dispensary, MedicationInventory

def test_ajax_endpoint():
    client = Client()
    
    # Create test user and login
    user = User.objects.create_user('testuser', 'test@test.com', 'testpass')
    client.login(username='testuser', password='testpass')
    
    # Get or create test data
    try:
        prescription = Prescription.objects.first()
        dispensary = Dispensary.objects.first()
        
        if not prescription or not dispensary:
            print("No test data found. Please ensure you have prescriptions and dispensaries in the database.")
            return
        
        # Test the AJAX endpoint
        url = f'/pharmacy/prescriptions/{prescription.id}/stock-quantities/'
        data = {'dispensary_id': str(dispensary.id)}
        
        response = client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.content.decode()}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"Success: {response_data.get('success')}")
            if response_data.get('success'):
                print(f"Stock quantities: {response_data.get('stock_quantities')}")
            else:
                print(f"Error: {response_data.get('error')}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_ajax_endpoint()