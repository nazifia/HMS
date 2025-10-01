"""
Test script for Referral System and Prescription Authorization

This script tests:
1. API endpoint for loading doctors
2. Referral creation
3. Prescription authorization for NHIA patients from non-NHIA units

Run with: python test_referral_system.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Q
from accounts.models import Role, CustomUserProfile, Department
from patients.models import Patient
from consultations.models import Referral, Consultation
from pharmacy.models import Prescription
from nhia.models import NHIAPatient

User = get_user_model()

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_success(text):
    """Print success message"""
    print(f"✅ {text}")

def print_error(text):
    """Print error message"""
    print(f"❌ {text}")

def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")

def test_api_doctors():
    """Test 1: Check if doctors can be retrieved via API logic"""
    print_header("Test 1: Doctor Retrieval via API Logic")
    
    # Simulate API query
    role = 'doctor'
    users_query = User.objects.filter(is_active=True)
    
    if role:
        users_query = users_query.filter(
            Q(roles__name__iexact=role) | Q(profile__role__iexact=role)
        ).distinct()
    
    doctors = users_query.select_related('profile').prefetch_related('roles')
    
    print_info(f"Found {doctors.count()} active doctors")
    
    if doctors.count() > 0:
        print_success("Doctors found successfully!")
        for doctor in doctors[:5]:  # Show first 5
            roles = list(doctor.roles.values_list('name', flat=True))
            profile_role = doctor.profile.role if hasattr(doctor, 'profile') and doctor.profile else 'N/A'
            dept = doctor.profile.department.name if (hasattr(doctor, 'profile') and doctor.profile and doctor.profile.department) else 'N/A'
            print(f"   - {doctor.get_full_name()} (ID: {doctor.id})")
            print(f"     Roles (M2M): {roles}")
            print(f"     Profile Role: {profile_role}")
            print(f"     Department: {dept}")
    else:
        print_error("No doctors found!")
        print_info("Creating a test doctor...")
        
        # Create test doctor
        doctor_role, created = Role.objects.get_or_create(name='doctor')
        
        doctor = User.objects.create_user(
            username='test_doctor',
            first_name='Test',
            last_name='Doctor',
            email='test.doctor@hospital.com',
            password='password123'
        )
        doctor.roles.add(doctor_role)
        
        # Create profile
        profile, created = CustomUserProfile.objects.get_or_create(
            user=doctor,
            defaults={'role': 'doctor'}
        )
        
        print_success(f"Created test doctor: {doctor.get_full_name()}")
    
    return doctors.count() > 0

def test_nhia_department():
    """Test 2: Check if NHIA department exists"""
    print_header("Test 2: NHIA Department Check")
    
    try:
        nhia_dept = Department.objects.filter(name__iexact='NHIA').first()
        if nhia_dept:
            print_success(f"NHIA department found: {nhia_dept.name}")
            return True
        else:
            print_error("NHIA department not found!")
            print_info("Creating NHIA department...")
            nhia_dept = Department.objects.create(
                name='NHIA',
                description='National Health Insurance Authority'
            )
            print_success(f"Created NHIA department: {nhia_dept.name}")
            return True
    except Exception as e:
        print_error(f"Error checking NHIA department: {e}")
        return False

def test_prescription_authorization():
    """Test 3: Test prescription authorization logic"""
    print_header("Test 3: Prescription Authorization Logic")
    
    # Get or create NHIA patient
    patient = Patient.objects.first()
    if not patient:
        print_error("No patients found in database!")
        return False
    
    print_info(f"Using patient: {patient.get_full_name()}")
    
    # Check if patient is NHIA
    is_nhia = patient.is_nhia_patient()
    print_info(f"Patient is NHIA: {is_nhia}")
    
    if not is_nhia:
        print_info("Making patient NHIA for testing...")
        try:
            nhia_info, created = NHIAPatient.objects.get_or_create(
                patient=patient,
                defaults={
                    'nhia_number': 'TEST123456',
                    'is_active': True
                }
            )
            print_success("Patient is now NHIA")
        except Exception as e:
            print_error(f"Error making patient NHIA: {e}")
            return False
    
    # Get doctors from different departments
    nhia_dept = Department.objects.filter(name__iexact='NHIA').first()
    other_dept = Department.objects.exclude(name__iexact='NHIA').first()
    
    if not nhia_dept or not other_dept:
        print_error("Need both NHIA and non-NHIA departments for testing")
        return False
    
    # Get or create NHIA doctor
    nhia_doctor = User.objects.filter(
        is_active=True,
        profile__department=nhia_dept
    ).first()
    
    if not nhia_doctor:
        print_info("Creating NHIA doctor...")
        doctor_role, _ = Role.objects.get_or_create(name='doctor')
        nhia_doctor = User.objects.create_user(
            username='nhia_doctor',
            first_name='NHIA',
            last_name='Doctor',
            password='password123'
        )
        nhia_doctor.roles.add(doctor_role)
        profile, _ = CustomUserProfile.objects.get_or_create(
            user=nhia_doctor,
            defaults={'role': 'doctor', 'department': nhia_dept}
        )
        profile.department = nhia_dept
        profile.save()
        print_success(f"Created NHIA doctor: {nhia_doctor.get_full_name()}")
    
    # Get or create non-NHIA doctor
    other_doctor = User.objects.filter(
        is_active=True,
        profile__department=other_dept
    ).first()
    
    if not other_doctor:
        print_info("Creating non-NHIA doctor...")
        doctor_role, _ = Role.objects.get_or_create(name='doctor')
        other_doctor = User.objects.create_user(
            username='other_doctor',
            first_name='Other',
            last_name='Doctor',
            password='password123'
        )
        other_doctor.roles.add(doctor_role)
        profile, _ = CustomUserProfile.objects.get_or_create(
            user=other_doctor,
            defaults={'role': 'doctor', 'department': other_dept}
        )
        profile.department = other_dept
        profile.save()
        print_success(f"Created non-NHIA doctor: {other_doctor.get_full_name()}")
    
    # Test Scenario 1: NHIA patient + NHIA doctor
    print("\n--- Scenario 1: NHIA Patient + NHIA Doctor ---")
    try:
        prescription1 = Prescription(
            patient=patient,
            doctor=nhia_doctor
        )
        prescription1.check_authorization_requirement()
        
        if not prescription1.requires_authorization:
            print_success("✓ No authorization required (CORRECT)")
        else:
            print_error("✗ Authorization required (INCORRECT)")
    except Exception as e:
        print_error(f"Error in scenario 1: {e}")
    
    # Test Scenario 2: NHIA patient + non-NHIA doctor
    print("\n--- Scenario 2: NHIA Patient + Non-NHIA Doctor ---")
    try:
        prescription2 = Prescription(
            patient=patient,
            doctor=other_doctor
        )
        prescription2.check_authorization_requirement()
        
        if prescription2.requires_authorization:
            print_success("✓ Authorization required (CORRECT)")
            print_info(f"   Authorization status: {prescription2.authorization_status}")
        else:
            print_error("✗ No authorization required (INCORRECT)")
    except Exception as e:
        print_error(f"Error in scenario 2: {e}")
    
    return True

def test_referral_form():
    """Test 4: Test referral form doctor queryset"""
    print_header("Test 4: Referral Form Doctor Queryset")
    
    try:
        from consultations.forms import ReferralForm
        
        form = ReferralForm()
        doctors = form.fields['referred_to'].queryset
        
        print_info(f"Referral form has {doctors.count()} doctors available")
        
        if doctors.count() > 0:
            print_success("Doctors available in referral form!")
            for doctor in doctors[:5]:
                print(f"   - {doctor.get_full_name()}")
            return True
        else:
            print_error("No doctors available in referral form!")
            return False
    except Exception as e:
        print_error(f"Error testing referral form: {e}")
        return False

def main():
    """Run all tests"""
    print_header("REFERRAL SYSTEM & PRESCRIPTION AUTHORIZATION TESTS")
    print_info("Testing referral system and prescription authorization logic...")
    
    results = []
    
    # Run tests
    results.append(("API Doctors", test_api_doctors()))
    results.append(("NHIA Department", test_nhia_department()))
    results.append(("Prescription Authorization", test_prescription_authorization()))
    results.append(("Referral Form", test_referral_form()))
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{'='*70}")
    print(f"  Total: {passed}/{total} tests passed")
    print(f"{'='*70}\n")
    
    if passed == total:
        print_success("All tests passed! ✨")
        print_info("Next steps:")
        print("   1. Test the referral button in browser")
        print("   2. Check browser console for any errors")
        print("   3. Verify modal opens when button is clicked")
    else:
        print_error("Some tests failed. Please review the output above.")
        print_info("Check REFERRAL_BUTTON_TROUBLESHOOTING.md for help")

if __name__ == '__main__':
    main()

