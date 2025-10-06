# Generated migration for partial dispensing support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0022_prescription_cart'),
    ]

    operations = [
        migrations.AlterField(
            model_name='prescriptioncart',
            name='status',
            field=models.CharField(
                choices=[
                    ('active', 'Active'),
                    ('invoiced', 'Invoiced'),
                    ('paid', 'Paid'),
                    ('partially_dispensed', 'Partially Dispensed'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled')
                ],
                default='active',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='prescriptioncartitem',
            name='quantity_dispensed',
            field=models.IntegerField(
                default=0,
                help_text='Quantity already dispensed from this cart item'
            ),
        ),
    ]

