from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_alter_customuserprofile_department'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuserprofile',
            name='role',
            field=models.CharField(blank=True, choices=[('admin', 'Administrator'), ('doctor', 'Doctor'), ('nurse', 'Nurse'), ('receptionist', 'Receptionist'), ('pharmacist', 'Pharmacist'), ('lab_technician', 'Lab Technician'), ('radiology_staff', 'Radiology Staff'), ('accountant', 'Accountant'), ('health_record_officer', 'Health Record Officer')], max_length=30, null=True),
        ),
    ]