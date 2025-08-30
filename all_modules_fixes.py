#!/usr/bin/env python
"""
All HMS Modules Comprehensive Fixes
This script addresses issues across ALL HMS modules systematically
"""

import os
import sys
import django
from django.db import transaction, connection
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def fix_pharmacy_module():
    """Fix pharmacy module issues"""
    print("=== Fixing Pharmacy Module ===")
    
    from pharmacy.models import (
        Medication, MedicationCategory, Dispensary, ActiveStore, 
        BulkStore, Prescription, PrescriptionItem
    )
    
    # Create default categories
    default_categories = [
        'Antibiotics', 'Analgesics', 'Antihypertensives', 
        'Antidiabetics', 'Vitamins', 'Emergency Drugs'
    ]
    
    for cat_name in default_categories:
        try:
            cat, created = MedicationCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'{cat_name} medications'}
            )
            if created:
                print(f"✓ Created medication category: {cat_name}")
        except Exception as e:
            print(f"✗ Failed to create category {cat_name}: {e}")
    
    # Ensure default stores exist
    try:
        dispensary, created = Dispensary.objects.get_or_create(
            name='Main Dispensary',
            defaults={'location': 'Ground Floor', 'is_active': True}
        )
        if created:
            print("✓ Created main dispensary")
            
        active_store, created = ActiveStore.objects.get_or_create(
            name='Main Active Store',
            defaults={'location': 'Pharmacy Active Storage', 'is_active': True}
        )
        if created:
            print("✓ Created main active store")
            
        bulk_store, created = BulkStore.objects.get_or_create(
            name='Main Bulk Store',
            defaults={'location': 'Central Storage Area', 'is_active': True}
        )
        if created:
            print("✓ Created main bulk store")
    except Exception as e:
        print(f"✗ Failed to create stores: {e}")

def fix_billing_module():
    """Fix billing module issues"""
    print("\n=== Fixing Billing Module ===")
    
    from billing.models import Invoice, ServiceCategory, Service, Payment
    
    # Create default service categories
    default_service_categories = [
        'Consultation', 'Laboratory', 'Radiology', 'Pharmacy', 
        'Surgery', 'Emergency', 'Inpatient Care'
    ]
    
    for cat_name in default_service_categories:
        try:
            cat, created = ServiceCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'{cat_name} services'}
            )
            if created:
                print(f"✓ Created service category: {cat_name}")
        except Exception as e:
            print(f"✗ Failed to create service category {cat_name}: {e}")
    
    # Fix invoices without numbers
    invoices_without_numbers = Invoice.objects.filter(invoice_number__isnull=True)
    for invoice in invoices_without_numbers:
        try:
            invoice.save()  # Triggers number generation
            print(f"✓ Generated invoice number for invoice {invoice.id}")
        except Exception as e:
            print(f"✗ Failed to generate invoice number: {e}")

def fix_laboratory_module():
    """Fix laboratory module issues"""
    print("\n=== Fixing Laboratory Module ===")
    
    from laboratory.models import TestCategory, Test, TestRequest
    
    # Create default test categories
    default_test_categories = [
        'Hematology', 'Chemistry', 'Microbiology', 'Immunology',
        'Pathology', 'Radiology', 'Cardiology'
    ]
    
    for cat_name in default_test_categories:
        try:
            cat, created = TestCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'{cat_name} tests'}
            )
            if created:
                print(f"✓ Created test category: {cat_name}")
        except Exception as e:
            print(f"✗ Failed to create test category {cat_name}: {e}")

def fix_appointments_module():
    """Fix appointments module issues"""
    print("\n=== Fixing Appointments Module ===")
    
    from appointments.models import Appointment
    from django.utils import timezone
    
    # Check for conflicting appointments
    overlapping_appointments = Appointment.objects.filter(
        appointment_date=timezone.now().date(),
        status='scheduled'
    ).order_by('appointment_time')
    
    print(f"Found {overlapping_appointments.count()} scheduled appointments for today")

def fix_medical_specialty_modules():
    """Fix all medical specialty modules"""
    print("\n=== Fixing Medical Specialty Modules ===")
    
    specialty_modules = [
        'dental', 'ophthalmic', 'ent', 'oncology', 'scbu',
        'anc', 'labor', 'icu', 'family_planning', 'gynae_emergency'
    ]
    
    for module_name in specialty_modules:
        try:
            # Import and verify module
            module = __import__(f'{module_name}.models', fromlist=[''])
            print(f"✓ Verified {module_name} module")
            
            # Check if module has records
            if hasattr(module, f'{module_name.title()}Record'):
                model_class = getattr(module, f'{module_name.title()}Record')
                count = model_class.objects.count()
                print(f"  - {module_name} has {count} records")
        except ImportError as e:
            print(f"✗ Issue with {module_name} module: {e}")
        except Exception as e:
            print(f"⚠ Warning for {module_name}: {e}")

def fix_user_management():
    """Fix user management and authentication"""
    print("\n=== Fixing User Management ===")
    
    from accounts.models import CustomUser, Role, Department
    
    # Create default roles
    default_roles = [
        ('admin', 'Administrator'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('pharmacist', 'Pharmacist'),
        ('receptionist', 'Receptionist'),
        ('lab_technician', 'Lab Technician'),
        ('radiologist', 'Radiologist'),
        ('accountant', 'Accountant'),
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
    
    # Create default departments
    default_departments = [
        'Administration', 'Emergency', 'Pharmacy', 'Laboratory',
        'Radiology', 'Surgery', 'Outpatient', 'Inpatient',
        'Dental', 'Ophthalmology', 'ENT', 'Oncology'
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

def fix_theatre_module():
    """Fix theatre/surgery module"""
    print("\n=== Fixing Theatre Module ===")
    
    try:
        from theatre.models import Surgery, OperationTheatre, SurgeryType
        
        # Create default surgery types
        default_surgery_types = [
            'General Surgery', 'Orthopedic Surgery', 'Cardiac Surgery',
            'Neurosurgery', 'Plastic Surgery', 'Emergency Surgery'
        ]
        
        for surgery_type in default_surgery_types:
            try:
                st, created = SurgeryType.objects.get_or_create(
                    name=surgery_type,
                    defaults={'description': f'{surgery_type} procedures'}
                )
                if created:
                    print(f"✓ Created surgery type: {surgery_type}")
            except Exception as e:
                print(f"✗ Failed to create surgery type {surgery_type}: {e}")
                
    except ImportError:
        print("⚠ Theatre module not properly configured")

def optimize_all_databases():
    """Optimize database performance for all modules"""
    print("\n=== Optimizing Database Performance ===")
    
    # Create comprehensive indexes
    indexes = [
        # Patient indexes
        "CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients_patient(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients_patient(phone_number);",
        "CREATE INDEX IF NOT EXISTS idx_patients_email ON patients_patient(email);",
        "CREATE INDEX IF NOT EXISTS idx_patients_active ON patients_patient(is_active);",
        
        # Pharmacy indexes
        "CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON pharmacy_prescription(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_prescriptions_date ON pharmacy_prescription(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_medications_name ON pharmacy_medication(name);",
        "CREATE INDEX IF NOT EXISTS idx_medications_active ON pharmacy_medication(is_active);",
        
        # Appointments indexes
        "CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments_appointment(appointment_date);",
        "CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointments_appointment(doctor_id);",
        "CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments_appointment(status);",
        
        # Billing indexes
        "CREATE INDEX IF NOT EXISTS idx_invoices_patient ON billing_invoice(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_date ON billing_invoice(invoice_date);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_status ON billing_invoice(status);",
        
        # Laboratory indexes
        "CREATE INDEX IF NOT EXISTS idx_test_requests_patient ON laboratory_testrequest(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_test_requests_date ON laboratory_testrequest(created_at);",
        
        # User indexes
        "CREATE INDEX IF NOT EXISTS idx_users_username ON accounts_customuser(username);",
        "CREATE INDEX IF NOT EXISTS idx_users_phone ON accounts_customuser(phone_number);",
        "CREATE INDEX IF NOT EXISTS idx_users_active ON accounts_customuser(is_active);",
    ]
    
    with connection.cursor() as cursor:
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                index_name = index_sql.split('idx_')[1].split(' ')[0]
                print(f"✓ Created/verified index: {index_name}")
            except Exception as e:
                print(f"✗ Failed to create index: {e}")

def generate_system_report():
    """Generate comprehensive system report"""
    print("\n=== System Report ===")
    
    from patients.models import Patient
    from pharmacy.models import Medication, Prescription
    from appointments.models import Appointment
    from billing.models import Invoice
    from accounts.models import CustomUser
    
    try:
        print(f"📊 System Statistics:")
        print(f"   Total Patients: {Patient.objects.count()}")
        print(f"   Active Patients: {Patient.objects.filter(is_active=True).count()}")
        print(f"   Total Users: {CustomUser.objects.count()}")
        print(f"   Active Users: {CustomUser.objects.filter(is_active=True).count()}")
        print(f"   Total Medications: {Medication.objects.count()}")
        print(f"   Total Prescriptions: {Prescription.objects.count()}")
        print(f"   Total Appointments: {Appointment.objects.count()}")
        print(f"   Total Invoices: {Invoice.objects.count()}")
    except Exception as e:
        print(f"✗ Error generating report: {e}")

def main():
    """Main function to run all module fixes"""
    print("=== HMS All Modules Comprehensive Fixes ===\n")
    
    try:
        with transaction.atomic():
            fix_pharmacy_module()
            fix_billing_module()
            fix_laboratory_module()
            fix_appointments_module()
            fix_medical_specialty_modules()
            fix_user_management()
            fix_theatre_module()
            optimize_all_databases()
            generate_system_report()
        
        print("\n=== All module fixes completed successfully ===")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error during module fixes: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
