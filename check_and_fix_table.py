#!/usr/bin/env python
"""Check and fix SurgeryTypeEquipment table"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
os.environ['DJANGO_COLORS'] = 'nocolor'
os.environ['NO_COLOR'] = '1'

import django
django.setup()

from django.db import connection

print("Checking database tables...")

with connection.cursor() as cursor:
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='theatre_surgerytypeequipment';")
    result = cursor.fetchone()
    
    if result:
        print("✓ Table 'theatre_surgerytypeequipment' exists")
    else:
        print("✗ Table 'theatre_surgerytypeequipment' does NOT exist")
        print("\nCreating table manually...")
        
        try:
            cursor.execute("""
                CREATE TABLE "theatre_surgerytypeequipment" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "quantity_required" integer unsigned NOT NULL CHECK ("quantity_required" >= 0),
                    "is_mandatory" bool NOT NULL,
                    "notes" text NULL,
                    "created_at" datetime NOT NULL,
                    "updated_at" datetime NOT NULL,
                    "equipment_id" bigint NOT NULL REFERENCES "theatre_surgicalequipment" ("id") DEFERRABLE INITIALLY DEFERRED,
                    "surgery_type_id" bigint NOT NULL REFERENCES "theatre_surgerytype" ("id") DEFERRABLE INITIALLY DEFERRED
                );
            """)
            
            # Create unique constraint
            cursor.execute("""
                CREATE UNIQUE INDEX "theatre_surgerytypeequipment_surgery_type_id_equipment_id_uniq" 
                ON "theatre_surgerytypeequipment" ("surgery_type_id", "equipment_id");
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX "theatre_surgerytypeequipment_equipment_id_8f5f5f8f" 
                ON "theatre_surgerytypeequipment" ("equipment_id");
            """)
            
            cursor.execute("""
                CREATE INDEX "theatre_surgerytypeequipment_surgery_type_id_30a29a7a" 
                ON "theatre_surgerytypeequipment" ("surgery_type_id");
            """)
            
            # Update django_migrations to mark as applied
            cursor.execute("""
                INSERT OR REPLACE INTO django_migrations (app, name, applied) 
                VALUES ('theatre', '0010_surgerytypeequipment', datetime('now'));
            """)
            
            print("✓ Table created successfully!")
            print("✓ Migration record updated")
            
        except Exception as e:
            print(f"✗ Error creating table: {e}")
            import traceback
            traceback.print_exc()

print("\nDone!")
