# Generated manually to add labor_record field back to PackOrder

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0019_prescription_authorization_code_and_more'),
        ('labor', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='packorder',
            name='labor_record',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='pack_orders',
                to='labor.laborrecord'
            ),
        ),
    ]

