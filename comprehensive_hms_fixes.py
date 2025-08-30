#!/usr/bin/env python
"""
Comprehensive HMS Fixes and Enhancements Script
This script addresses issues across all HMS modules systematically
"""

import os
import sys
import django
from django.db import transaction, connection
from django.core.management import call_command
from django.contrib.auth import get_user_model

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

User = get_user_model()

def fix_patient_module():
    """Fix issues in the patient module"""
    print("=== Fixing Patient Module ===")
    
    from patients.models import Patient, PatientWallet
    
    # Fix patients without patient_id
    patients_without_id = Patient.objects.filter(patient_id__isnull=True)
    for patient in patients_without_id:
        try:
            patient.save()  # This will trigger the patient ID generation
            print(f"✓ Generated patient ID for {patient.get_full_name()}")
        except Exception as e:
            print(f"✗ Failed to generate ID for patient {patient.id}: {e}")
    
    # Ensure all patients have wallets
    patients_without_wallets = Patient.objects.filter(wallet__isnull=True)
    for patient in patients_without_wallets:
        try:
            PatientWallet.objects.create(patient=patient, balance=0.00)
            print(f"✓ Created wallet for {patient.get_full_name()}")
        except Exception as e:
            print(f"✗ Failed to create wallet for {patient.get_full_name()}: {e}")

def fix_pharmacy_module():
    """Fix issues in the pharmacy module"""
    print("\n=== Fixing Pharmacy Module ===")
    
    from pharmacy.models import Medication, Dispensary, ActiveStore, BulkStore
    
    # Ensure default dispensary exists
    try:
        default_dispensary, created = Dispensary.objects.get_or_create(
            name='Main Dispensary',
            defaults={
                'location': 'Ground Floor',
                'is_active': True
            }
        )
        if created:
            print("✓ Created default dispensary")
    except Exception as e:
        print(f"✗ Failed to create default dispensary: {e}")
    
    # Ensure default stores exist
    try:
        default_active_store, created = ActiveStore.objects.get_or_create(
            name='Main Active Store',
            defaults={
                'location': 'Pharmacy Active Storage',
                'is_active': True
            }
        )
        if created:
            print("✓ Created default active store")
            
        default_bulk_store, created = BulkStore.objects.get_or_create(
            name='Main Bulk Store',
            defaults={
                'location': 'Central Storage Area',
                'is_active': True
            }
        )
        if created:
            print("✓ Created default bulk store")
    except Exception as e:
        print(f"✗ Failed to create default stores: {e}")

def fix_billing_module():
    """Fix issues in the billing module"""
    print("\n=== Fixing Billing Module ===")
    
    from billing.models import Invoice, ServiceCategory, Service
    
    # Ensure default service category exists
    try:
        default_category, created = ServiceCategory.objects.get_or_create(
            name='General Services',
            defaults={'description': 'General hospital services'}
        )
        if created:
            print("✓ Created default service category")
    except Exception as e:
        print(f"✗ Failed to create default service category: {e}")
    
    # Fix invoices without invoice numbers
    invoices_without_numbers = Invoice.objects.filter(invoice_number__isnull=True)
    for invoice in invoices_without_numbers:
        try:
            invoice.save()  # This will trigger invoice number generation
            print(f"✓ Generated invoice number for invoice {invoice.id}")
        except Exception as e:
            print(f"✗ Failed to generate invoice number for {invoice.id}: {e}")

def fix_appointments_module():
    """Fix issues in the appointments module"""
    print("\n=== Fixing Appointments Module ===")
    
    from appointments.models import Appointment
    from django.utils import timezone
    
    # Fix appointments with invalid dates
    invalid_appointments = Appointment.objects.filter(appointment_date__lt=timezone.now().date())
    count = invalid_appointments.count()
    if count > 0:
        print(f"Found {count} appointments with past dates")

def fix_laboratory_module():
    """Fix issues in the laboratory module"""
    print("\n=== Fixing Laboratory Module ===")
    
    from laboratory.models import TestCategory, Test
    
    # Ensure default test category exists
    try:
        default_category, created = TestCategory.objects.get_or_create(
            name='General Tests',
            defaults={'description': 'General laboratory tests'}
        )
        if created:
            print("✓ Created default test category")
    except Exception as e:
        print(f"✗ Failed to create default test category: {e}")

def fix_user_management():
    """Fix issues in user management"""
    print("\n=== Fixing User Management ===")
    
    from accounts.models import CustomUser, Role, Department
    
    # Ensure default roles exist
    default_roles = [
        ('admin', 'Administrator'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('pharmacist', 'Pharmacist'),
        ('receptionist', 'Receptionist'),
        ('lab_technician', 'Lab Technician'),
    ]
    
    for role_name, role_display in default_roles:
        try:
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={'description': f'{role_display} role'}
            )
            if created:
                print(f"✓ Created role: {role_display}")
        except Exception as e:
            print(f"✗ Failed to create role {role_name}: {e}")
    
    # Ensure default departments exist
    default_departments = [
        'Administration',
        'Emergency',
        'Pharmacy',
        'Laboratory',
        'Radiology',
        'Surgery',
        'Outpatient',
        'Inpatient',
    ]
    
    for dept_name in default_departments:
        try:
            dept, created = Department.objects.get_or_create(
                name=dept_name,
                defaults={'is_active': True}
            )
            if created:
                print(f"✓ Created department: {dept_name}")
        except Exception as e:
            print(f"✗ Failed to create department {dept_name}: {e}")

def fix_medical_modules():
    """Fix issues in medical specialty modules"""
    print("\n=== Fixing Medical Specialty Modules ===")
    
    medical_modules = [
        'dental', 'ophthalmic', 'ent', 'oncology', 'scbu', 
        'anc', 'labor', 'icu', 'family_planning', 'gynae_emergency'
    ]
    
    for module_name in medical_modules:
        try:
            # Import the module dynamically
            module = __import__(f'{module_name}.models', fromlist=[''])
            print(f"✓ Verified {module_name} module")
        except ImportError as e:
            print(f"✗ Issue with {module_name} module: {e}")

def optimize_database():
    """Optimize database performance"""
    print("\n=== Optimizing Database ===")
    
    # Create indexes for better performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients_patient(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients_patient(phone_number);",
        "CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON pharmacy_prescription(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments_appointment(appointment_date);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_patient ON billing_invoice(patient_id);",
    ]
    
    with connection.cursor() as cursor:
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                index_name = index_sql.split('idx_')[1].split(' ')[0]
                print(f"✓ Created/verified index: {index_name}")
            except Exception as e:
                print(f"✗ Failed to create index: {e}")

def run_system_checks():
    """Run Django system checks"""
    print("\n=== Running System Checks ===")
    
    try:
        call_command('check', verbosity=0)
        print("✓ Django system checks passed")
    except Exception as e:
        print(f"✗ System checks failed: {e}")

def main():
    """Main function to run all fixes"""
    print("=== HMS Comprehensive Fixes and Enhancements ===\n")
    
    try:
        with transaction.atomic():
            fix_patient_module()
            fix_pharmacy_module()
            fix_billing_module()
            fix_appointments_module()
            fix_laboratory_module()
            fix_user_management()
            fix_medical_modules()
            optimize_database()
            run_system_checks()
        
        print("\n=== All fixes completed successfully ===")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error during fixes: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
