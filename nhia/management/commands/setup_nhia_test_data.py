"""
Django management command to set up test data for NHIA authorization system testing.

Usage:
    python manage.py setup_nhia_test_data
    python manage.py setup_nhia_test_data --clear  # Clear existing test data first
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
import random

from patients.models import Patient
from nhia.models import NHIAPatient
from accounts.models import Department, CustomUserProfile
from consultations.models import ConsultingRoom
from doctors.models import Doctor, Specialization

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up test data for NHIA authorization system testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before creating new data',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('NHIA Authorization System - Test Data Setup'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if options['clear']:
            self.clear_test_data()
        
        try:
            with transaction.atomic():
                # Step 1: Create/Verify Departments
                self.stdout.write('\n' + self.style.WARNING('Step 1: Setting up Departments...'))
                nhia_dept, general_dept, cardiology_dept, pediatrics_dept = self.setup_departments()
                
                # Step 2: Create/Verify Consulting Rooms
                self.stdout.write('\n' + self.style.WARNING('Step 2: Setting up Consulting Rooms...'))
                nhia_room, general_room, cardiology_room = self.setup_consulting_rooms(
                    nhia_dept, general_dept, cardiology_dept
                )
                
                # Step 3: Create Test Users (Doctors, Desk Office Staff)
                self.stdout.write('\n' + self.style.WARNING('Step 3: Setting up Test Users...'))
                nhia_doctor, general_doctor, cardiology_doctor, desk_staff = self.setup_users(
                    nhia_dept, general_dept, cardiology_dept
                )
                
                # Step 4: Create Test Patients (NHIA and Regular)
                self.stdout.write('\n' + self.style.WARNING('Step 4: Setting up Test Patients...'))
                nhia_patients, regular_patients = self.setup_patients()
                
                # Step 5: Display Summary
                self.display_summary(
                    nhia_dept, general_dept, cardiology_dept,
                    nhia_room, general_room, cardiology_room,
                    nhia_doctor, general_doctor, cardiology_doctor, desk_staff,
                    nhia_patients, regular_patients
                )
                
                self.stdout.write('\n' + self.style.SUCCESS('✓ Test data setup completed successfully!'))
                self.stdout.write(self.style.SUCCESS('=' * 70))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error setting up test data: {str(e)}'))
            raise

    def clear_test_data(self):
        """Clear existing test data"""
        self.stdout.write(self.style.WARNING('\nClearing existing test data...'))
        
        # Note: Be careful with this in production!
        # This only clears data created by this command (identifiable by specific patterns)
        
        # Clear test patients (those with patient_id starting with specific patterns)
        test_patients = Patient.objects.filter(
            first_name__startswith='Test'
        )
        count = test_patients.count()
        test_patients.delete()
        self.stdout.write(f'  - Cleared {count} test patients')
        
        # Clear test users
        test_users = User.objects.filter(
            username__startswith='test_'
        )
        count = test_users.count()
        test_users.delete()
        self.stdout.write(f'  - Cleared {count} test users')

    def setup_departments(self):
        """Create or get required departments"""
        # NHIA Department
        nhia_dept, created = Department.objects.get_or_create(
            name='NHIA',
            defaults={'description': 'National Health Insurance Authority Department'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Created NHIA department'))
        else:
            self.stdout.write('  - NHIA department already exists')
        
        # General Medicine Department
        general_dept, created = Department.objects.get_or_create(
            name='General Medicine',
            defaults={'description': 'General Medicine Department'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Created General Medicine department'))
        else:
            self.stdout.write('  - General Medicine department already exists')
        
        # Cardiology Department
        cardiology_dept, created = Department.objects.get_or_create(
            name='Cardiology',
            defaults={'description': 'Cardiology Department'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Created Cardiology department'))
        else:
            self.stdout.write('  - Cardiology department already exists')
        
        # Pediatrics Department
        pediatrics_dept, created = Department.objects.get_or_create(
            name='Pediatrics',
            defaults={'description': 'Pediatrics Department'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Created Pediatrics department'))
        else:
            self.stdout.write('  - Pediatrics department already exists')
        
        return nhia_dept, general_dept, cardiology_dept, pediatrics_dept

    def setup_consulting_rooms(self, nhia_dept, general_dept, cardiology_dept):
        """Create or get consulting rooms"""
        # NHIA Consulting Room
        nhia_room, created = ConsultingRoom.objects.get_or_create(
            room_number='NHIA-101',
            defaults={
                'floor': '1st Floor',
                'department': nhia_dept,
                'description': 'NHIA Consultation Room',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Created NHIA consulting room (NHIA-101)'))
        else:
            self.stdout.write('  - NHIA consulting room already exists')
        
        # General Medicine Consulting Room
        general_room, created = ConsultingRoom.objects.get_or_create(
            room_number='GEN-201',
            defaults={
                'floor': '2nd Floor',
                'department': general_dept,
                'description': 'General Medicine Consultation Room',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Created General Medicine consulting room (GEN-201)'))
        else:
            self.stdout.write('  - General Medicine consulting room already exists')
        
        # Cardiology Consulting Room
        cardiology_room, created = ConsultingRoom.objects.get_or_create(
            room_number='CARD-301',
            defaults={
                'floor': '3rd Floor',
                'department': cardiology_dept,
                'description': 'Cardiology Consultation Room',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Created Cardiology consulting room (CARD-301)'))
        else:
            self.stdout.write('  - Cardiology consulting room already exists')
        
        return nhia_room, general_room, cardiology_room

    def setup_users(self, nhia_dept, general_dept, cardiology_dept):
        """Create test users (doctors and desk office staff)"""
        # NHIA Doctor
        nhia_doctor_user, created = User.objects.get_or_create(
            username='test_nhia_doctor',
            defaults={
                'first_name': 'John',
                'last_name': 'Mensah',
                'email': 'nhia.doctor@test.com',
                'phone_number': '0244111111',
                'is_staff': True,
                'is_active': True
            }
        )
        if created:
            nhia_doctor_user.set_password('test123')
            nhia_doctor_user.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Created NHIA doctor user (test_nhia_doctor / test123)'))
        else:
            self.stdout.write('  - NHIA doctor user already exists')
        
        # Create profile for NHIA doctor
        profile, created = CustomUserProfile.objects.get_or_create(
            user=nhia_doctor_user,
            defaults={
                'department': nhia_dept,
                'role': 'doctor',
                'specialization': 'General Practice'
            }
        )
        
        # General Medicine Doctor
        general_doctor_user, created = User.objects.get_or_create(
            username='test_general_doctor',
            defaults={
                'first_name': 'Sarah',
                'last_name': 'Osei',
                'email': 'general.doctor@test.com',
                'phone_number': '0244222222',
                'is_staff': True,
                'is_active': True
            }
        )
        if created:
            general_doctor_user.set_password('test123')
            general_doctor_user.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Created General Medicine doctor user (test_general_doctor / test123)'))
        else:
            self.stdout.write('  - General Medicine doctor user already exists')
        
        # Create profile for General doctor
        profile, created = CustomUserProfile.objects.get_or_create(
            user=general_doctor_user,
            defaults={
                'department': general_dept,
                'role': 'doctor',
                'specialization': 'General Medicine'
            }
        )
        
        # Cardiology Doctor
        cardiology_doctor_user, created = User.objects.get_or_create(
            username='test_cardiology_doctor',
            defaults={
                'first_name': 'Michael',
                'last_name': 'Asante',
                'email': 'cardiology.doctor@test.com',
                'phone_number': '0244333333',
                'is_staff': True,
                'is_active': True
            }
        )
        if created:
            cardiology_doctor_user.set_password('test123')
            cardiology_doctor_user.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Created Cardiology doctor user (test_cardiology_doctor / test123)'))
        else:
            self.stdout.write('  - Cardiology doctor user already exists')
        
        # Create profile for Cardiology doctor
        profile, created = CustomUserProfile.objects.get_or_create(
            user=cardiology_doctor_user,
            defaults={
                'department': cardiology_dept,
                'role': 'doctor',
                'specialization': 'Cardiology'
            }
        )
        
        # Desk Office Staff
        desk_staff_user, created = User.objects.get_or_create(
            username='test_desk_office',
            defaults={
                'first_name': 'Grace',
                'last_name': 'Boateng',
                'email': 'desk.office@test.com',
                'phone_number': '0244444444',
                'is_staff': True,
                'is_active': True
            }
        )
        if created:
            desk_staff_user.set_password('test123')
            desk_staff_user.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Created Desk Office staff user (test_desk_office / test123)'))
        else:
            self.stdout.write('  - Desk Office staff user already exists')
        
        # Create profile for desk office staff
        admin_dept, _ = Department.objects.get_or_create(
            name='Administration',
            defaults={'description': 'Administration Department'}
        )
        profile, created = CustomUserProfile.objects.get_or_create(
            user=desk_staff_user,
            defaults={
                'department': admin_dept,
                'role': 'admin'
            }
        )
        
        return nhia_doctor_user, general_doctor_user, cardiology_doctor_user, desk_staff_user

    def setup_patients(self):
        """Create test patients (NHIA and Regular)"""
        nhia_patients = []
        regular_patients = []
        
        # Create 3 NHIA test patients
        nhia_patient_data = [
            {'first_name': 'Test NHIA', 'last_name': 'Patient One', 'gender': 'M', 'dob': datetime.strptime('1980-05-15', '%Y-%m-%d').date()},
            {'first_name': 'Test NHIA', 'last_name': 'Patient Two', 'gender': 'F', 'dob': datetime.strptime('1975-08-22', '%Y-%m-%d').date()},
            {'first_name': 'Test NHIA', 'last_name': 'Patient Three', 'gender': 'M', 'dob': datetime.strptime('1990-12-10', '%Y-%m-%d').date()},
        ]
        
        for idx, data in enumerate(nhia_patient_data, 1):
            patient, created = Patient.objects.get_or_create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                defaults={
                    'gender': data['gender'],
                    'date_of_birth': data['dob'],
                    'phone_number': f'0244{idx:06d}',
                    'email': f'nhia.patient{idx}@test.com',
                    'address': f'{idx} Test Street, Accra',
                    'patient_type': 'nhia',
                    'is_active': True
                }
            )
            
            if created:
                # Create NHIA info
                nhia_info, _ = NHIAPatient.objects.get_or_create(
                    patient=patient,
                    defaults={
                        'nhia_reg_number': f'NHIA-TEST-{idx:04d}',
                        'is_active': True
                    }
                )
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created NHIA patient: {patient.get_full_name()} ({patient.patient_id})'))
                nhia_patients.append(patient)
            else:
                self.stdout.write(f'  - NHIA patient already exists: {patient.get_full_name()}')
                nhia_patients.append(patient)
        
        # Create 2 Regular test patients
        regular_patient_data = [
            {'first_name': 'Test Regular', 'last_name': 'Patient One', 'gender': 'F', 'dob': datetime.strptime('1985-03-20', '%Y-%m-%d').date()},
            {'first_name': 'Test Regular', 'last_name': 'Patient Two', 'gender': 'M', 'dob': datetime.strptime('1992-07-14', '%Y-%m-%d').date()},
        ]
        
        for idx, data in enumerate(regular_patient_data, 1):
            patient, created = Patient.objects.get_or_create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                defaults={
                    'gender': data['gender'],
                    'date_of_birth': data['dob'],
                    'phone_number': f'0244{idx+10:06d}',
                    'email': f'regular.patient{idx}@test.com',
                    'address': f'{idx+10} Test Street, Accra',
                    'patient_type': 'regular',
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created Regular patient: {patient.get_full_name()} ({patient.patient_id})'))
                regular_patients.append(patient)
            else:
                self.stdout.write(f'  - Regular patient already exists: {patient.get_full_name()}')
                regular_patients.append(patient)
        
        return nhia_patients, regular_patients

    def display_summary(self, nhia_dept, general_dept, cardiology_dept,
                       nhia_room, general_room, cardiology_room,
                       nhia_doctor, general_doctor, cardiology_doctor, desk_staff,
                       nhia_patients, regular_patients):
        """Display summary of created test data"""
        self.stdout.write('\n' + self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('TEST DATA SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        self.stdout.write('\n' + self.style.WARNING('DEPARTMENTS:'))
        self.stdout.write(f'  • NHIA Department: {nhia_dept.name}')
        self.stdout.write(f'  • General Medicine: {general_dept.name}')
        self.stdout.write(f'  • Cardiology: {cardiology_dept.name}')
        
        self.stdout.write('\n' + self.style.WARNING('CONSULTING ROOMS:'))
        self.stdout.write(f'  • NHIA Room: {nhia_room.room_number} ({nhia_room.department.name})')
        self.stdout.write(f'  • General Room: {general_room.room_number} ({general_room.department.name})')
        self.stdout.write(f'  • Cardiology Room: {cardiology_room.room_number} ({cardiology_room.department.name})')
        
        self.stdout.write('\n' + self.style.WARNING('TEST USERS (All passwords: test123):'))
        self.stdout.write(f'  • NHIA Doctor: {nhia_doctor.username} (Dr. {nhia_doctor.get_full_name()})')
        self.stdout.write(f'  • General Doctor: {general_doctor.username} (Dr. {general_doctor.get_full_name()})')
        self.stdout.write(f'  • Cardiology Doctor: {cardiology_doctor.username} (Dr. {cardiology_doctor.get_full_name()})')
        self.stdout.write(f'  • Desk Office Staff: {desk_staff.username} ({desk_staff.get_full_name()})')
        
        self.stdout.write('\n' + self.style.WARNING('NHIA PATIENTS:'))
        for patient in nhia_patients:
            nhia_reg = patient.nhia_info.nhia_reg_number if hasattr(patient, 'nhia_info') else 'N/A'
            self.stdout.write(f'  • {patient.get_full_name()} (ID: {patient.patient_id}, NHIA: {nhia_reg})')
        
        self.stdout.write('\n' + self.style.WARNING('REGULAR PATIENTS:'))
        for patient in regular_patients:
            self.stdout.write(f'  • {patient.get_full_name()} (ID: {patient.patient_id})')

