#!/usr/bin/env python
import os
import sys

project_dir = os.path.dirname(__file__)
sys.path.insert(0, project_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

import django
django.setup()

from patients.models import Patient
from consultations.models import Referral

try:
    patient = Patient.objects.get(id=42)
    print(f"Patient 42 exists: {patient.get_full_name()}")
    print(f"Patient type: {patient.patient_type}")
    
    # Check referral history
    referrals = Referral.objects.filter(patient=patient)[:5]
    print(f"Referral count: {referrals.count()}")
    
    for referral in referrals:
        print(f"  - Referral {referral.id}: {referral.referral_type}")
        
except Patient.DoesNotExist:
    print("Patient 42 does not exist")
except Exception as e:
    print(f"Error: {e}")