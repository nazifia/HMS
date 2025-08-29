from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0012_pack_alter_packitem_options_alter_packorder_options_and_more'),
    ]

    operations = [
        # Use raw SQL to rename the column since the Django migration system is confused
        migrations.RunSQL(
            "ALTER TABLE pharmacy_prescriptionitem RENAME COLUMN dispensed_date TO dispensed_at;",
            reverse_sql="ALTER TABLE pharmacy_prescriptionitem RENAME COLUMN dispensed_at TO dispensed_date;"
        ),
    ]