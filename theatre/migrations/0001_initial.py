# Generated by Django 5.2.3 on 2025-06-23 06:53

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('patients', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OperationTheatre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('theatre_number', models.CharField(max_length=20, unique=True)),
                ('floor', models.CharField(max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('is_available', models.BooleanField(default=True)),
                ('capacity', models.PositiveIntegerField(default=1)),
                ('equipment_list', models.TextField(blank=True, null=True)),
                ('last_sanitized', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Operation Theatre',
                'verbose_name_plural': 'Operation Theatres',
                'ordering': ['theatre_number'],
            },
        ),
        migrations.CreateModel(
            name='SurgeryType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
                ('average_duration', models.DurationField(help_text='Expected duration of surgery (HH:MM:SS)')),
                ('preparation_time', models.DurationField(help_text='Time needed for preparation before surgery')),
                ('recovery_time', models.DurationField(help_text='Expected recovery time after surgery')),
                ('risk_level', models.CharField(choices=[('low', 'Low Risk'), ('medium', 'Medium Risk'), ('high', 'High Risk'), ('critical', 'Critical Risk')], default='medium', max_length=20)),
                ('instructions', models.TextField(blank=True, help_text='Special instructions for this surgery type', null=True)),
            ],
            options={
                'verbose_name': 'Surgery Type',
                'verbose_name_plural': 'Surgery Types',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='SurgicalEquipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('equipment_type', models.CharField(choices=[('instrument', 'Surgical Instrument'), ('monitor', 'Monitoring Equipment'), ('anesthesia', 'Anesthesia Equipment'), ('imaging', 'Imaging Equipment'), ('other', 'Other Equipment')], max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('quantity_available', models.PositiveIntegerField(default=1)),
                ('is_available', models.BooleanField(default=True)),
                ('last_maintenance_date', models.DateField(blank=True, null=True)),
                ('next_maintenance_date', models.DateField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Surgical Equipment',
                'verbose_name_plural': 'Surgical Equipment',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Surgery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_date', models.DateTimeField()),
                ('expected_duration', models.DurationField()),
                ('pre_surgery_notes', models.TextField(blank=True, null=True)),
                ('post_surgery_notes', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('postponed', 'Postponed')], default='scheduled', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('anesthetist', models.ForeignKey(limit_choices_to={'custom_profile__specialization__icontains': 'anesthetist'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='anesthetist_surgeries', to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='surgeries', to='patients.patient')),
                ('primary_surgeon', models.ForeignKey(limit_choices_to={'custom_profile__specialization__icontains': 'surgeon'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='primary_surgeries', to=settings.AUTH_USER_MODEL)),
                ('theatre', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='surgeries', to='theatre.operationtheatre')),
                ('surgery_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='surgeries', to='theatre.surgerytype')),
            ],
            options={
                'verbose_name': 'Surgery',
                'verbose_name_plural': 'Surgeries',
                'ordering': ['-scheduled_date'],
            },
        ),
        migrations.CreateModel(
            name='PostOperativeNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notes', models.TextField()),
                ('complications', models.TextField(blank=True, null=True)),
                ('follow_up_instructions', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='post_op_notes', to=settings.AUTH_USER_MODEL)),
                ('surgery', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_op_notes', to='theatre.surgery')),
            ],
            options={
                'verbose_name': 'Post-Operative Note',
                'verbose_name_plural': 'Post-Operative Notes',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SurgerySchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('pre_op_preparation_start', models.DateTimeField()),
                ('post_op_recovery_end', models.DateTimeField()),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('delayed', 'Delayed'), ('cancelled', 'Cancelled')], default='scheduled', max_length=20)),
                ('delay_reason', models.TextField(blank=True, null=True)),
                ('surgery', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='schedule', to='theatre.surgery')),
            ],
            options={
                'verbose_name': 'Surgery Schedule',
                'verbose_name_plural': 'Surgery Schedules',
                'ordering': ['start_time'],
            },
        ),
        migrations.CreateModel(
            name='EquipmentUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_used', models.PositiveIntegerField(default=1)),
                ('notes', models.TextField(blank=True, null=True)),
                ('surgery', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment_used', to='theatre.surgery')),
                ('equipment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage_records', to='theatre.surgicalequipment')),
            ],
            options={
                'verbose_name': 'Equipment Usage',
                'verbose_name_plural': 'Equipment Usage Records',
            },
        ),
        migrations.CreateModel(
            name='SurgicalTeam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('surgeon', 'Surgeon'), ('assistant_surgeon', 'Assistant Surgeon'), ('anesthetist', 'Anesthetist'), ('nurse', 'Nurse'), ('technician', 'Technician'), ('other', 'Other')], max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='surgical_assignments', to=settings.AUTH_USER_MODEL)),
                ('surgery', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_members', to='theatre.surgery')),
            ],
            options={
                'verbose_name': 'Surgical Team Member',
                'verbose_name_plural': 'Surgical Team Members',
                'unique_together': {('surgery', 'staff', 'role')},
            },
        ),
    ]
