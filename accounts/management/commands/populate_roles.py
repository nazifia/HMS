from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import Role


class Command(BaseCommand):
    help = 'Populate HMS system with initial roles and permissions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting HMS role population...'))
        
        # Define roles with their descriptions and hierarchical relationships
        roles_data = [
            {
                'name': 'admin',
                'description': 'System Administrator - Full access to all HMS modules and user management',
                'parent': None,
                'permissions': []  # Admins get all permissions through superuser status
            },
            {
                'name': 'doctor',
                'description': 'Medical Doctor - Access to patient care, consultations, prescriptions, and medical records',
                'parent': None,
                'permissions': [
                    # Patient management
                    'view_patient', 'change_patient',
                    # Appointments
                    'view_appointment', 'change_appointment',
                    # Consultations
                    'add_consultation', 'view_consultation', 'change_consultation',
                    # Prescriptions
                    'add_prescription', 'view_prescription', 'change_prescription',
                    # Lab requests
                    'add_testrequest', 'view_testrequest', 'view_testresult',
                    # Medical records
                    'view_medicalrecord', 'add_medicalrecord', 'change_medicalrecord',
                ]
            },
            {
                'name': 'nurse',
                'description': 'Registered Nurse - Patient care, vitals monitoring, and inpatient management',
                'parent': None,
                'permissions': [
                    # Patient management
                    'view_patient', 'change_patient',
                    # Inpatient care
                    'view_admission', 'change_admission',
                    'add_vitalsign', 'view_vitalsign', 'change_vitalsign',
                    'view_careplan', 'add_careplan', 'change_careplan',
                    # Appointments (view only)
                    'view_appointment',
                    # Basic medical records
                    'view_medicalrecord',
                ]
            },
            {
                'name': 'receptionist',
                'description': 'Front Desk Receptionist - Patient registration, appointment scheduling, and basic billing',
                'parent': None,
                'permissions': [
                    # Patient registration - FULL CRUD
                    'add_patient', 'view_patient', 'change_patient', 'delete_patient',
                    # Medical records - FULL CRUD (MedicalHistory model)
                    'add_medicalhistory', 'view_medicalhistory', 'change_medicalhistory', 'delete_medicalhistory',
                    # Vitals - FULL CRUD
                    'add_vitals', 'view_vitals', 'change_vitals', 'delete_vitals',
                    # Appointments
                    'add_appointment', 'view_appointment', 'change_appointment', 'delete_appointment',
                    # Waiting list management
                    'add_waitinglist', 'view_waitinglist', 'change_waitinglist', 'delete_waitinglist',
                    # Basic billing
                    'add_invoice', 'view_invoice', 'change_invoice',
                    'add_payment', 'view_payment',
                ]
            },
            {
                'name': 'pharmacist',
                'description': 'Licensed Pharmacist - Medication management, prescription dispensing, and inventory control',
                'parent': None,
                'permissions': [
                    # Pharmacy inventory
                    'add_medication', 'view_medication', 'change_medication',
                    'view_medicationcategory', 'add_medicationcategory', 'change_medicationcategory',
                    # Prescriptions - including creation for pharmacy staff
                    'add_prescription', 'view_prescription', 'change_prescription',
                    'add_dispenseditem', 'view_dispenseditem', 'change_dispenseditem',
                    # Pharmacy billing
                    'add_pharmacybill', 'view_pharmacybill', 'change_pharmacybill',
                    # Patient access for prescription creation
                    'view_patient',
                ]
            },
            {
                'name': 'lab_technician',
                'description': 'Laboratory Technician - Lab test management, sample processing, and result entry',
                'parent': None,
                'permissions': [
                    # Lab tests
                    'view_test', 'add_test', 'change_test',
                    'view_testcategory', 'add_testcategory', 'change_testcategory',
                    # Test requests and results
                    'view_testrequest', 'change_testrequest',
                    'add_testresult', 'view_testresult', 'change_testresult',
                    # Sample management
                    'add_sample', 'view_sample', 'change_sample',
                ]
            },
            {
                'name': 'radiology_staff',
                'description': 'Radiology Technician - Imaging services, radiology requests, and report management',
                'parent': None,
                'permissions': [
                    # Radiology
                    'view_radiologyrequest', 'add_radiologyrequest', 'change_radiologyrequest',
                    'view_radiologyresult', 'add_radiologyresult', 'change_radiologyresult',
                    'view_radiologyservice', 'add_radiologyservice', 'change_radiologyservice',
                ]
            },
            {
                'name': 'accountant',
                'description': 'Hospital Accountant - Financial management, billing oversight, and payment processing',
                'parent': None,
                'permissions': [
                    # Billing and payments
                    'view_invoice', 'add_invoice', 'change_invoice', 'delete_invoice',
                    'view_payment', 'add_payment', 'change_payment',
                    'view_service', 'add_service', 'change_service',
                    'view_servicecategory', 'add_servicecategory', 'change_servicecategory',
                    # Financial reports
                    'view_financialreport',
                ]
            },
            {
                'name': 'health_record_officer',
                'description': 'Health Records Officer - Medical records management, patient data, and information systems',
                'parent': None,
                'permissions': [
                    # Patient management - FULL CRUD
                    'add_patient', 'view_patient', 'change_patient', 'delete_patient',
                    # Medical records - FULL CRUD (MedicalHistory model)
                    'add_medicalhistory', 'view_medicalhistory', 'change_medicalhistory', 'delete_medicalhistory',
                    # Vitals - FULL CRUD
                    'add_vitals', 'view_vitals', 'change_vitals', 'delete_vitals',
                    # Appointments
                    'add_appointment', 'view_appointment', 'change_appointment',
                    # Health information
                    'view_consultation', 'view_testrequest', 'view_testresult',
                ]
            },
        ]

        # Create or update roles
        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                name=role_data['name'],
                defaults={
                    'description': role_data['description'],
                    'parent': role_data['parent']
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created role: {role.name}')
                )
            else:
                # Update description if role exists
                role.description = role_data['description']
                role.save()
                self.stdout.write(
                    self.style.WARNING(f'Updated role: {role.name}')
                )
            
            # Assign permissions to role
            if role_data['permissions']:
                permissions = Permission.objects.filter(codename__in=role_data['permissions'])
                role.permissions.set(permissions)
                self.stdout.write(
                    f'  Assigned {permissions.count()} permissions to {role.name}'
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully populated HMS roles!')
        )
        
        # Display summary
        total_roles = Role.objects.count()
        self.stdout.write(f'\nTotal roles in system: {total_roles}')
        
        for role in Role.objects.all():
            user_count = role.customuser_roles.count()
            permission_count = role.permissions.count()
            self.stdout.write(
                f'  {role.name}: {user_count} users, {permission_count} permissions'
            )
