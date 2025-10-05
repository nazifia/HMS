# Generated migration to remove total_cost field from MedicalPack

from django.db import migrations


def remove_total_cost_column(apps, schema_editor):
    """Remove total_cost column from MedicalPack table"""
    # SQLite doesn't support DROP COLUMN, so we need to recreate the table
    with schema_editor.connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("PRAGMA table_info(pharmacy_medicalpack);")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if 'total_cost' in column_names:
            # Create new table without total_cost
            cursor.execute("""
                CREATE TABLE pharmacy_medicalpack_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    pack_type VARCHAR(20) NOT NULL,
                    surgery_type VARCHAR(50),
                    labor_type VARCHAR(50),
                    risk_level VARCHAR(10) NOT NULL,
                    requires_approval BOOLEAN NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                );
            """)

            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO pharmacy_medicalpack_new
                (id, name, description, pack_type, surgery_type, labor_type,
                 risk_level, requires_approval, is_active, created_at, updated_at)
                SELECT id, name, description, pack_type, surgery_type, labor_type,
                       risk_level, requires_approval, is_active, created_at, updated_at
                FROM pharmacy_medicalpack;
            """)

            # Drop old table
            cursor.execute("DROP TABLE pharmacy_medicalpack;")

            # Rename new table
            cursor.execute("ALTER TABLE pharmacy_medicalpack_new RENAME TO pharmacy_medicalpack;")


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0020_add_labor_record_to_packorder'),
    ]

    operations = [
        migrations.RunPython(remove_total_cost_column, migrations.RunPython.noop),
    ]

