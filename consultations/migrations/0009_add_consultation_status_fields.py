# Generated migration for consultation status update functionality

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consultations', '0008_remove_doctor_referral_type'),  # Latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='consultation',
            name='consultation_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('general', 'General'),
                    ('specialist', 'Specialist'),
                    ('emergency', 'Emergency'),
                    ('followup', 'Follow-up'),
                    ('review', 'Review')
                ],
                default='general',
                help_text='Type of consultation',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='consultation',
            name='start_time',
            field=models.DateTimeField(
                blank=True,
                help_text='When consultation started',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='consultation',
            name='end_time',
            field=models.DateTimeField(
                blank=True,
                help_text='When consultation ended',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='consultation',
            name='duration',
            field=models.IntegerField(
                blank=True,
                help_text='Duration in minutes',
                null=True
            ),
        ),
    ]
