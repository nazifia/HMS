#!/usr/bin/env python
"""
Simple database population script for HMS (Hospital Management System)
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
    Dispensary, BulkStore, ActiveStore, BulkStoreInventory, ActiveStoreInventory
)
from consultations.models import Consultation
from appointments.models import Appointment
from billing.models import Invoice, InvoiceItem, Payment
from inpatient.models import Ward, Bed, Admission
from laboratory.models import Test, TestRequest, TestCategory
from radiology.models import RadiologyTest, RadiologyOrder, RadiologyCategory
from core.models import SOAPNote, InternalNotification
from nhia.models import NHIAPatient, AuthorizationCode

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_progress(message):
    """Log progress with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")
    logger.info(message)

class SimpleDatabasePopulator:
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
            RadiologyOrder, RadiologyTest,
            TestRequest, Test,
            Admission, Bed, Ward,
            Payment, InvoiceItem, Invoice,
            Appointment,
            Consultation,
            ActiveStoreInventory, BulkStoreInventory, Purchase, Supplier,
            Medication, MedicationCategory,
            Patient, MedicalHistory, PatientWallet, WalletTransaction,
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
        first_names = ['John', 'Jane', 'Michael', 'Sarah', 'David', 'Emily', 'Robert', 'Jennifer']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Miller', 'Davis', 'Wilson']
        
        for i in range(count):
            role_name = role_names[i % len(role_names)]
            username = f"{role_name}_{i+1}"
            phone_number = f"{1000000000 + i}"
            
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'phone_number': phone_number,
                    'first_name': first_names[i % len(first_names)],
                    'last_name': last_names[i % len(last_names)],
                    'email': f'{username}@hospital.com',
                    'is_active': True
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                
                # Create profile (use get_or_create to avoid duplicate profile errors)
                profile, profile_created = CustomUserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'phone_number': phone_number,
                        'address': f'{i+1} Hospital Street, City',
                        'role': role_name,
                        'department': self.created_departments[i % len(self.created_departments)] if self.created_departments else None,
                        'employee_id': f"EMP{1000 + i}"
                    }
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
        first_names = ['James', 'Mary', 'Robert', 'Patricia', 'John', 'Jennifer', 'William', 'Linda']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Miller', 'Davis', 'Wilson']
        
        for i in range(count):
            patient_type = patient_types[i % len(patient_types)]
            gender = genders[i % len(genders)]
            
            # Generate date of birth (age between 1 and 90)
            age = random.randint(1, 90)
            dob = datetime.now() - timedelta(days=age*365)
            
            patient, created = Patient.objects.get_or_create(
                patient_id=f"PAT{1000 + i}",
                defaults={
                    'first_name': first_names[i % len(first_names)],
                    'last_name': last_names[i % len(last_names)],
                    'patient_type': patient_type,
                    'date_of_birth': dob.date(),
                    'gender': gender,
                    'email': f'patient{i+1}@example.com',
                    'phone_number': f"{2000000000 + i}",
                    'address': f'{i+1} Patient Street, City',
                    'city': 'Health City',
                    'state': 'Health State',
                    'country': 'India',
                    'is_active': True,
                    'primary_doctor': self.created_users[i % len(self.created_users)] if self.created_users else None
                }
            )
            
            if created:
                # Create medical history
                MedicalHistory.objects.create(
                    patient=patient,
                    diagnosis=f'Diagnosis for patient {i+1}',
                    treatment=f'Treatment plan for patient {i+1}',
                    date=datetime.now().date(),
                    doctor_name=f'Dr. {first_names[i % len(first_names)]} {last_names[i % len(last_names)]}',
                    notes=f'Medical notes for patient {i+1}'
                )
                
                # Create wallet (use get_or_create to avoid duplicate wallet errors)
                PatientWallet.objects.get_or_create(
                    patient=patient,
                    defaults={
                        'balance': Decimal(random.uniform(100, 5000)),
                        'is_active': True
                    }
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
        medication_names = [
            'Paracetamol', 'Amoxicillin', 'Ibuprofen', 'Amlodipine', 'Metformin',
            'Atorvastatin', 'Omeprazole', 'Losartan', 'Simvastatin', 'Levothyroxine',
            'Azithromycin', 'Gabapentin', 'Pregabalin', 'Sertraline', 'Citalopram',
            'Vitamin D', 'Vitamin B12', 'Calcium', 'Iron', 'Folic Acid',
            'Salbutamol', 'Montelukast', 'Fluticasone', 'Formoterol', 'Tiotropium'
        ]
        
        for i in range(count):
            category = categories[i % len(categories)]
            
            medication, created = Medication.objects.get_or_create(
                name=medication_names[i % len(medication_names)] or f"Medication {i+1}",
                defaults={
                    'generic_name': f"Generic {i+1}",
                    'category': category,
                    'dosage_form': ['Tablet', 'Capsule', 'Syrup', 'Injection'][i % 4],
                    'strength': f"{['50', '100', '200', '500'][i % 4]}mg",
                    'manufacturer': f"Pharma Company {i % 5 + 1}",
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
        
        supplier_names = ['MedPharma Inc', 'HealthSupply Corp', 'BioMed Solutions', 'CarePharma Ltd', 'MediTech Distributors']
        
        for i in range(count):
            Supplier.objects.get_or_create(
                name=supplier_names[i] if i < len(supplier_names) else f"Supplier {i+1}",
                defaults={
                    'contact_person': f'Contact Person {i+1}',
                    'email': f'supplier{i+1}@example.com',
                    'phone_number': f"{3000000000 + i}",
                    'address': f'{i+1} Supplier Street, City',
                    'city': 'Pharma City',
                    'state': 'Pharma State',
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
                    'description': f"Dispensary located on Floor {i+1}",
                    'is_active': True
                }
            )
        
        log_progress(f"Created {count} sample dispensaries")
    
    def create_inventory(self):
        """Create inventory for medications"""
        log_progress("Creating inventory...")
        
        # Create bulk store
        bulk_store, created = BulkStore.objects.get_or_create(
            name="Central Bulk Store",
            defaults={
                'location': 'Basement',
                'description': 'Main bulk storage facility',
                'capacity': 10000,
                'temperature_controlled': True,
                'humidity_controlled': True,
                'security_level': 'high',
                'is_active': True
            }
        )
        
        # Get or create active stores based on existing dispensaries
        active_stores = []
        dispensaries = Dispensary.objects.all()
        
        for i, dispensary in enumerate(dispensaries):
            store, created = ActiveStore.objects.get_or_create(
                dispensary=dispensary,
                defaults={
                    'name': f"{dispensary.name} - Active Store",
                    'location': f"Floor {i+1}",
                    'description': f'Active store for {dispensary.name}',
                    'capacity': 5000,
                    'temperature_controlled': True,
                    'humidity_controlled': True,
                    'security_level': 'medium',
                    'is_active': True
                }
            )
            active_stores.append(store)
        
        if self.created_medications:
            for medication in self.created_medications:
                # Bulk store inventory
                BulkStoreInventory.objects.get_or_create(
                    medication=medication,
                    bulk_store=bulk_store,
                    defaults={
                        'batch_number': f"BATCH-{random.randint(1000, 9999)}",
                        'stock_quantity': random.randint(50, 500),
                        'expiry_date': datetime.now() + timedelta(days=random.randint(30, 365)),
                        'unit_cost': medication.price * Decimal('0.7'),
                        'markup_percentage': Decimal('20.00'),
                        'purchase_date': datetime.now().date()
                    }
                )
                
                # Active store inventory
                for store in active_stores:
                    ActiveStoreInventory.objects.get_or_create(
                        medication=medication,
                        active_store=store,
                        defaults={
                            'batch_number': f"BATCH-{random.randint(1000, 9999)}",
                            'stock_quantity': random.randint(10, 100),
                            'expiry_date': datetime.now() + timedelta(days=random.randint(30, 365)),
                            'unit_cost': medication.price
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
            patient = self.created_patients[i % len(self.created_patients)]
            doctor = random.choice([u for u in self.created_users if hasattr(u, 'profile') and u.profile.role == 'doctor'])
            
            consultation, created = Consultation.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                consultation_date=datetime.now() - timedelta(days=random.randint(1, 30)),
                defaults={
                    'consultation_type': consultation_types[i % len(consultation_types)],
                    'status': statuses[i % len(statuses)],
                    'chief_complaint': f'Chief complaint for consultation {i+1}',
                    'diagnosis': f'Diagnosis for consultation {i+1}',
                    'treatment_plan': f'Treatment plan for consultation {i+1}',
                    'notes': f'Notes for consultation {i+1}'
                }
            )
            
            if created and i % 2 == 0:
                # Create SOAP note for some consultations
                SOAPNote.objects.create(
                    consultation=consultation,
                    created_by=doctor,
                    subjective=f'Subjective notes for consultation {i+1}',
                    objective=f'Objective findings for consultation {i+1}',
                    assessment=f'Assessment for consultation {i+1}',
                    plan=f'Plan for consultation {i+1}'
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
            patient = self.created_patients[i % len(self.created_patients)]
            doctor = random.choice([u for u in self.created_users if hasattr(u, 'profile') and u.profile.role == 'doctor'])
            
            appointment_date = datetime.now() + timedelta(days=random.randint(1, 30))
            
            Appointment.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                appointment_date=appointment_date,
                defaults={
                    'appointment_type': appointment_types[i % len(appointment_types)],
                    'status': statuses[i % len(statuses)],
                    'reason': f'Reason for appointment {i+1}',
                    'notes': f'Notes for appointment {i+1}'
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
            patient = self.created_patients[i % len(self.created_patients)]
            
            subtotal = Decimal(random.uniform(100, 5000))
            tax_amount = subtotal * Decimal('0.1')  # 10% tax
            total_amount = subtotal + tax_amount
            
            invoice, created = Invoice.objects.get_or_create(
                invoice_number=f"INV{1000 + i}",
                defaults={
                    'patient': patient,
                    'invoice_date': datetime.now() - timedelta(days=random.randint(1, 30)),
                    'due_date': datetime.now() + timedelta(days=random.randint(1, 15)),
                    'subtotal': subtotal,
                    'tax_amount': tax_amount,
                    'total_amount': total_amount,
                    'amount_paid': Decimal(random.uniform(0, float(total_amount))),
                    'payment_method': payment_methods[i % len(payment_methods)],
                    'status': statuses[i % len(statuses)],
                    'notes': f'Notes for invoice {i+1}'
                }
            )
            
            if created and i % 3 == 0:
                # Create payment for some invoices
                Payment.objects.create(
                    invoice=invoice,
                    amount=invoice.amount_paid,
                    payment_date=datetime.now() - timedelta(days=random.randint(1, 5)),
                    payment_method=invoice.payment_method,
                    transaction_id=f"TXN{random.randint(100000, 999999)}"
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
                    'floor': f"Floor {i+1}",
                    'capacity': random.randint(10, 30),
                    'charge_per_day': Decimal(random.uniform(500, 5000)),
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
                        description=f"Bed {bed_num:02d} in Ward {i+1}",
                        is_occupied=['Available', 'Occupied', 'Maintenance'][bed_num % 3] == 'Occupied',
                        is_active=True
                    )
        
        log_progress("Created wards and beds")
    
    def create_lab_tests(self, count=10):
        """Create sample lab tests"""
        log_progress(f"Creating {count} sample lab tests...")
        
        # Create test categories
        categories = []
        category_names = ['Blood Tests', 'Urinalysis', 'Imaging', 'Microbiology', 'Chemistry']
        
        for cat_name in category_names:
            category, created = TestCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'{cat_name} tests'}
            )
            categories.append(category)
        
        test_names = ['Complete Blood Count', 'Basic Metabolic Panel', 'Urinalysis', 'Chest X-Ray', 'MRI Brain', 'CT Abdomen', 'Ultrasound Abdomen', 'Thyroid Function Test', 'Liver Function Test', 'Kidney Function Test']
        sample_types = ['blood', 'urine', 'blood', 'blood', 'blood', 'blood', 'urine', 'blood', 'blood', 'blood']
        durations = ['1 day', '1 day', '2 hours', '1 hour', '2 days', '2 hours', '1 hour', '1 day', '1 day', '1 day']
        
        for i in range(count):
            Test.objects.get_or_create(
                name=test_names[i % len(test_names)] or f"Test {i+1}",
                defaults={
                    'category': categories[i % len(categories)],
                    'description': f'Description for test {i+1}',
                    'price': Decimal(random.uniform(50, 1000)),
                    'preparation_instructions': f'Instructions for test {i+1}',
                    'normal_range': f'Normal range for test {i+1}',
                    'unit': f'unit{i+1}',
                    'sample_type': sample_types[i % len(sample_types)],
                    'duration': durations[i % len(durations)],
                    'is_active': True
                }
            )
        
        log_progress(f"Created {count} sample lab tests")
    
    def create_radiology_tests(self, count=5):
        """Create sample radiology tests"""
        log_progress(f"Creating {count} sample radiology tests...")
        
        # Create radiology categories
        categories = []
        category_names = ['X-Ray', 'MRI', 'CT Scan', 'Ultrasound', 'Mammography']
        
        for cat_name in category_names:
            category, created = RadiologyCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'{cat_name} tests'}
            )
            categories.append(category)
        
        test_names = ['Chest X-Ray', 'MRI Brain', 'CT Abdomen', 'Ultrasound Abdomen', 'Mammography']
        
        for i in range(count):
            RadiologyTest.objects.get_or_create(
                name=test_names[i % len(test_names)] or f"Radiology Test {i+1}",
                defaults={
                    'category': categories[i % len(categories)],
                    'description': f'Description for radiology test {i+1}',
                    'price': Decimal(random.uniform(200, 5000)),
                    'duration_minutes': random.randint(15, 120),
                    'is_active': True
                }
            )
        
        log_progress(f"Created {count} sample radiology tests")
    
    def create_nhia_data(self, count=5):
        """Create sample NHIA data"""
        log_progress(f"Creating {count} sample NHIA patients...")
        
        nhia_patients = [p for p in self.created_patients if p.patient_type == 'nhia']
        
        for i, patient in enumerate(nhia_patients[:count]):
            NHIAPatient.objects.get_or_create(
                patient=patient,
                defaults={
                    'nhia_reg_number': f"NHIA{100000000 + i}",
                    'is_active': True
                }
            )
            
            if i % 2 == 0:
                # Create authorization code for some NHIA patients
                AuthorizationCode.objects.create(
                    patient=patient,
                    code=f"AUTH{100000 + i}",
                    service_type=['laboratory', 'radiology', 'general'][i % 3],
                    amount=Decimal(random.uniform(100, 2000)),
                    expiry_date=datetime.now() + timedelta(days=random.randint(30, 180)),
                    status='active',
                    notes=f'Authorization code for patient {i+1}'
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
    populator = SimpleDatabasePopulator()
    populator.populate_all()
