import os
import subprocess

print("Simple Migration Fix")
print("=" * 30)

os.chdir('C:\\Users\\dell\\Desktop\\MY_PRODUCTS\\HMS')

# Remove conflicting migration
if os.path.exists('accounts\\migrations\\0007_activity_monitoring_models.py'):
    os.remove('accounts\\migrations\\0007_activity_monitoring_models.py')
    print("Removed conflicting file")

# Create simple migration script
with open('create_migration.py', 'w', encoding='utf-8') as f:
    f.write('''
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = '1'

import django
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

# Create migration
from django.db.migrations import Migration, migrations
from django.db import models

class Migration(Migration):
    dependencies = [('accounts', '0006')]

    operations = [
        migrations.CreateModel('UserActivity', [
            ('id', models.BigAutoField(primary_key=True)),
            ('user', models.ForeignKey('accounts.CustomUser', null=True, on_delete=models.SET_NULL)),
            ('action_type', models.CharField(max_length=20)),
            ('activity_level', models.CharField(max_length=10, default='low')),
            ('description', models.CharField(max_length=500)),
            ('timestamp', models.DateTimeField(auto_now_add=True)),
        ]),
        
        migrations.CreateModel('ActivityAlert', [
            ('id', models.BigAutoField(primary_key=True)),
            ('user', models.ForeignKey('accounts.CustomUser', null=True, on_delete=models.SET_NULL)),
            ('alert_type', models.CharField(max_length=30)),
            ('severity', models.CharField(max_length=10)),
            ('message', models.TextField()),
            ('is_resolved', models.BooleanField(default=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),
        
        migrations.CreateModel('UserSession', [
            ('id', models.BigAutoField(primary_key=True)),
            ('user', models.ForeignKey('accounts.CustomUser', null=True, on_delete=models.CASCADE)),
            ('session_key', models.CharField(max_length=100, unique=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),
    ]

# Save migration
with open('accounts\\migrations\\0007_activity_monitoring_models.py', 'w') as f:
    f.write(open('create_migration.py').read())

# Apply migration  
result = subprocess.run(['manage.py', 'migrate', 'accounts', '0007'])
if result.returncode == 0:
    print("✅ Migration applied successfully!")
else:
    print("⚠ Migration failed, try Django shell")
''')

print("Done!")''
    )

print("Creating and applying migration...")
with open('create_migration.py', 'w') as f:
    f.write('')

print("Creating and applying migration...")
with open('create_migration.py', 'w') as f:
    f.write(open('create_migration.py').read())

result = subprocess.run(['python', 'create_migration.py'])
print(f"Result: {result.returncode}")

if result.returncode == 0:
    print("✅ Success! Activity monitoring is now active.")
else:
    print("\n⚠ Manual approach required:")
    print("1. Remove conflicting: del accounts\\migrations\\0007_activity_monitoring_models.py")
    print("2. Run: python manage.py shell")
    print("3. In shell: from django.core.management import execute_from_command_line")
    print("4. Then: execute_from_command_line(['migrate', 'accounts', '0007'])")
