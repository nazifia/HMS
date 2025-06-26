from django.db import models
from django.utils import timezone
from django.conf import settings

class Report(models.Model):
    CATEGORY_CHOICES = (
        ('financial', 'Financial'),
        ('clinical', 'Clinical'),
        ('operational', 'Operational'),
        ('administrative', 'Administrative'),
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    query = models.TextField(blank=True, null=True)  # SQL query or query definition
    parameters = models.TextField(blank=True, null=True)  # JSON string of required parameters
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='operational')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    # Add any custom methods here

class ReportExecution(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='executions')
    parameters = models.TextField(blank=True, null=True)  # JSON string of parameters used
    result_count = models.IntegerField(default=0)  # Number of records returned
    executed_at = models.DateTimeField(default=timezone.now)
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='executed_reports', null=True, blank=True)

    def __str__(self):
        return f"{self.report.name} - {self.executed_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-executed_at']

class Dashboard(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_dashboards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']

class DashboardWidget(models.Model):
    WIDGET_TYPE_CHOICES = (
        ('table', 'Table'),
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('donut', 'Donut Chart'),
    )

    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='widgets')
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='widgets', null=True, blank=True)
    title = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPE_CHOICES, default='table')
    parameters = models.TextField(blank=True, null=True)  # JSON string of parameters
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=6)  # Default half width (out of 12)
    height = models.IntegerField(default=4)  # Default height in rows
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_widget_type_display()}) on {self.dashboard.name}"

    class Meta:
        ordering = ['dashboard', 'position_y', 'position_x']
