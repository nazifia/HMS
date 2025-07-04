# Generated by Django 5.2 on 2025-05-31 08:03

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('billing', '0001_initial'),
        ('patients', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TestCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Test Categories',
            },
        ),
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('preparation_instructions', models.TextField(blank=True, null=True)),
                ('normal_range', models.CharField(blank=True, max_length=100, null=True)),
                ('unit', models.CharField(blank=True, max_length=50, null=True)),
                ('sample_type', models.CharField(max_length=50)),
                ('duration', models.CharField(blank=True, max_length=50, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tests', to='laboratory.testcategory')),
            ],
        ),
        migrations.CreateModel(
            name='TestParameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('normal_range', models.CharField(blank=True, max_length=100, null=True)),
                ('unit', models.CharField(blank=True, max_length=50, null=True)),
                ('order', models.IntegerField(default=0)),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameters', to='laboratory.test')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='TestRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_date', models.DateField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('awaiting_payment', 'Awaiting Payment'), ('payment_confirmed', 'Payment Confirmed'), ('sample_collected', 'Sample Collected'), ('processing', 'Processing'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('priority', models.CharField(choices=[('normal', 'Normal'), ('urgent', 'Urgent'), ('emergency', 'Emergency')], default='normal', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_test_requests', to=settings.AUTH_USER_MODEL)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doctor_test_requests', to=settings.AUTH_USER_MODEL)),
                ('invoice', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lab_test_request', to='billing.invoice')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_requests', to='patients.patient')),
                ('tests', models.ManyToManyField(related_name='test_requests', to='laboratory.test')),
            ],
            options={
                'ordering': ['-request_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TestResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result_date', models.DateField(default=django.utils.timezone.now)),
                ('sample_collection_date', models.DateTimeField(blank=True, null=True)),
                ('result_file', models.FileField(blank=True, null=True, upload_to='test_results/')),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('performed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='performed_tests', to=settings.AUTH_USER_MODEL)),
                ('sample_collected_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='collected_samples', to=settings.AUTH_USER_MODEL)),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='laboratory.test')),
                ('test_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='laboratory.testrequest')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_tests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-result_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TestResultParameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=100)),
                ('is_normal', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('parameter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='laboratory.testparameter')),
                ('test_result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameters', to='laboratory.testresult')),
            ],
        ),
        migrations.AddIndex(
            model_name='testrequest',
            index=models.Index(fields=['patient'], name='laboratory__patient_20bebf_idx'),
        ),
        migrations.AddIndex(
            model_name='testrequest',
            index=models.Index(fields=['doctor'], name='laboratory__doctor__91fa67_idx'),
        ),
        migrations.AddIndex(
            model_name='testrequest',
            index=models.Index(fields=['status'], name='laboratory__status_62cf0a_idx'),
        ),
        migrations.AddIndex(
            model_name='testrequest',
            index=models.Index(fields=['request_date'], name='laboratory__request_8c1fbf_idx'),
        ),
        migrations.AddIndex(
            model_name='testresult',
            index=models.Index(fields=['test_request'], name='laboratory__test_re_267121_idx'),
        ),
        migrations.AddIndex(
            model_name='testresult',
            index=models.Index(fields=['test'], name='laboratory__test_id_31af16_idx'),
        ),
        migrations.AddIndex(
            model_name='testresult',
            index=models.Index(fields=['result_date'], name='laboratory__result__b7c534_idx'),
        ),
    ]
