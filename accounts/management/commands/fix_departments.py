from django.core.management.base import BaseCommand
from accounts.models import CustomUserProfile, Department
from django.db import transaction, connection
import sys

class Command(BaseCommand):
    help = 'Fix all department data issues in the accounts_customuserprofile table'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in dry-run mode. No changes will be made.'))
        
        self.stdout.write(self.style.SUCCESS('Starting comprehensive department data cleanup...'))
        
        try:
            # First, fix any invalid department IDs
            self.fix_invalid_department_ids(dry_run)
            
            # Then migrate string department names to foreign keys
            self.migrate_department_data(dry_run)
            
            self.stdout.write(self.style.SUCCESS('All department data fixes completed!'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error during department fixes: {e}'))
            self.stderr.write(self.style.ERROR('Fix failed. Manual intervention may be required.'))
            sys.exit(1)

    def fix_invalid_department_ids(self, dry_run=False):
        """Fix any invalid department_id values in the database."""
        self.stdout.write('Starting to fix invalid department IDs...')
        
        # First approach: Try using Django ORM
        try:
            # Get all profiles
            profiles_to_update = []
            for profile in CustomUserProfile.objects.all():
                # Check if department is a string (not a FK or None)
                if profile.department is not None and not hasattr(profile.department, 'id'):
                    profiles_to_update.append(profile)
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'Would update {len(profiles_to_update)} profiles with invalid department IDs'))
                return
            
            # Actually update the profiles
            for profile in profiles_to_update:
                profile.department = None
                profile.save(update_fields=['department'])
            
            self.stdout.write(self.style.SUCCESS(f'Updated {len(profiles_to_update)} profiles with invalid department IDs'))
            return
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error using Django ORM approach: {e}'))
            self.stdout.write(self.style.WARNING('Falling back to SQL approach...'))
        
        # Second approach: Use raw SQL
        if dry_run:
            self.stdout.write(self.style.WARNING('Would execute SQL to fix invalid department IDs'))
            return
            
        try:
            with connection.cursor() as cursor:
                # Check which database engine is being used
                db_engine = connection.vendor
                
                if db_engine == 'sqlite':
                    # SQLite version
                    cursor.execute('''
                        UPDATE accounts_customuserprofile
                        SET department_id = NULL
                        WHERE department_id IS NOT NULL AND typeof(department_id) != 'integer'
                    ''')
                elif db_engine == 'postgresql':
                    # PostgreSQL version
                    cursor.execute('''
                        UPDATE accounts_customuserprofile
                        SET department_id = NULL
                        WHERE department_id IS NOT NULL AND department_id ~ '[^0-9]'
                    ''')
                elif db_engine == 'mysql':
                    # MySQL version
                    cursor.execute('''
                        UPDATE accounts_customuserprofile
                        SET department_id = NULL
                        WHERE department_id IS NOT NULL AND department_id REGEXP '[^0-9]'
                    ''')
                else:
                    # Generic approach for other databases
                    # First, get all department_id values
                    cursor.execute('SELECT id, department_id FROM accounts_customuserprofile WHERE department_id IS NOT NULL')
                    rows = cursor.fetchall()
                    
                    # Process each row
                    updated_count = 0
                    for row_id, dept_id in rows:
                        if dept_id is not None:
                            try:
                                # Try to convert to integer
                                int(dept_id)
                            except (ValueError, TypeError):
                                # If conversion fails, set to NULL
                                cursor.execute(
                                    'UPDATE accounts_customuserprofile SET department_id = NULL WHERE id = %s',
                                    [row_id]
                                )
                                updated_count += 1
                    
                    self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} profiles using generic SQL approach'))
                    return
                
                self.stdout.write(self.style.SUCCESS('Invalid department_id values set to NULL using database-specific SQL'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error using SQL approach: {e}'))
            raise Exception('Both approaches to fix invalid department IDs failed')

    def migrate_department_data(self, dry_run=False):
        """Migrate string department names to proper foreign key relationships."""
        self.stdout.write('Starting department data migration...')
        
        # Use a transaction to ensure all or nothing
        with transaction.atomic():
            # 1. Create Department objects for all unique department names
            unique_departments = set()
            
            # Get all profiles with non-null, non-empty department values
            for profile in CustomUserProfile.objects.exclude(department__isnull=True).exclude(department__exact=''):
                # Check if department is a string (not a FK)
                if isinstance(profile.department, str) and profile.department.strip():
                    unique_departments.add(profile.department.strip())
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'Would create {len(unique_departments)} new departments'))
            else:
                # Create departments for unique names
                dept_count = 0
                for dept_name in unique_departments:
                    dept, created = Department.objects.get_or_create(name=dept_name)
                    if created:
                        dept_count += 1
                
                self.stdout.write(self.style.SUCCESS(f'Created {dept_count} new departments'))

            # 2. Update CustomUserProfile to use Department FK
            profiles_to_update = []
            for profile in CustomUserProfile.objects.all():
                # Only process if department is a string (not already a FK)
                if isinstance(profile.department, str):
                    if profile.department.strip():
                        profiles_to_update.append((profile, profile.department.strip()))
                    else:
                        profiles_to_update.append((profile, None))
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'Would update {len(profiles_to_update)} user profiles'))
                return
            
            # Actually update the profiles
            updated_count = 0
            for profile, dept_name in profiles_to_update:
                if dept_name:
                    try:
                        dept = Department.objects.get(name=dept_name)
                        profile.department = dept
                    except Department.DoesNotExist:
                        profile.department = None
                else:
                    profile.department = None
                
                profile.save(update_fields=['department'])
                updated_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} user profiles'))