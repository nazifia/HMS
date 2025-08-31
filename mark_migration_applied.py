import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.db import connection
from datetime import datetime

# Mark the migration as applied
cursor = connection.cursor()
cursor.execute(
    "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
    ('pharmacy', '0018_add_surgery_field_to_packorder', datetime.now())
)
print('Migration marked as applied')