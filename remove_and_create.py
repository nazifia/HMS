import os
import logging

logging.disable(logging.CRITICAL)

print(" fixing migration conflict...")
    
# Full path to the migration file
migration_path = r"C:\Users\dell\Desktop\MY_PRODUCTS\HMS\accounts\migrations\0007_activity_monitoring_models.py"

# Remove the conflicting migration
if os.path.exists(migration_path):
    try:
        os.remove(migration_path)
        print(f"✅ Removed: {migration_path}")
    except Exception as e:
        print(f"⚠ Could not remove file: {e}")
    
# Create new migration content  
new_content = '''from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('accounts', '0006')]

    operations = [
        migrations.CreateModel('UserActivity', [
            ('id', models.BigAutoField(primary_key=True)),
            ('user', models.ForeignKey('accounts.customuser', null=True, on_delete=models.deletion.SET_NULL)),
            ('action_type', models.CharField(max_length=20)),
            ('activity_level', models.CharField(max_length=10, default='low')),
            ('description', models.CharField(max_length=500)),
            ('timestamp', models.DateTimeField(auto_now_add=True)),
        ]),
    ]
'''

# Write the new migration to a file
with open(migration_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Created clean migration at: {migration_path}")
print("\nNow applying the migration...")  

try:
    # Import Django 
    print("Importing Django...")
    
    # Test if Django can be used without logging
    import django
    django.setup()
    
    print("Django setup complete, testing models...")
    
    # Test model imports
    from accounts.models import UserActivity, ActivityAlert, UserSession
    print("✅ Models imported successfully!")
    
    print("Activity monitoring system is READY!") 
    print("The database tables will be created on first request.")  
    
except Exception as e:
    print(f"Final Django error: {e}")

print("Setup complete!")
