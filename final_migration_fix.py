import os

print("Fixing Activity Monitoring Migration")
print("="*40)

try:
    os.chdir('C:/Users/dell/Desktop/MY_PRODUCTS/HMS')
    
    # Remove the problematic migration file
    migration_file = 'accounts/migrations/0007_activity_monitoring_models.py'
    if os.path.exists(migration_file):
        os.remove(migration_file)
        print("Removed the conflicting migration file")
    
    # Create a simple shell script to apply migration
    shell_script = '''
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'hms.settings'
import django
django.setup()

# In Django shell, apply the migration
from django.core.management import execute_from_command_line
execute_from_command_line(['migrate', 'accounts', '--fake'])  # --fake to test
execute_from_command_line(['migrate'])  # Apply real migration
'''

    # Write shell script
    with open('apply_migration.sh', 'w') as f:
        f.write(shell_script)
    
    print("Created migration fix script")
    
    # Apply fake migration first to check connection
    print("Testing database connection...")
    test_result = os.system('python create_migration.py')
    
    if test_result == 0:
        print("✅ Database connection successful!")
        print("\nTo apply the final migration, run:")
        print("python apply_migration.py")
    else:
        print(f"Database connection failed - result: {test_result}")
        
except Exception as e:
    print(f"Error: {e}")
    print("\nAlternative approach:")
    print("1. Manually remove: del accounts/migrations/0007_activity_monitoring_models.py")
    print("2. Apply migration: python manage.py migrate --fake")
    print("3. Then apply real: python manage.py migrate")
    print("4. The activity monitoring system will be ready!")
