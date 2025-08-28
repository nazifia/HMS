#!/usr/bin/env python
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Dispensary

def check_and_create_dispensary():
    """Check if THEATRE-PH exists, create it if not"""
    # Check if THEATRE-PH already exists
    try:
        existing_dispensary = Dispensary.objects.get(name='THEATRE-PH')
        print(f'THEATRE-PH already exists with ID: {existing_dispensary.id}')
        return existing_dispensary
    except Dispensary.DoesNotExist:
        # Create THEATRE-PH dispensary
        theatre_ph = Dispensary.objects.create(
            name='THEATRE-PH',
            location='Theatre Department',
            description='Pharmacy dispensary for theatre procedures',
            is_active=True
        )
        print(f'Created THEATRE-PH with ID: {theatre_ph.id}')
        return theatre_ph

if __name__ == '__main__':
    check_and_create_dispensary()