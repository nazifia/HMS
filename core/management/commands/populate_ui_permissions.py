"""
Management command to populate default UI permissions for HMS.
This creates UI permission entries for common UI elements across all modules.

Usage:
    python manage.py populate_ui_permissions
    python manage.py populate_ui_permissions --clear  # Clear existing and recreate
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from core.models import UIPermission
from accounts.models import Role


class Command(BaseCommand):
    help = 'Populate default UI permissions for HMS modules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing UI permissions before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing UI permissions...'))
            UIPermission.objects.filter(is_system=False).delete()
            self.stdout.write(self.style.SUCCESS('Cleared non-system UI permissions'))

        self.stdout.write(self.style.MIGRATE_HEADING('Populating UI Permissions...'))

        created_count = 0
        updated_count = 0

        # Define default UI permissions for each module
        ui_permissions_data = self.get_ui_permissions_data()

        for perm_data in ui_permissions_data:
            element_id = perm_data['element_id']

            # Extract many-to-many data before creating/updating
            permission_codenames = perm_data.pop('permission_codenames', [])
            role_names = perm_data.pop('role_names', [])

            ui_perm, created = UIPermission.objects.get_or_create(
                element_id=element_id,
                defaults=perm_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created: {element_id} ({perm_data["element_label"]})')
                )
            else:
                # Update existing permission
                for key, value in perm_data.items():
                    if key not in ['required_permissions', 'required_roles']:
                        setattr(ui_perm, key, value)
                ui_perm.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  ⟳ Updated: {element_id}')
                )

            # Handle many-to-many relationships
            if permission_codenames:
                permissions = Permission.objects.filter(
                    codename__in=permission_codenames
                )
                if permissions.exists():
                    ui_perm.required_permissions.set(permissions)

            if role_names:
                roles = Role.objects.filter(name__in=role_names)
                if roles.exists():
                    ui_perm.required_roles.set(roles)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Successfully populated UI permissions: {created_count} created, {updated_count} updated'
            )
        )

    def get_ui_permissions_data(self):
        """
        Define all default UI permissions for the HMS system.
        This is where you define which UI elements require which permissions/roles.
        """
        return [
            # ============ DASHBOARD MODULE ============
            {
                'element_id': 'menu_dashboard',
                'element_label': 'Dashboard Menu',
                'element_type': 'menu_item',
                'module': 'dashboard',
                'description': 'Main dashboard menu item',
                'url_pattern': 'dashboard:dashboard',
                'icon_class': 'fas fa-tachometer-alt',
                'is_active': True,
                'is_system': True,
                'display_order': 1,
                'permission_codenames': ['view_dashboard'],
            },

            # ============ PATIENT MANAGEMENT MODULE ============
            {
                'element_id': 'menu_patients',
                'element_label': 'Patients Menu',
                'element_type': 'menu_item',
                'module': 'patients',
                'description': 'Patient management menu',
                'url_pattern': 'patients:list',
                'icon_class': 'fas fa-user-injured',
                'is_active': True,
                'is_system': True,
                'display_order': 10,
                'permission_codenames': ['view_patients'],
            },
            {
                'element_id': 'btn_create_patient',
                'element_label': 'Create Patient Button',
                'element_type': 'button',
                'module': 'patients',
                'description': 'Button to create new patient',
                'url_pattern': 'patients:register',
                'icon_class': 'fas fa-plus',
                'is_active': True,
                'is_system': True,
                'display_order': 1,
                'permission_codenames': ['create_patient'],
            },
            {
                'element_id': 'btn_edit_patient',
                'element_label': 'Edit Patient Button',
                'element_type': 'button',
                'module': 'patients',
                'description': 'Button to edit patient information',
                'icon_class': 'fas fa-edit',
                'is_active': True,
                'is_system': True,
                'display_order': 2,
                'permission_codenames': ['edit_patient'],
            },
            {
                'element_id': 'btn_delete_patient',
                'element_label': 'Delete Patient Button',
                'element_type': 'button',
                'module': 'patients',
                'description': 'Button to delete patient record',
                'icon_class': 'fas fa-trash',
                'is_active': True,
                'is_system': True,
                'display_order': 3,
                'permission_codenames': ['delete_patient'],
                'role_names': ['admin'],
            },
            {
                'element_id': 'section_patient_wallet',
                'element_label': 'Patient Wallet Section',
                'element_type': 'section',
                'module': 'patients',
                'description': 'Patient wallet and financial information section',
                'is_active': True,
                'is_system': True,
                'display_order': 4,
                'permission_codenames': ['manage_wallet'],
            },

            # ============ PHARMACY MODULE ============
            {
                'element_id': 'menu_pharmacy',
                'element_label': 'Pharmacy Menu',
                'element_type': 'menu_item',
                'module': 'pharmacy',
                'description': 'Pharmacy management menu',
                'url_pattern': 'pharmacy:dashboard',
                'icon_class': 'fas fa-pills',
                'is_active': True,
                'is_system': True,
                'display_order': 20,
                'permission_codenames': ['view_prescriptions', 'manage_inventory'],
                'role_names': ['pharmacist', 'admin'],
            },
            {
                'element_id': 'btn_dispense_medication',
                'element_label': 'Dispense Medication Button',
                'element_type': 'button',
                'module': 'pharmacy',
                'description': 'Button to dispense medications',
                'icon_class': 'fas fa-prescription-bottle',
                'is_active': True,
                'is_system': True,
                'display_order': 1,
                'permission_codenames': ['dispense_medication'],
                'role_names': ['pharmacist', 'admin'],
            },
            {
                'element_id': 'btn_manage_inventory',
                'element_label': 'Manage Inventory Button',
                'element_type': 'button',
                'module': 'pharmacy',
                'description': 'Button to manage pharmacy inventory',
                'icon_class': 'fas fa-boxes',
                'is_active': True,
                'is_system': True,
                'display_order': 2,
                'permission_codenames': ['manage_inventory'],
                'role_names': ['pharmacist', 'admin'],
            },
            {
                'element_id': 'section_bulk_store',
                'element_label': 'Bulk Store Section',
                'element_type': 'section',
                'module': 'pharmacy',
                'description': 'Bulk store inventory section',
                'is_active': True,
                'is_system': True,
                'display_order': 3,
                'permission_codenames': ['manage_inventory'],
                'role_names': ['pharmacist', 'admin'],
            },

            # ============ LABORATORY MODULE ============
            {
                'element_id': 'menu_laboratory',
                'element_label': 'Laboratory Menu',
                'element_type': 'menu_item',
                'module': 'laboratory',
                'description': 'Laboratory management menu',
                'url_pattern': 'laboratory:dashboard',
                'icon_class': 'fas fa-flask',
                'is_active': True,
                'is_system': True,
                'display_order': 30,
                'permission_codenames': ['view_tests'],
                'role_names': ['lab_technician', 'doctor', 'admin'],
            },
            {
                'element_id': 'btn_create_test',
                'element_label': 'Create Test Request Button',
                'element_type': 'button',
                'module': 'laboratory',
                'description': 'Button to create lab test request',
                'icon_class': 'fas fa-plus',
                'is_active': True,
                'is_system': True,
                'display_order': 1,
                'permission_codenames': ['create_test_request'],
                'role_names': ['doctor', 'admin'],
            },
            {
                'element_id': 'btn_enter_results',
                'element_label': 'Enter Results Button',
                'element_type': 'button',
                'module': 'laboratory',
                'description': 'Button to enter lab test results',
                'icon_class': 'fas fa-keyboard',
                'is_active': True,
                'is_system': True,
                'display_order': 2,
                'permission_codenames': ['enter_results'],
                'role_names': ['lab_technician', 'admin'],
            },

            # ============ BILLING MODULE ============
            {
                'element_id': 'menu_billing',
                'element_label': 'Billing Menu',
                'element_type': 'menu_item',
                'module': 'billing',
                'description': 'Billing and payments menu',
                'url_pattern': 'billing:dashboard',
                'icon_class': 'fas fa-file-invoice-dollar',
                'is_active': True,
                'is_system': True,
                'display_order': 40,
                'permission_codenames': ['view_invoices'],
                'role_names': ['accountant', 'receptionist', 'admin'],
            },
            {
                'element_id': 'btn_create_invoice',
                'element_label': 'Create Invoice Button',
                'element_type': 'button',
                'module': 'billing',
                'description': 'Button to create new invoice',
                'icon_class': 'fas fa-plus',
                'is_active': True,
                'is_system': True,
                'display_order': 1,
                'permission_codenames': ['create_invoice'],
                'role_names': ['accountant', 'receptionist', 'admin'],
            },
            {
                'element_id': 'btn_process_payment',
                'element_label': 'Process Payment Button',
                'element_type': 'button',
                'module': 'billing',
                'description': 'Button to process payments',
                'icon_class': 'fas fa-money-bill-wave',
                'is_active': True,
                'is_system': True,
                'display_order': 2,
                'permission_codenames': ['process_payments'],
                'role_names': ['accountant', 'admin'],
            },
            {
                'element_id': 'section_financial_reports',
                'element_label': 'Financial Reports Section',
                'element_type': 'section',
                'module': 'billing',
                'description': 'Financial reports and analytics',
                'is_active': True,
                'is_system': True,
                'display_order': 3,
                'permission_codenames': ['view_financial_reports'],
                'role_names': ['accountant', 'admin'],
            },

            # ============ APPOINTMENTS MODULE ============
            {
                'element_id': 'menu_appointments',
                'element_label': 'Appointments Menu',
                'element_type': 'menu_item',
                'module': 'appointments',
                'description': 'Appointment scheduling menu',
                'url_pattern': 'appointments:list',
                'icon_class': 'fas fa-calendar-alt',
                'is_active': True,
                'is_system': True,
                'display_order': 50,
                'permission_codenames': ['view_appointments'],
            },
            {
                'element_id': 'btn_create_appointment',
                'element_label': 'Create Appointment Button',
                'element_type': 'button',
                'module': 'appointments',
                'description': 'Button to create new appointment',
                'icon_class': 'fas fa-plus',
                'is_active': True,
                'is_system': True,
                'display_order': 1,
                'permission_codenames': ['create_appointment'],
            },

            # ============ USER MANAGEMENT MODULE ============
            {
                'element_id': 'menu_users',
                'element_label': 'User Management Menu',
                'element_type': 'menu_item',
                'module': 'accounts',
                'description': 'User and role management menu',
                'url_pattern': 'accounts:user_dashboard',
                'icon_class': 'fas fa-users',
                'is_active': True,
                'is_system': True,
                'display_order': 90,
                'permission_codenames': ['view_users'],
                'role_names': ['admin'],
            },
            {
                'element_id': 'btn_create_user',
                'element_label': 'Create User Button',
                'element_type': 'button',
                'module': 'accounts',
                'description': 'Button to create new user',
                'icon_class': 'fas fa-user-plus',
                'is_active': True,
                'is_system': True,
                'display_order': 1,
                'permission_codenames': ['create_user'],
                'role_names': ['admin'],
            },
            {
                'element_id': 'btn_manage_roles',
                'element_label': 'Manage Roles Button',
                'element_type': 'button',
                'module': 'accounts',
                'description': 'Button to manage user roles',
                'icon_class': 'fas fa-user-tag',
                'is_active': True,
                'is_system': True,
                'display_order': 2,
                'permission_codenames': ['manage_roles'],
                'role_names': ['admin'],
            },
            {
                'element_id': 'modal_delete_user',
                'element_label': 'Delete User Modal',
                'element_type': 'modal',
                'module': 'accounts',
                'description': 'Modal for deleting users',
                'is_active': True,
                'is_system': True,
                'display_order': 3,
                'permission_codenames': ['delete_user'],
                'role_names': ['admin'],
            },

            # ============ REPORTS MODULE ============
            {
                'element_id': 'menu_reports',
                'element_label': 'Reports Menu',
                'element_type': 'menu_item',
                'module': 'reports',
                'description': 'Reports and analytics menu',
                'url_pattern': 'reports:dashboard',
                'icon_class': 'fas fa-chart-bar',
                'is_active': True,
                'is_system': True,
                'display_order': 80,
                'permission_codenames': ['view_reports'],
            },
            {
                'element_id': 'btn_generate_report',
                'element_label': 'Generate Report Button',
                'element_type': 'button',
                'module': 'reports',
                'description': 'Button to generate custom reports',
                'icon_class': 'fas fa-file-export',
                'is_active': True,
                'is_system': True,
                'display_order': 1,
                'permission_codenames': ['generate_reports'],
                'role_names': ['admin', 'accountant'],
            },
            {
                'element_id': 'btn_export_data',
                'element_label': 'Export Data Button',
                'element_type': 'button',
                'module': 'reports',
                'description': 'Button to export system data',
                'icon_class': 'fas fa-download',
                'is_active': True,
                'is_system': True,
                'display_order': 2,
                'permission_codenames': ['export_data'],
                'role_names': ['admin'],
            },

            # ============ RADIOLOGY MODULE ============
            {
                'element_id': 'menu_radiology',
                'element_label': 'Radiology Menu',
                'element_type': 'menu_item',
                'module': 'radiology',
                'description': 'Radiology management menu',
                'url_pattern': 'radiology:index',
                'icon_class': 'fas fa-x-ray',
                'is_active': True,
                'is_system': True,
                'display_order': 40,
                'role_names': ['radiology_staff', 'doctor', 'admin'],
            },
            {
                'element_id': 'btn_create_radiology_request',
                'element_label': 'Create Radiology Request',
                'element_type': 'button',
                'module': 'radiology',
                'description': 'Button to create radiology test request',
                'icon_class': 'fas fa-plus',
                'is_active': True,
                'is_system': True,
                'display_order': 1,
                'permission_codenames': ['create_radiology_request'],
                'role_names': ['doctor', 'admin'],
            },

            # ============ THEATRE MODULE ============
            {
                'element_id': 'menu_theatre',
                'element_label': 'Theatre Menu',
                'element_type': 'menu_item',
                'module': 'theatre',
                'description': 'Theatre/Surgery management menu',
                'url_pattern': 'theatre:dashboard',
                'icon_class': 'fas fa-hospital-symbol',
                'is_active': True,
                'is_system': True,
                'display_order': 50,
                'role_names': ['doctor', 'nurse', 'admin'],
            },
            {
                'element_id': 'btn_schedule_surgery',
                'element_label': 'Schedule Surgery Button',
                'element_type': 'button',
                'module': 'theatre',
                'description': 'Button to schedule a new surgery',
                'icon_class': 'fas fa-calendar-plus',
                'is_active': True,
                'is_system': True,
                'display_order': 1,
                'permission_codenames': ['schedule_surgery'],
                'role_names': ['doctor', 'admin'],
            },
            {
                'element_id': 'btn_manage_theatres',
                'element_label': 'Manage Theatres Button',
                'element_type': 'button',
                'module': 'theatre',
                'description': 'Button to manage operation theatres',
                'icon_class': 'fas fa-door-open',
                'is_active': True,
                'is_system': True,
                'display_order': 2,
                'role_names': ['admin'],
            },
        ]
