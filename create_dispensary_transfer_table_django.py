"""
Create DispensaryTransfer table using Django's schema editor
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.db import connection
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from pharmacy.models import DispensaryTransfer

# Drop existing table
with connection.cursor() as cursor:
    print("Dropping existing table...")
    cursor.execute("DROP TABLE IF EXISTS pharmacy_dispensarytransfer;")
    print("✅ Table dropped")

# Create table using Django's schema editor
print("\nCreating table using Django schema editor...")
with connection.schema_editor() as schema_editor:
    schema_editor.create_model(DispensaryTransfer)
    print("✅ Table created")

# Verify
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(pharmacy_dispensarytransfer);")
    columns = cursor.fetchall()
    print("\nTable structure:")
    for col in columns:
        print(f"  {col[0]}: {col[1]} ({col[2]})")
    
    # Check if to_dispensary_id exists
    column_names = [col[1] for col in columns]
    if 'to_dispensary_id' in column_names:
        print("\n✅ to_dispensary_id column exists!")
    else:
        print("\n❌ to_dispensary_id column is MISSING!")

