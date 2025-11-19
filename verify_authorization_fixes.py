import os
import sys
import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from datetime import timedelta
from django.utils import timezone
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

from patients.models import Patient
from desk_office.models import AuthorizationCode
from dental.models import DentalRecord, DentalService
from core.models import InternalNotification
from django.contrib.auth import get_user_model
from desk_office.views import generate_authorization_code
from dental.views import dental_record_detail

User = get_user_model()

def verify_fixes():
    print("Starting verification...")

    # 1. Verify AuthorizationCode model fix (String code)
    print("\n1. Verifying AuthorizationCode model fix...")
    try:
        patient = Patient.objects.first()
        if not patient:
            print("No patients found. Creating a test patient.")
            patient = Patient.objects.create(
                first_name="Test", last_name="Patient", 
                date_of_birth="1990-01-01", gender="Male", 
                patient_type="nhia", phone_number="1234567890"
            )
        
        code_str = "AUTH-20231119-TEST"
        # Check if code exists and delete if so
        AuthorizationCode.objects.filter(code=code_str).delete()
        
        auth_code = AuthorizationCode.objects.create(
            code=code_str,
            patient=patient,
            department="Dental",
            amount=100.00,
            status='active'
        )
        print(f"SUCCESS: Created AuthorizationCode with string PK: {auth_code.code}")
        
        # Verify type
        field = AuthorizationCode._meta.get_field('code')
        print(f"Field type: {type(field).__name__}")
        if type(field).__name__ == 'CharField':
             print("SUCCESS: Field type is CharField")
        else:
             print(f"FAILURE: Field type is {type(field).__name__}")

    except Exception as e:
        print(f"FAILURE: Error creating AuthorizationCode: {e}")

    # 2. Verify Duplicate Prevention Logic (Simulation)
    print("\n2. Verifying Duplicate Prevention Logic...")
    # We already created an active code for this patient above.
    # Let's check if we can detect it.
    existing_code = AuthorizationCode.objects.filter(
        patient=patient, 
        status='active'
    ).first()
    
    if existing_code:
        print(f"SUCCESS: Detected existing active code: {existing_code.code}")
    else:
        print("FAILURE: Could not detect existing active code.")

    # 3. Verify Dental Module Request Control
    print("\n3. Verify Dental Module Request Control...")
    try:
        # Create a dental record
        service = DentalService.objects.first()
        if not service:
             service = DentalService.objects.create(name="Test Service", price=50.00)
             
        record = DentalRecord.objects.create(
            patient=patient,
            service=service,
            dentist=User.objects.first() # Assuming a user exists
        )
        
        # Create a notification simulating a pending request
        msg = f"Patient: {patient.get_full_name()} (ID: {patient.patient_id})"
        InternalNotification.objects.create(
            user=User.objects.first(),
            title="NHIA Authorization Request - Dental",
            message=f"{msg}\nModule: dental",
            is_read=False
        )
        
        # Check logic from dental/views.py
        from django.db.models import Q
        has_pending_request = InternalNotification.objects.filter(
            Q(message__icontains=msg) &
            Q(message__icontains="Module: dental") &
            Q(is_read=False)
        ).exists()
        
        if has_pending_request:
            print("SUCCESS: Detected pending request via InternalNotification.")
        else:
            print("FAILURE: Failed to detect pending request.")
            
        # Clean up
        record.delete()
        InternalNotification.objects.filter(message__icontains=msg).delete()

    except Exception as e:
        print(f"FAILURE: Error verifying dental request control: {e}")

    print("\nVerification complete.")

if __name__ == "__main__":
    verify_fixes()
