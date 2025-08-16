from django.db import models
from django.utils import timezone
from django.conf import settings
from patients.models import Patient

class TestCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Test Categories"

class Test(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(TestCategory, on_delete=models.SET_NULL, null=True, related_name='tests')
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    preparation_instructions = models.TextField(blank=True, null=True)
    normal_range = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)  # e.g., mg/dL, mmol/L
    sample_type = models.CharField(max_length=50)  # e.g., blood, urine, stool
    duration = models.CharField(max_length=50, blank=True, null=True)  # e.g., 1 day, 3 hours
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class TestParameter(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=100)
    normal_range = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    order = models.IntegerField(default=0)  # For ordering parameters in a test

    def __str__(self):
        return f"{self.test.name} - {self.name}"

    class Meta:
        ordering = ['order']

class TestRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('awaiting_payment', 'Awaiting Payment'), # New status
        ('payment_confirmed', 'Payment Confirmed'), # New status (or could be 'ready_for_sample_collection')
        ('sample_collected', 'Sample Collected'), # Renamed from 'collected' for clarity
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='test_requests')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_test_requests')
    tests = models.ManyToManyField(Test, related_name='test_requests')
    request_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=(
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    ), default='normal')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_test_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Link to an invoice - can be null if not yet billed or if billing is handled differently
    invoice = models.OneToOneField('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_test_request')
    
    # Authorization code for NHIA patients
    authorization_code = models.ForeignKey('nhia.AuthorizationCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_test_requests')

    def __str__(self):
        return f"Test Request for {self.patient.get_full_name()} - {self.request_date}"

    def get_total_price(self):
        return sum(test.price for test in self.tests.all())

    class Meta:
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['doctor']),
            models.Index(fields=['status']),
            models.Index(fields=['request_date']),
        ]
        ordering = ['-request_date', '-created_at']

class TestResult(models.Model):
    test_request = models.ForeignKey(TestRequest, on_delete=models.CASCADE, related_name='results')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='results')
    result_date = models.DateField(default=timezone.now)
    sample_collection_date = models.DateTimeField(blank=True, null=True)
    sample_collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='collected_samples')
    result_file = models.FileField(upload_to='test_results/', blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='performed_tests')
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_tests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.test.name} result for {self.test_request.patient.get_full_name()} - {self.result_date}"

    class Meta:
        indexes = [
            models.Index(fields=['test_request']),
            models.Index(fields=['test']),
            models.Index(fields=['result_date']),
        ]
        ordering = ['-result_date', '-created_at']

class TestResultParameter(models.Model):
    test_result = models.ForeignKey(TestResult, on_delete=models.CASCADE, related_name='parameters')
    parameter = models.ForeignKey(TestParameter, on_delete=models.CASCADE)
    value = models.CharField(max_length=100)
    is_normal = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.parameter.name}: {self.value} {self.parameter.unit or ''}"
