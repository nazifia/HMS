
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'hms.settings'
import django
django.setup()

# In Django shell, apply the migration
from django.core.management import execute_from_command_line
execute_from_command_line(['migrate', 'accounts', '--fake'])  # --fake to test
execute_from_command_line(['migrate'])  # Apply real migration
