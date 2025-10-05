# Generated migration for Prescription Cart models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0021_remove_total_cost_from_medicalpack'),
        ('pharmacy_billing', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PrescriptionCart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('active', 'Active'), ('invoiced', 'Invoiced'), ('paid', 'Paid'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='active', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='prescription_carts_created', to=settings.AUTH_USER_MODEL)),
                ('dispensary', models.ForeignKey(blank=True, help_text='Dispensary from which items will be dispensed', null=True, on_delete=django.db.models.deletion.SET_NULL, to='pharmacy.dispensary')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='prescription_cart', to='pharmacy_billing.invoice')),
                ('prescription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='carts', to='pharmacy.prescription')),
            ],
            options={
                'verbose_name': 'Prescription Cart',
                'verbose_name_plural': 'Prescription Carts',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PrescriptionCartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(help_text='Quantity to dispense/bill')),
                ('unit_price', models.DecimalField(decimal_places=2, help_text='Unit price at time of adding to cart', max_digits=10)),
                ('available_stock', models.IntegerField(default=0, help_text='Available stock at time of adding to cart (cached)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='pharmacy.prescriptioncart')),
                ('prescription_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cart_items', to='pharmacy.prescriptionitem')),
            ],
            options={
                'verbose_name': 'Cart Item',
                'verbose_name_plural': 'Cart Items',
                'ordering': ['created_at'],
                'unique_together': {('cart', 'prescription_item')},
            },
        ),
    ]

