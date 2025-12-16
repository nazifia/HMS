import os

print("Manual Migration Setup for Activity Monitoring")
print("=" * 50)

# Change to project directory
os.chdir('C:\\Users\dell\\Desktop\\MY_PRODUCTS\\HMS')

try:
    # Step 1: Remove conflicting migrations
    migrations_dir = 'accounts\\migrations'
    
    # List migrations in the accounts app
    import os
    migrations = [f for f in os.listdir(migrations_dir) if f.startswith('000')]
    print(f"Found migrations: {migrations}")
    
    # Remove the problematic migration if it exists
    if '0007_activity_monitoring_models.py' in migrations:
        os.remove(os.path.join(migrations_dir, '0007_activity_monitoring_models.py'))
        print(f"✅ Removed conflicting migration: 0007_activity_monitoring_models.py")
    
    # Check if 0006 exists
    if '0006_customuserprofile_updated_at_alter_auditlog_action_and_more.py' not in migrations:
        print("⚠️ Warning: Expected migration 0006 not found. This may cause issues.")
    
    print("Creating fresh migration...")
    
    # Create a new migration file
    migration_file = os.path.join(migrations_dir, '0007_activity_monitoring_models.py')
    with open(migration_file, 'w', encoding='utf-8') as f:
        f.write('''# Generated manual migration for Activity Monitoring
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('accounts', '0006')]

    operations = [
        migrations.CreateModel('UserActivity', [
            ['id', models.BigAutoField(primary_key=True)],
            ['user', models.ForeignKey('accounts.CustomUser', null=True, on_delete=models.deletion.SET_NULL)],
            ['action_type', models.CharField(max_length=20)],
            ['activity_level', models.CharField(max_length=10, default='low')],
            ['description', models.CharField(max_length=500)],
            ['timestamp', models.DateTimeField(auto_now_add=True)],
        ]),
        
        migrations.CreateModel('ActivityAlert', [
            ['id', models.BigAutoField(primary_key=True)],  
            ['user', models.ForeignKey('accounts.CustomUser', null=True, on_delete=models.deletion.SET_NULL)],
            ['alert_type', models.CharField(max_length=30)],
            ['severity', models.CharField(max_length=10)],
            ['message', models.TextField()],
            ['is_resolved', models.BooleanField(default=False)],
            ['created_at', models.DateTimeField(auto_now_add=True)],
        ]),
        
        migrations.CreateModel('UserSession', [
            ['id', models.BigAutoField(primary_key=True)],
            ['user', models.ForeignKey('accounts.CustomUser', null=True, on_delete=models.deletion.CASCADE)],
            ['session_key', models.CharField(max_length=100, unique=True)],
            ['created_at', models.DateTimeField(auto_now_add=True)],
        ]),
    ]
''')

    print(f"✅ Created migration file at: {migration_file}")
    
    print("\nNow applying migration manually...")  
    print("Choose method:")
    
    print("\n=== Option A: Django Shell (RECOMMENDED) ===")
    print("  1. cd C:\\Users\\dell\\Desktop\\MY_PRODUCTS\\HMS")
    print("  2. python manage.py shell")
    print("  3. In shell, run:")
    print("     >>> from django.core.management import execute_from_command_line")
    print("     >>> execute_from_command_line(['migrate', 'accounts'])")
    
    print("\n=== Option B: Direct Migration ===")
    print(" 1. python manage.py migrate --fake (first run to test)")
    print(" 2. python manage.py migrate (final run)")
    print("\n=== ===")
    
    print("\nAfter migration, the activity monitoring system will activate automatically!")
    
    print("\n✅ Ready to use Activity Monitor:")
    print("   - Navigate to: User Management → Activity Monitor")
    print("   - URL: http://127.0.0.1:8000/accounts/activity-dashboard/")
    print()
    
    return True
    
except Exception as e:
    print(f"Error: {e}")
    print("Please try the manual Django shell approach above.")
