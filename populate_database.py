#!/usr/bin/env python
"""
Database population script for HMS (Hospital Management System)
This script populates the database with initial data for all modules
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Add the project directory to the Python path
sys.path.append('C:\\Users\\Dell\\Desktop\\MY_PRODUCTS\\HMS')

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import Django models
from django.contrib.auth.models import Permission, Group
from accounts.models import CustomUser, CustomUserProfile, Role, Department, AuditLog
from patients.models import Patient, MedicalHistory, PatientWallet, WalletTransaction
from pharmacy.models import (
    Medication, MedicationCategory, Supplier, Purchase, 
    Dispensary, BulkStoreInventory, ActiveStoreInventory
)
from consultations.models import Consultation, Referral, WaitingList
from appointments.models import Appointment
from billing.models import Invoice, InvoiceItem, Payment
from inpatient.models import Ward, Bed, Admission
from laboratory.models import Test, TestRequest
from radiology.models import RadiologyTest, RadiologyOrder
from core.models import SOAPNote, InternalNotification
from nhia.models import NHIAPatient, AuthorizationCode
# from desk_office.models import MeetingRoom, AuthorizationRequest
from theatre.models import SurgeryType, SurgicalTeam, Surgery
from dental.models import DentalRecord
from ophthalmic.models import OphthalmicRecord
from ent.models import EntRecord
from anc.models import AncRecord
from family_planning.models import Family_planningRecord
from gynae_emergency.models import Gynae_emergencyRecord
from icu.models import IcuRecord
from labor.models import LaborRecord
from oncology.models import OncologyRecord
from scbu.models import ScbuRecord
# from hr.models import Employee, LeaveRequest
# from reporting.models import ReportTemplate

# Faker for generating realistic test data
from faker import Faker
fake = Faker()

# Disable auto-reload for faster execution
import django.db
from django.db import transaction

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_progress(message):
    """Log progress with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")
    logger.info(message)

class DatabasePopulator:
    def __init__(self):
        self.created_users = []
        self.created_patients = []
        self.created_medications = []
        self.created_departments = []
        self.created_roles = []
        
    def clear_existing_data(self):
        """Clear existing data to start fresh"""
        log_progress("Clearing existing data...")
        
        # Delete in reverse order to avoid foreign key constraints
        models_to_clear = [
            # Core models
            SOAPNote, InternalNotification, AuditLog,
            
            # App-specific models (reverse dependency order)
            RadiologyOrder, RadiologyService,
            TestRequest, Test,
            Surgery, SurgicalTeam, SurgeryType,
            Admission, Bed, Ward,
            Payment, InvoiceItem, Invoice,
            Appointment,
            Referral, Consultation, WaitingList,
            ActiveStoreInventory, BulkStoreInventory, Purchase, Supplier,
            Medication, MedicationCategory,
            Patient, MedicalHistory, Wallet, WalletTransaction,
            NHIAPatient, AuthorizationCode,
            CustomUserProfile, CustomUser,
            Role, Department,
        ]
        
        for model in models_to_clear:
            try:
                count = model.objects.count()
                if count > 0:
                    model.objects.all().delete()
                    log_progress(f"Cleared {count} records from {model.__name__}")
            except Exception as e:
                log_progress(f"Error clearing {model.__name__}: {e}")
                continue
    
    def create_roles_and_permissions(self):
        """Create roles and permissions"""
        log_progress("Creating roles and permissions...")
        
        # Create roles
        role_data = [
            {'name': 'admin', 'description': 'System Administrator with full access'},
            {'name': 'doctor', 'description': 'Medical doctor with patient care access'},
            {'name': 'nurse', 'description': 'Nursing staff with patient care access'},
            {'name': 'pharmacist', 'description': 'Pharmacy staff with medication access'},
            {'name': 'lab_technician', 'description': 'Laboratory staff with test access'},
            {'name': 'receptionist', 'description': 'Front desk staff with appointment access'},
            {'name': 'accountant', 'description': 'Financial staff with billing access'},
            {'name': 'radiology_staff', 'description': 'Radiology staff with imaging access'},
            {'name': 'health_record_officer', 'description': 'Medical records staff'},
        ]
        
        for role_info in role_data:
            role, created = Role.objects.get_or_create(
                name=role_info['name'],
                defaults={'description': role_info['description']}
            )
            if created:
                self.created_roles.append(role)
                log_progress(f"Created role: {role.name}")
    
    def create_departments(self):
        """Create hospital departments"""
        log_progress("Creating departments...")
        
        department_data = [
            'Cardiology', 'Neurology', 'Pediatrics', 'General Medicine',
            'Surgery', 'Orthopedics', 'Obstetrics & Gynecology',
            'Emergency Medicine', 'Radiology', 'Laboratory',
            'Pharmacy', 'Administration', 'Finance', 'Human Resources'
        ]
        
        for dept_name in department_data:
            dept, created = Department.objects.get_or_create(
                name=dept_name,
                defaults={'description': f'{dept_name} Department'}
            )
            if created:
                self.created_departments.append(dept)
                log_progress(f"Created department: {dept.name}")
    
    def create_admin_user(self):
        """Create admin user"""
        log_progress("Creating admin user...")
        
        admin_user, created = CustomUser.objects.get_or_create(
            username='admin',
            defaults={
                'phone_number': '1234567890',
                'first_name': 'Admin',
                'last_name': 'User',
                'email': 'admin@hospital.com',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True
            }
        )
        
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            
            # Create profile
            profile = CustomUserProfile.objects.create(
                user=admin_user,
                phone_number='1234567890',
                address='Hospital Admin Office',
                role='admin',
                department=self.created_departments[0] if self.created_departments else None
            )
            
            # Assign admin role
            admin_role = Role.objects.filter(name='admin').first()
            if admin_role:
                admin_user.roles.add(admin_role)
            
            self.created_users.append(admin_user)
            log_progress(f"Created admin user: {admin_user.username}")
        
        return admin_user
    
    def create_sample_users(self, count=10):
        """Create sample users for different roles"""
        log_progress(f"Creating {count} sample users...")
        
        role_names = ['doctor', 'nurse', 'pharmacist', 'lab_technician', 'receptionist']
        
        for i in range(count):
            role_name = random.choice(role_names)
            username = f"{role_name}_{i+1}"
            phone_number = f"{random.randint(1000000000, 9999999999)}"
            
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'phone_number': phone_number,
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'email': fake.email(),
                    'is_active': True
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                
                # Create profile
                profile = CustomUserProfile.objects.create(
                    user=user,
                    phone_number=phone_number,
                    address=fake.address(),
                    role=role_name,
                    department=random.choice(self.created_departments) if self.created_departments else None,
                    employee_id=f"EMP{1000 + i}"
                )
                
                # Assign role
                role = Role.objects.filter(name=role_name).first()
                if role:
                    user.roles.add(role)
                
                self.created_users.append(user)
        
        log_progress(f"Created {count} sample users")
    
    def create_patients(self, count=20):
        """Create sample patients"""
        log_progress(f"Creating {count} sample patients...")
        
        patient_types = ['regular', 'nhia', 'private', 'insurance']
        genders = ['M', 'F', 'O']
        
        for i in range(count):
            patient_type = random.choice(patient_types)
            gender = random.choice(genders)
            
            # Generate date of birth (age between 1 and 90)
            age = random.randint(1, 90)
            dob = datetime.now() - timedelta(days=age*365)
            
            patient, created = Patient.objects.get_or_create(
                patient_id=f"PAT{1000 + i}",
                defaults={
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'patient_type': patient_type,
                    'date_of_birth': dob.date(),
                    'gender': gender,
                    'email': fake.email(),
                    'phone_number': f"{random.randint(1000000000, 9999999999)}",
                    'address': fake.address(),
                    'city': fake.city(),
                    'state': fake.state(),
                    'country': 'India',
                    'is_active': True,
                    'primary_doctor': random.choice(self.created_users) if self.created_users else None
                }
            )
            
            if created:
                # Create medical history
                MedicalHistory.objects.create(
                    patient=patient,
                    condition=fake.text(max_nb_chars=100),
                    diagnosis=fake.text(max_nb_chars=50),
                    treatment=fake.text(max_nb_chars=200),
                    notes=fake.text(max_nb_chars=100)
                )
                
                # Create wallet
                PatientWallet.objects.create(
                    patient=patient,
                    balance=Decimal(random.uniform(100, 5000)),
                    currency='INR'
                )
                
                self.created_patients.append(patient)
        
        log_progress(f"Created {count} sample patients")
    
    def create_medications(self, count=30):
        """Create sample medications"""
        log_progress(f"Creating {count} sample medications...")
        
        # Create medication categories
        categories = []
        category_names = ['Antibiotics', 'Pain Relief', 'Cardiovascular', 'Antidiabetic', 'Vitamins']
        
        for cat_name in category_names:
            category, created = MedicationCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'{cat_name} medications'}
            )
            categories.append(category)
        
        # Create medications
        for i in range(count):
            category = random.choice(categories)
            
            medication, created = Medication.objects.get_or_create(
                name=f"Medication {i+1}",
                defaults={
                    'generic_name': f"Generic {i+1}",
                    'category': category,
                    'dosage_form': random.choice(['Tablet', 'Capsule', 'Syrup', 'Injection']),
                    'strength': f"{random.choice([50, 100, 200, 500])}mg",
                    'manufacturer': fake.company(),
                    'price': Decimal(random.uniform(10, 500)),
                    'reorder_level': random.randint(5, 50),
                    'expiry_date': datetime.now() + timedelta(days=random.randint(30, 365)),
                    'is_active': True
                }
            )
            
            if created:
                self.created_medications.append(medication)
        
        log_progress(f"Created {count} sample medications")
    
    def create_suppliers(self, count=5):
        """Create sample suppliers"""
        log_progress(f"Creating {count} sample suppliers...")
        
        for i in range(count):
            Supplier.objects.get_or_create(
                name=f"Supplier {i+1}",
                defaults={
                    'contact_person': fake.name(),
                    'email': fake.email(),
                    'phone_number': f"{random.randint(1000000000, 9999999999)}",
                    'address': fake.address(),
                    'city': fake.city(),
                    'state': fake.state(),
                    'country': 'India',
                    'is_active': True
                }
            )
        
        log_progress(f"Created {count} sample suppliers")
    
    def create_dispensaries(self, count=2):
        """Create sample dispensaries"""
        log_progress(f"Creating {count} sample dispensaries...")
        
        for i in range(count):
            Dispensary.objects.get_or_create(
                name=f"Dispensary {i+1}",
                defaults={
                    'location': f"Floor {i+1}",
                    'phone_number': f"{random.randint(1000000000, 9999999999)}",
                    'is_active': True,
                    'is_bulk_store': (i == 0)  # First one is bulk store
                }
            )
        
        log_progress(f"Created {count} sample dispensaries")
    
    def create_inventory(self):
        """Create inventory for medications"""
        log_progress("Creating inventory...")
        
        dispensaries = Dispensary.objects.all()
        if not dispensaries:
            self.create_dispensaries()
            dispensaries = Dispensary.objects.all()
        
        bulk_store = dispensaries.filter(is_bulk_store=True).first()
        active_stores = dispensaries.filter(is_bulk_store=False)
        
        if bulk_store and self.created_medications:
            for medication in self.created_medications:
                # Bulk store inventory
                BulkStoreInventory.objects.get_or_create(
                    medication=medication,
                    defaults={
                        'dispensary': bulk_store,
                        'quantity': random.randint(50, 500),
                        'unit_cost': medication.price * Decimal('0.7'),
                        'marked_up_cost': medication.price,
                        'expiry_date': datetime.now() + timedelta(days=random.randint(30, 365)),
                        'batch_number': f"BATCH-{random.randint(1000, 9999)}"
                    }
                )
                
                # Active store inventory
                for store in active_stores:
                    ActiveStoreInventory.objects.get_or_create(
                        medication=medication,
                        dispensary=store,
                        defaults={
                            'quantity': random.randint(10, 100),
                            'unit_cost': medication.price,
                            'expiry_date': datetime.now() + timedelta(days=random.randint(30, 365)),
                            'batch_number': f"BATCH-{random.randint(1000, 9999)}"
                        }
                    )
        
        log_progress("Created inventory for medications")
    
    def create_consultations(self, count=15):
        """Create sample consultations"""
        log_progress(f"Creating {count} sample consultations...")
        
        if not self.created_patients or not self.created_users:
            log_progress("Need patients and users to create consultations")
            return
        
        consultation_types = ['General', 'Follow-up', 'Emergency', 'Specialist']
        statuses = ['Scheduled', 'In Progress', 'Completed', 'Cancelled']
        
        for i in range(count):
            patient = random.choice(self.created_patients)
            doctor = random.choice([u for u in self.created_users if hasattr(u, 'profile') and u.profile.role == 'doctor'])
            
            consultation, created = Consultation.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                consultation_date=datetime.now() - timedelta(days=random.randint(1, 30)),
                defaults={
                    'consultation_type': random.choice(consultation_types),
                    'status': random.choice(statuses),
                    'chief_complaint': fake.text(max_nb_chars=100),
                    'diagnosis': fake.text(max_nb_chars=200),
                    'treatment_plan': fake.text(max_nb_chars=200),
                    'notes': fake.text(max_nb_chars=100)
                }
            )
            
            if created and random.random() > 0.5:
                # Create SOAP note for some consultations
                SOAPNote.objects.create(
                    consultation=consultation,
                    created_by=doctor,
                    subjective=fake.text(max_nb_chars=100),
                    objective=fake.text(max_nb_chars=100),
                    assessment=fake.text(max_nb_chars=100),
                    plan=fake.text(max_nb_chars=100)
                )
        
        log_progress(f"Created {count} sample consultations")
    
    def create_appointments(self, count=10):
        """Create sample appointments"""
        log_progress(f"Creating {count} sample appointments...")
        
        if not self.created_patients or not self.created_users:
            log_progress("Need patients and users to create appointments")
            return
        
        appointment_types = ['New Patient', 'Follow-up', 'Routine Checkup', 'Specialist']
        statuses = ['Scheduled', 'Confirmed', 'Cancelled', 'Completed', 'No Show']
        
        for i in range(count):
            patient = random.choice(self.created_patients)
            doctor = random.choice([u for u in self.created_users if hasattr(u, 'profile') and u.profile.role == 'doctor'])
            
            appointment_date = datetime.now() + timedelta(days=random.randint(1, 30))
            
            Appointment.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                appointment_date=appointment_date,
                defaults={
                    'appointment_type': random.choice(appointment_types),
                    'status': random.choice(statuses),
                    'reason': fake.text(max_nb_chars=100),
                    'notes': fake.text(max_nb_chars=50)
                }
            )
        
        log_progress(f"Created {count} sample appointments")
    
    def create_invoices(self, count=10):
        """Create sample invoices"""
        log_progress(f"Creating {count} sample invoices...")
        
        if not self.created_patients:
            log_progress("Need patients to create invoices")
            return
        
        payment_methods = ['Cash', 'Credit Card', 'Bank Transfer', 'Insurance', 'NHIA']
        statuses = ['Draft', 'Issued', 'Paid', 'Cancelled', 'Refunded']
        
        for i in range(count):
            patient = random.choice(self.created_patients)
            
            invoice, created = Invoice.objects.get_or_create(
                invoice_number=f"INV{1000 + i}",
                defaults={
                    'patient': patient,
                    'invoice_date': datetime.now() - timedelta(days=random.randint(1, 30)),
                    'due_date': datetime.now() + timedelta(days=random.randint(1, 15)),
                    'total_amount': Decimal(random.uniform(100, 5000)),
                    'amount_paid': Decimal(random.uniform(0, 5000)),
                    'payment_method': random.choice(payment_methods),
                    'status': random.choice(statuses),
                    'notes': fake.text(max_nb_chars=100)
                }
            )
            
            if created and random.random() > 0.3:
                # Create payment for some invoices
                Payment.objects.create(
                    invoice=invoice,
                    amount=invoice.amount_paid,
                    payment_date=datetime.now() - timedelta(days=random.randint(1, 5)),
                    payment_method=invoice.payment_method,
                    transaction_id=f"TXN{random.randint(100000, 999999)}",
                    status='Completed'
                )
        
        log_progress(f"Created {count} sample invoices")
    
    def create_wards_and_beds(self):
        """Create wards and beds"""
        log_progress("Creating wards and beds...")
        
        ward_types = ['General', 'Private', 'ICU', 'Maternity', 'Pediatric']
        
        for i in range(5):
            ward, created = Ward.objects.get_or_create(
                name=f"Ward {i+1}",
                defaults={
                    'ward_type': ward_types[i % len(ward_types)],
                    'capacity': random.randint(10, 30),
                    'location': f"Floor {i+1}",
                    'is_active': True,
                    'description': f"Ward {i+1} - {ward_types[i % len(ward_types)]}"
                }
            )
            
            if created:
                # Create beds for this ward
                for bed_num in range(1, random.randint(5, 15)):
                    Bed.objects.create(
                        ward=ward,
                        bed_number=f"{i+1}-{bed_num:02d}",
                        bed_type=random.choice(['Standard', 'Private', 'Semi-Private', 'ICU']),
                        status=random.choice(['Available', 'Occupied', 'Maintenance']),
                        is_active=True
                    )
        
        log_progress("Created wards and beds")
    
    def create_lab_tests(self, count=10):
        """Create sample lab tests"""
        log_progress(f"Creating {count} sample lab tests...")
        
        test_types = ['Blood Test', 'Urinalysis', 'X-Ray', 'MRI', 'CT Scan', 'Ultrasound']
        
        for i in range(count):
            Test.objects.get_or_create(
                name=f"Test {i+1}",
                defaults={
                    'test_type': random.choice(test_types),
                    'description': fake.text(max_nb_chars=100),
                    'price': Decimal(random.uniform(50, 1000)),
                    'turnaround_time': random.randint(1, 7),
                    'is_active': True
                }
            )
        
        log_progress(f"Created {count} sample lab tests")
    
    def create_radiology_tests(self, count=5):
        """Create sample radiology tests"""
        log_progress(f"Creating {count} sample radiology tests...")
        
        test_types = ['X-Ray', 'MRI', 'CT Scan', 'Ultrasound', 'Mammography']
        
        for i in range(count):
            RadiologyTest.objects.get_or_create(
                name=f"Radiology Test {i+1}",
                defaults={
                    'test_type': test_types[i % len(test_types)],
                    'description': fake.text(max_nb_chars=100),
                    'price': Decimal(random.uniform(200, 5000)),
                    'duration': random.randint(15, 120),
                    'is_active': True
                }
            )
        
        log_progress(f"Created {count} sample radiology tests")
    
    def create_nhia_data(self, count=5):
        """Create sample NHIA data"""
        log_progress(f"Creating {count} sample NHIA patients...")
        
        nhia_patients = [p for p in self.created_patients if p.patient_type == 'nhia']
        
        for patient in nhia_patients[:count]:
            NHIAPatient.objects.get_or_create(
                patient=patient,
                defaults={
                    'nhia_number': f"NHIA{random.randint(100000000, 999999999)}",
                    'nhia_expiry_date': datetime.now() + timedelta(days=365),
                    'nhia_type': random.choice(['Standard', 'Premium', 'Basic']),
                    'is_active': True,
                    'authorization_required': random.choice([True, False])
                }
            )
            
            if random.random() > 0.5:
                # Create authorization code for some NHIA patients
                AuthorizationCode.objects.create(
                    patient=patient,
                    code=f"AUTH{random.randint(100000, 999999)}",
                    service_type=random.choice(['Consultation', 'Medication', 'Procedure']),
                    amount=Decimal(random.uniform(100, 2000)),
                    expiry_date=datetime.now() + timedelta(days=random.randint(30, 180)),
                    is_used=False
                )
        
        log_progress(f"Created {count} sample NHIA patients")
    
    def populate_all(self):
        """Populate all data"""
        log_progress("Starting database population...")
        
        try:
            # Clear existing data
            self.clear_existing_data()
            
            # Create foundational data
            self.create_roles_and_permissions()
            self.create_departments()
            
            # Create users
            self.create_admin_user()
            self.create_sample_users(15)
            
            # Create patient data
            self.create_patients(25)
            
            # Create pharmacy data
            self.create_medications(40)
            self.create_suppliers(8)
            self.create_dispensaries(3)
            self.create_inventory()
            
            # Create clinical data
            self.create_consultations(20)
            self.create_appointments(15)
            
            # Create financial data
            self.create_invoices(12)
            
            # Create facility data
            self.create_wards_and_beds()
            
            # Create diagnostic data
            self.create_lab_tests(12)
            self.create_radiology_tests(6)
            
            # Create NHIA data
            self.create_nhia_data(8)
            
            log_progress("Database population completed successfully!")
            log_progress(f"Summary: {len(self.created_users)} users, {len(self.created_patients)} patients, {len(self.created_medications)} medications")
            
        except Exception as e:
            log_progress(f"Error during database population: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    populator = DatabasePopulator()
    populator.populate_all()
