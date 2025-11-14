from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from core.models import HMSPermission, SidebarMenuItem, FeatureFlag

class Command(BaseCommand):
    help = 'Sync HMS Custom Permissions and create default sidebar menu items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing permissions before syncing',
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting HMS Custom Permission sync...")
        
        if options['clear']:
            self.stdout.write("Clearing existing permissions...")
            HMSPermission.objects.all().delete()
            SidebarMenuItem.objects.all().delete()
            FeatureFlag.objects.all().delete()
        
        # Create HMS Permission content type
        hms_content_type, created = ContentType.objects.get_or_create(
            app_label='hms',
            model='custompermission',
            defaults={'name': 'Custom Permission'}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created HMS content type: {hms_content_type}"))
        
        # Define HMS Custom Permissions
        permissions_data = [
            # Dashboard permissions
            {
                'name': 'View Dashboard',
                'codename': 'view_dashboard',
                'description': 'Access to the main dashboard and system overview',
                'category': 'dashboard'
            },
            
            # Patient Management permissions
            {
                'name': 'View Patients',
                'codename': 'view_patients',
                'description': 'View patient list and details',
                'category': 'patient_management'
            },
            {
                'name': 'Create Patient',
                'codename': 'create_patient',
                'description': 'Register new patients in the system',
                'category': 'patient_management'
            },
            {
                'name': 'Edit Patient',
                'codename': 'edit_patient',
                'description': 'Edit existing patient information',
                'category': 'patient_management'
            },
            {
                'name': 'Delete Patient',
                'codename': 'delete_patient',
                'description': 'Delete patient records',
                'category': 'patient_management'
            },
            {
                'name': 'Access Sensitive Data',
                'codename': 'access_sensitive_data',
                'description': 'Access sensitive patient medical history and data',
                'category': 'medical_records'
            },
            {
                'name': 'Manage Patient Admission',
                'codename': 'manage_patient_admission',
                'description': 'Manage patient admission processes',
                'category': 'patient_management'
            },
            {
                'name': 'Manage Patient Discharge',
                'codename': 'manage_patient_discharge',
                'description': 'Manage patient discharge processes',
                'category': 'patient_management'
            },
            
            # Medical Records permissions
            {
                'name': 'View Medical Records',
                'codename': 'view_medical_records',
                'description': 'View patient medical records and history',
                'category': 'medical_records'
            },
            {
                'name': 'Create Medical Record',
                'codename': 'create_medical_record',
                'description': 'Create new medical records',
                'category': 'medical_records'
            },
            {
                'name': 'Edit Medical Record',
                'codename': 'edit_medical_record',
                'description': 'Edit existing medical records',
                'category': 'medical_records'
            },
            {
                'name': 'Manage Vitals',
                'codename': 'manage_vitals',
                'description': 'Record and manage patient vital signs',
                'category': 'medical_records'
            },
            
            # Consultation permissions
            {
                'name': 'View Consultations',
                'codename': 'view_consultations',
                'description': 'View consultation history and details',
                'category': 'consultations'
            },
            {
                'name': 'Create Consultation',
                'codename': 'create_consultation',
                'description': 'Create new consultations',
                'category': 'consultations'
            },
            {
                'name': 'Edit Consultation',
                'codename': 'edit_consultation',
                'description': 'Edit existing consultations',
                'category': 'consultations'
            },
            {
                'name': 'View Referrals',
                'codename': 'view_referrals',
                'description': 'View patient referrals',
                'category': 'consultations'
            },
            {
                'name': 'Create Referral',
                'codename': 'create_referral',
                'description': 'Create patient referrals',
                'category': 'consultations'
            },
            {
                'name': 'Edit Referral',
                'codename': 'edit_referral',
                'description': 'Edit existing referrals',
                'category': 'consultations'
            },
            
            # Pharmacy permissions
            {
                'name': 'View Pharmacy',
                'codename': 'view_pharmacy',
                'description': 'View pharmacy operations and inventory',
                'category': 'pharmacy'
            },
            {
                'name': 'Manage Pharmacy Inventory',
                'codename': 'manage_pharmacy_inventory',
                'description': 'Manage pharmacy inventory and stock',
                'category': 'pharmacy'
            },
            {
                'name': 'Dispense Medication',
                'codename': 'dispense_medication',
                'description': 'Dispense medications to patients',
                'category': 'pharmacy'
            },
            {
                'name': 'View Prescriptions',
                'codename': 'view_prescriptions',
                'description': 'View prescription history and details',
                'category': 'pharmacy'
            },
            {
                'name': 'Create Prescription',
                'codename': 'create_prescription',
                'description': 'Create new prescriptions',
                'category': 'pharmacy'
            },
            {
                'name': 'Edit Prescription',
                'codename': 'edit_prescription',
                'description': 'Edit existing prescriptions',
                'category': 'pharmacy'
            },
            {
                'name': 'Manage Dispensary',
                'codename': 'manage_dispensary',
                'description': 'Manage dispensary operations',
                'category': 'pharmacy'
            },
            {
                'name': 'Transfer Medication',
                'codename': 'transfer_medication',
                'description': 'Transfer medication between dispensaries',
                'category': 'pharmacy'
            },
            
            # Laboratory permissions
            {
                'name': 'View Laboratory',
                'codename': 'view_laboratory',
                'description': 'View laboratory tests and results',
                'category': 'laboratory'
            },
            {
                'name': 'Create Lab Test',
                'codename': 'create_lab_test',
                'description': 'Create laboratory test requests',
                'category': 'laboratory'
            },
            {
                'name': 'Enter Lab Results',
                'codename': 'enter_lab_results',
                'description': 'Enter laboratory test results',
                'category': 'laboratory'
            },
            {
                'name': 'Edit Lab Results',
                'codename': 'edit_lab_results',
                'description': 'Edit existing laboratory results',
                'category': 'laboratory'
            },
            {
                'name': 'View Laboratory Reports',
                'codename': 'view_laboratory_reports',
                'description': 'View laboratory report dashboard',
                'category': 'reports'
            },
            
            # Radiology permissions
            {
                'name': 'View Radiology',
                'codename': 'view_radiology',
                'description': 'View radiology requests and results',
                'category': 'radiology'
            },
            {
                'name': 'Create Radiology Request',
                'codename': 'create_radiology_request',
                'description': 'Create radiology imaging requests',
                'category': 'radiology'
            },
            {
                'name': 'Enter Radiology Results',
                'codename': 'enter_radiology_results',
                'description': 'Enter radiology imaging results',
                'category': 'radiology'
            },
            {
                'name': 'Edit Radiology Results',
                'codename': 'edit_radiology_results',
                'description': 'Edit existing radiology results',
                'category': 'radiology'
            },
            
            # Appointment permissions
            {
                'name': 'View Appointments',
                'codename': 'view_appointments',
                'description': 'View appointment schedules and details',
                'category': 'appointments'
            },
            {
                'name': 'Create Appointment',
                'codename': 'create_appointment',
                'description': 'Schedule new appointments',
                'category': 'appointments'
            },
            {
                'name': 'Edit Appointment',
                'codename': 'edit_appointment',
                'description': 'Edit existing appointments',
                'category': 'appointments'
            },
            {
                'name': 'Cancel Appointment',
                'codename': 'cancel_appointment',
                'description': 'Cancel appointments',
                'category': 'appointments'
            },
            
            # Inpatient permissions
            {
                'name': 'View Inpatient Records',
                'codename': 'view_inpatient_records',
                'description': 'View inpatient records and information',
                'category': 'inpatient'
            },
            {
                'name': 'Manage Admission',
                'codename': 'manage_admission',
                'description': 'Manage patient admissions',
                'category': 'inpatient'
            },
            {
                'name': 'Manage Discharge',
                'codename': 'manage_discharge',
                'description': 'Manage patient discharge',
                'category': 'inpatient'
            },
            
            # Billing permissions
            {
                'name': 'View Invoices',
                'codename': 'view_invoices',
                'description': 'View billing invoices and financial records',
                'category': 'billing'
            },
            {
                'name': 'Create Invoice',
                'codename': 'create_invoice',
                'description': 'Create new invoices',
                'category': 'billing'
            },
            {
                'name': 'Edit Invoice',
                'codename': 'edit_invoice',
                'description': 'Edit existing invoices',
                'category': 'billing'
            },
            {
                'name': 'Process Payments',
                'codename': 'process_payments',
                'description': 'Process patient payments and receipts',
                'category': 'billing'
            },
            {
                'name': 'Manage Wallet',
                'codename': 'manage_wallet',
                'description': 'Manage patient wallet operations',
                'category': 'billing'
            },
            {
                'name': 'View Financial Reports',
                'codename': 'view_financial_reports',
                'description': 'View financial reports and analytics',
                'category': 'reports'
            },
            
            # User Management permissions
            {
                'name': 'View User Management',
                'codename': 'view_user_management',
                'description': 'Access user and role management areas',
                'category': 'administration'
            },
            {
                'name': 'Create User',
                'codename': 'create_user',
                'description': 'Create new system users',
                'category': 'administration'
            },
            {
                'name': 'Edit User',
                'codename': 'edit_user',
                'description': 'Edit existing user accounts',
                'category': 'administration'
            },
            {
                'name': 'Delete User',
                'codename': 'delete_user',
                'description': 'Delete user accounts',
                'category': 'administration'
            },
            {
                'name': 'Manage Roles',
                'codename': 'manage_roles',
                'description': 'Assign and manage user roles',
                'category': 'administration'
            },
            {
                'name': 'Reset Password',
                'codename': 'reset_password',
                'description': 'Reset user passwords',
                'category': 'administration'
            },
            
            # Reports permissions
            {
                'name': 'View Reports',
                'codename': 'view_reports',
                'description': 'View system reports and analytics',
                'category': 'reports'
            },
            {
                'name': 'Generate Reports',
                'codename': 'generate_reports',
                'description': 'Generate custom reports',
                'category': 'reports'
            },
            {
                'name': 'Export Data',
                'codename': 'export_data',
                'description': 'Export data from the system',
                'category': 'reports'
            },
            {
                'name': 'View Analytics',
                'codename': 'view_analytics',
                'description': 'View system analytics and dashboards',
                'category': 'reports'
            },
            
            # System Administration permissions
            {
                'name': 'System Configuration',
                'codename': 'system_configuration',
                'description': 'Configure system settings',
                'category': 'administration'
            },
            {
                'name': 'Manage Departments',
                'codename': 'manage_departments',
                'description': 'Manage hospital departments',
                'category': 'administration'
            },
            {
                'name': 'View Audit Logs',
                'codename': 'view_audit_logs',
                'description': 'View system audit logs',
                'category': 'administration'
            },
            {
                'name': 'Backup Data',
                'codename': 'backup_data',
                'description': 'Perform system backups',
                'category': 'administration'
            },
            {
                'name': 'System Maintenance',
                'codename': 'system_maintenance',
                'description': 'Perform system maintenance tasks',
                'category': 'administration'
            },
        ]
        
        # Create permissions
        created_count = 0
        for perm_data in permissions_data:
            permission, created = HMSPermission.objects.get_or_create(
                codename=perm_data['codename'],
                defaults={
                    'name': perm_data['name'],
                    'display_name': perm_data['name'],
                    'description': perm_data['description'],
                    'category': perm_data['category'],
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"Created permission: {permission.display_name}")
            
            # Also create Django permission for compatibility
            django_perm, django_created = Permission.objects.get_or_create(
                codename=perm_data['codename'],
                content_type=hms_content_type,
                defaults={
                    'name': perm_data['description'][:230],  # Django limit
                }
            )
            
            if django_created:
                self.stdout.write(f"Created Django permission: {django_perm.name}")
        
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} new HMS permissions"))
        
        # Create sidebar menu items
        self.create_sidebar_menu_items()
        
        # Create feature flags
        self.create_feature_flags()
        
        self.stdout.write(self.style.SUCCESS("HMS Custom Permission sync completed successfully!"))

    def create_sidebar_menu_items(self):
        """Create default sidebar menu items with permissions"""
        self.stdout.write("Creating sidebar menu items...")
        
        menu_items_data = [
            {
                'title': 'Dashboard',
                'url_name': 'dashboard:dashboard',
                'icon': 'fas fa-tachometer-alt',
                'category': 'main',
                'permission_required': 'view_dashboard',
                'order': 1,
            },
            {
                'title': 'Access Control',
                'url_name': '',
                'icon': 'fas fa-shield-alt',
                'category': 'administration',
                'permission_required': 'view_user_management',
                'order': 2,
            },
            {
                'title': 'Manage Roles',
                'url_name': 'accounts:role_management',
                'icon': 'fas fa-users-cog',
                'category': 'administration',
                'permission_required': 'manage_roles',
                'parent_title': 'Access Control',
                'order': 1,
            },
            {
                'title': 'Create Role',
                'url_name': 'accounts:create_role',
                'icon': 'fas fa-user-plus',
                'category': 'administration',
                'permission_required': 'manage_roles',
                'parent_title': 'Access Control',
                'order': 2,
            },
            {
                'title': 'Permissions',
                'url_name': 'accounts:permission_management',
                'icon': 'fas fa-key',
                'category': 'administration',
                'permission_required': 'manage_roles',
                'parent_title': 'Access Control',
                'order': 3,
            },
            {
                'title': 'Patients',
                'url_name': '',
                'icon': 'fas fa-user-injured',
                'category': 'patient_care',
                'permission_required': 'view_patients',
                'order': 3,
            },
            {
                'title': 'All Patients',
                'url_name': 'patients:list',
                'icon': 'fas fa-list',
                'category': 'patient_care',
                'permission_required': 'view_patients',
                'parent_title': 'Patients',
                'order': 1,
            },
            {
                'title': 'Register Patient',
                'url_name': 'patients:register',
                'icon': 'fas fa-user-plus',
                'category': 'patient_care',
                'permission_required': 'create_patient',
                'parent_title': 'Patients',
                'order': 2,
            },
            {
                'title': 'Consultations',
                'url_name': '',
                'icon': 'fas fa-comments',
                'category': 'patient_care',
                'permission_required': 'access_sensitive_data',
                'order': 4,
            },
            {
                'title': 'All Consultations',
                'url_name': 'consultations:consultation_list',
                'icon': 'fas fa-list',
                'category': 'patient_care',
                'permission_required': 'view_consultations',
                'parent_title': 'Consultations',
                'order': 1,
            },
            {
                'title': 'Create Consultation',
                'url_name': 'consultations:patient_list',
                'icon': 'fas fa-plus',
                'category': 'patient_care',
                'permission_required': 'create_consultation',
                'parent_title': 'Consultations',
                'order': 2,
            },
            {
                'title': 'Referrals',
                'url_name': 'consultations:referral_list',
                'icon': 'fas fa-exchange-alt',
                'category': 'patient_care',
                'permission_required': 'view_referrals',
                'parent_title': 'Consultations',
                'order': 3,
            },
            {
                'title': 'Appointments',
                'url_name': '',
                'icon': 'fas fa-calendar-check',
                'category': 'patient_care',
                'permission_required': 'view_appointments',
                'order': 5,
            },
            {
                'title': 'All Appointments',
                'url_name': 'appointments:list',
                'icon': 'fas fa-list',
                'category': 'patient_care',
                'permission_required': 'view_appointments',
                'parent_title': 'Appointments',
                'order': 1,
            },
            {
                'title': 'Schedule Appointment',
                'url_name': 'appointments:create',
                'icon': 'fas fa-plus',
                'category': 'patient_care',
                'permission_required': 'create_appointment',
                'parent_title': 'Appointments',
                'order': 2,
            },
            {
                'title': 'Pharmacy',
                'url_name': '',
                'icon': 'fas fa-pills',
                'category': 'medical_services',
                'permission_required': 'view_pharmacy',
                'order': 6,
            },
            {
                'title': 'Prescriptions',
                'url_name': 'pharmacy:prescriptions',
                'icon': 'fas fa-prescription',
                'category': 'medical_services',
                'permission_required': 'view_prescriptions',
                'parent_title': 'Pharmacy',
                'order': 1,
            },
            {
                'title': 'Inventory',
                'url_name': 'pharmacy:inventory',
                'icon': 'fas fa-boxes',
                'category': 'medical_services',
                'permission_required': 'manage_pharmacy_inventory',
                'parent_title': 'Pharmacy',
                'order': 2,
            },
            {
                'title': 'Laboratory',
                'url_name': '',
                'icon': 'fas fa-flask',
                'category': 'medical_services',
                'permission_required': 'view_laboratory',
                'order': 7,
            },
            {
                'title': 'Lab Tests',
                'url_name': 'laboratory:tests',
                'icon': 'fas fa-microscope',
                'category': 'medical_services',
                'permission_required': 'view_laboratory',
                'parent_title': 'Laboratory',
                'order': 1,
            },
            {
                'title': 'Test Requests',
                'url_name': 'laboratory:test_requests',
                'icon': 'fas fa-vial',
                'category': 'medical_services',
                'permission_required': 'create_lab_test',
                'parent_title': 'Laboratory',
                'order': 2,
            },
            {
                'title': 'Billing',
                'url_name': '',
                'icon': 'fas fa-file-invoice-dollar',
                'category': 'administration',
                'permission_required': 'view_invoices',
                'order': 8,
            },
            {
                'title': 'Invoices',
                'url_name': 'billing:list',
                'icon': 'fas fa-file-invoice',
                'category': 'administration',
                'permission_required': 'view_invoices',
                'parent_title': 'Billing',
                'order': 1,
            },
            {
                'title': 'Create Invoice',
                'url_name': 'billing:create',
                'icon': 'fas fa-plus-circle',
                'category': 'administration',
                'permission_required': 'create_invoice',
                'parent_title': 'Billing',
                'order': 2,
            },
            {
                'title': 'Reports',
                'url_name': '',
                'icon': 'fas fa-chart-bar',
                'category': 'administration',
                'permission_required': 'view_reports',
                'order': 9,
            },
            {
                'title': 'System Reports',
                'url_name': 'reporting:pharmacy_sales_report',
                'icon': 'fas fa-chart-line',
                'category': 'administration',
                'permission_required': 'view_reports',
                'parent_title': 'Reports',
                'order': 1,
            },
            {
                'title': 'Laboratory Reports',
                'url_name': 'laboratory:laboratory_sales_report',
                'icon': 'fas fa-flask',
                'category': 'administration',
                'permission_required': 'view_laboratory_reports',
                'parent_title': 'Reports',
                'order': 2,
            },
        ]
        
        created_count = 0
        for item_data in menu_items_data:
            permission_required = None
            if item_data.get('permission_required'):
                try:
                    permission_required = HMSPermission.objects.get(codename=item_data['permission_required'])
                except HMSPermission.DoesNotExist:
                    self.stdout.write(f"Warning: Permission {item_data['permission_required']} not found")
            
            parent = None
            if item_data.get('parent_title'):
                try:
                    parent = SidebarMenuItem.objects.get(title=item_data['parent_title'])
                except SidebarMenuItem.DoesNotExist:
                    self.stdout.write(f"Warning: Parent menu item {item_data['parent_title']} not found")
            
            menu_item, created = SidebarMenuItem.objects.get_or_create(
                title=item_data['title'],
                defaults={
                    'url_name': item_data['url_name'],
                    'icon': item_data['icon'],
                    'category': item_data['category'],
                    'permission_required': permission_required,
                    'parent': parent,
                    'order': item_data['order'],
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"Created menu item: {menu_item.title}")
        
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} sidebar menu items"))

    def create_feature_flags(self):
        """Create default feature flags"""
        self.stdout.write("Creating feature flags...")
        
        feature_flags_data = [
            {
                'name': 'Enhanced Pharmacy Workflow',
                'display_name': 'Enhanced Pharmacy Workflow',
                'description': 'Enable advanced pharmacy cart and dispensing workflow',
                'feature_type': 'module',
                'permission_required': 'manage_pharmacy_inventory',
            },
            {
                'name': 'Advanced Reporting',
                'display_name': 'Advanced Reporting Module',
                'description': 'Enable advanced reporting and analytics features',
                'feature_type': 'module',
                'permission_required': 'view_analytics',
            },
            {
                'name': 'NHIA Integration',
                'display_name': 'NHIA Integration Features',
                'description': 'Enable NHIA authorization and billing features',
                'feature_type': 'module',
                'permission_required': 'access_sensitive_data',
            },
            {
                'name': 'Bulk Operations',
                'display_name': 'Bulk Operations',
                'description': 'Enable bulk patient and data operations',
                'feature_type': 'feature',
                'permission_required': 'manage_roles',
            },
            {
                'name': 'Audit Trail',
                'display_name': 'Audit Trail Access',
                'description': 'Enable access to system audit logs',
                'feature_type': 'feature',
                'permission_required': 'view_audit_logs',
            },
        ]
        
        created_count = 0
        for flag_data in feature_flags_data:
            permission_required = None
            if flag_data.get('permission_required'):
                try:
                    permission_required = HMSPermission.objects.get(codename=flag_data['permission_required'])
                except HMSPermission.DoesNotExist:
                    self.stdout.write(f"Warning: Permission {flag_data['permission_required']} not found")
            
            feature_flag, created = FeatureFlag.objects.get_or_create(
                name=flag_data['name'],
                defaults={
                    'display_name': flag_data['display_name'],
                    'description': flag_data['description'],
                    'feature_type': flag_data['feature_type'],
                    'permission_required': permission_required,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"Created feature flag: {feature_flag.display_name}")
        
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} feature flags"))
