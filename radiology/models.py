from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from patients.models import Patient
from django.conf import settings


class RadiologyCategory(models.Model):
    """Model for radiology test categories"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    invoice = models.OneToOneField('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='radiology_category_invoice')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Radiology Categories"
        ordering = ['name']

class RadiologyTest(models.Model):
    """Model for radiology tests"""
    name = models.CharField(max_length=100)
    category = models.ForeignKey(RadiologyCategory, on_delete=models.CASCADE, related_name='tests')
    description = models.TextField(blank=True, null=True)
    preparation_instructions = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    invoice = models.OneToOneField('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='radiology_test_invoice')

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    class Meta:
        ordering = ['name']

# from billing.models import Invoice # This line caused a circular import

class RadiologyOrder(models.Model):
    """Model for radiology orders"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('awaiting_payment', 'Awaiting Payment'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    PRIORITY_CHOICES = (
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='radiology_orders')
    test = models.ForeignKey(RadiologyTest, on_delete=models.CASCADE, related_name='orders')
    referring_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='radiology_referrals')
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='radiology_performed')
    order_date = models.DateTimeField(default=timezone.now)
    scheduled_date = models.DateTimeField(blank=True, null=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    clinical_information = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    invoice = models.OneToOneField('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='radiology_order')

    def __str__(self):
        return f"{self.test.name} for {self.patient.get_full_name()} ({self.order_date.strftime('%Y-%m-%d')})"

    class Meta:
        ordering = ['-order_date']

class RadiologyResult(models.Model):
    """Model for radiology test results"""
    order = models.OneToOneField(RadiologyOrder, on_delete=models.CASCADE, related_name='result')
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='performed_radiology')
    result_date = models.DateTimeField(default=timezone.now)
    findings = models.TextField()
    impression = models.TextField()
    image_file = models.FileField(upload_to='radiology_images/', blank=True, null=True)
    is_abnormal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    invoice = models.OneToOneField('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='radiology_result_invoice')

    def __str__(self):
        return f"Result for {self.order}"

    class Meta:
        ordering = ['-result_date']
