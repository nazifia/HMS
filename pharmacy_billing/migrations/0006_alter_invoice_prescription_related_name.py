# Generated manually to fix related_name clash

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy_billing', '0005_alter_invoice_prescription'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='prescription',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='pharmacy_invoices',
                to='pharmacy.prescription'
            ),
        ),
    ]
