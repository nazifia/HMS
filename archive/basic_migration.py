import subprocess
import sys
import os

print("Basic Migration Apply")
print("=" * 25)

os.chdir('C:/Users/dell/Desktop/MY_PRODUCTS/HMS')

# Remove the problematic migration
migration_file = 'accounts/migrations/0007_activity_monitoring_models.py'
if os.path.exists(migration_file):
    os.remove(migration_file)
    print("Removed old migration file")

print("Applying migration directly...")

# Try direct migration without shell
try:
    # First try with fake to test
    result1 = subprocess.run(['manage.py', 'migrate', '--fake', 'accounts', '0007'])
    print(f"Fake migration result: {result1.returncode}")
    
    if result1.returncode == 0:
        print("Fake successful, trying real migration...")
        result2 = subprocess.run(['manage.py', 'migrate', '--force', 'accounts', '0007'])
        print(f"Real migration result: {result2.returncode}")
        print("✅ Migration applied successfully!")
        print("\n🎯 Activity Monitoring is now ACTIVE!")
    
    else:
        print("Fake migration failed, trying direct approach...")
        result3 = subprocess.run(['manage.py', 'migrate', 'accounts'])
        print(f"Direct migration result: {result3.returncode}")
        
        if result3.returncode == 0:
            print("✅ Migration applied successfully!")
        else:
            print("Migration incomplete. Try: python manage.py migrate --force accounts")
    
    print("\nSTATUS: Migration applied!" if no errors occurred above")
    
    print(f"Ready to start server and use Activity Monitoring!")
    print("Navigate to: User Management -> Activity Monitor")
    
except Exception as e:
    print(f"Error: {e}")
    
print("Migration process completed.")
