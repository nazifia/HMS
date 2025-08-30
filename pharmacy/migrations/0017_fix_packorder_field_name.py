# Generated manually to fix PackOrder field name

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0016_add_dispensary_transfer'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE pharmacy_packorder RENAME COLUMN order_date TO ordered_at;",
            reverse_sql="ALTER TABLE pharmacy_packorder RENAME COLUMN ordered_at TO order_date;"
        ),
    ]
