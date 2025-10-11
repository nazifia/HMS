# Generated migration to add missing fields to activity monitoring models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_merge_20251011_1652'),
    ]

    operations = [
        migrations.AddField(
            model_name='activityalert',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='activityalert',
            name='metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='activityalert',
            name='resolved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='activityalert',
            name='resolved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='resolved_alerts', to='accounts.customuser'),
        ),
        migrations.AddField(
            model_name='activityalert',
            name='resolution_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='activityalert',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='activity_level',
            field=models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='low', max_length=10),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='additional_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='module',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='object_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='object_repr',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='object_type',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='response_time_ms',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='session_key',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='status_code',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='useractivity',
            name='user_agent',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='useractivity',
            name='action_type',
            field=models.CharField(choices=[('login', 'Login'), ('logout', 'Logout'), ('view', 'View'), ('create', 'Create'), ('update', 'Update'), ('delete', 'Delete'), ('export', 'Export'), ('search', 'Search'), ('download', 'Download'), ('print', 'Print'), ('authorize', 'Authorize'), ('access_denied', 'Access Denied'), ('error', 'Error'), ('other', 'Other')], max_length=20),
        ),
        migrations.AddField(
            model_name='usersession',
            name='average_response_time',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usersession',
            name='ended_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usersession',
            name='ended_reason',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='usersession',
            name='ip_address',
            field=models.GenericIPAddressField(),
        ),
        migrations.AddField(
            model_name='usersession',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usersession',
            name='last_activity',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='usersession',
            name='page_views',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='usersession',
            name='total_requests',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='usersession',
            name='user_agent',
            field=models.TextField(blank=True),
        ),
    ]
