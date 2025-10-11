import os
import subprocess

os.chdir('C:\\Users\\dell\\Desktop\\MY_PRODUCTS\\HMS')

# Remove old migration
if os.path.exists('accounts\\migrations\\0007_activity_monitoring_models.py'):
    os.remove('accounts\\migrations\\migrations\\0007_activity_monitoring_models.py')
    print("Removed conflicting migration")

# Create new migration script
migration_content = '''import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'hms.settings'

import django
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from django.db.migrations import Migration
from django.db import models

class Migration(Migration):
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
'''

with open('accounts\\migrations\\0007_activity_monitoring_models.py', 'w') as f:
    f.write(migration_content)

print("Created migration file, now applying...")

# Run Django shell to apply migration
try:
    from django.core.management import execute_from_command_line
    execute_from_command_line(['shell'])
    
    print("Inside Django shell, applying migration...")
    
    shell_result = execute_from_command_line(['migrate', 'accounts', '0007'])
    print("Shell result:", shell_result.returncode)
    
    if shell_result.returncode == 0:
        print("✅ SUCCESS: Activity monitoring is now ACTIVE!")
        print("All tables created and ready for use.")
    
    execute_from_command_line(['exit'])
    
except Exception as e:
    print(f"Shell error: {e}")
