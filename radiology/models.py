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

    AUTHORIZATION_STATUS_CHOICES = (
        ('not_required', 'Not Required'),
        ('required', 'Required'),
        ('pending', 'Pending Authorization'),
        ('authorized', 'Authorized'),
        ('rejected', 'Rejected'),
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

    # Authorization code for NHIA patients
    authorization_code = models.ForeignKey('nhia.AuthorizationCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='radiology_orders')

    # Link to consultation
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='radiology_orders',
        help_text="Link to the consultation this radiology order was created from"
    )

    # NHIA Authorization fields
    requires_authorization = models.BooleanField(
        default=False,
        help_text="True if this NHIA patient radiology order from non-NHIA consultation requires desk office authorization"
    )
    authorization_status = models.CharField(
        max_length=20,
        choices=AUTHORIZATION_STATUS_CHOICES,
        default='not_required',
        help_text="Status of authorization for this radiology order"
    )

    def __str__(self):
        return f"{self.test.name} for {self.patient.get_full_name()} ({self.order_date.strftime('%Y-%m-%d')})"

    def is_nhia_patient(self):
        """Check if the patient is an NHIA patient"""
        return self.patient.is_nhia_patient()

    def check_authorization_requirement(self):
        """
        Check if this radiology order requires authorization.
        NHIA patients with radiology orders from non-NHIA consultations require authorization.
        """
        if self.is_nhia_patient():
            # Check if linked to a consultation that requires authorization
            if self.consultation and self.consultation.requires_authorization:
                self.requires_authorization = True
                if not self.authorization_code:
                    self.authorization_status = 'required'
                else:
                    self.authorization_status = 'authorized'
                return True

        self.requires_authorization = False
        self.authorization_status = 'not_required'
        return False

    def can_be_processed(self):
        """Check if radiology order can be processed based on authorization and payment"""
        # Check authorization requirement for NHIA patients from non-NHIA consultations
        if self.requires_authorization:
            if not self.authorization_code:
                return False, 'Desk office authorization required for NHIA patient from non-NHIA unit. Please obtain authorization code before processing.'
            elif not self.authorization_code.is_valid():
                return False, f'Authorization code is {self.authorization_code.status}. Please obtain a valid authorization code.'

        # Check if already completed or cancelled
        if self.status in ['completed', 'cancelled']:
            return False, f'Radiology order is already {self.status}'

        return True, 'Radiology order can be processed'

    class Meta:
        ordering = ['-order_date']

class RadiologyResult(models.Model):
    """Enhanced model for radiology test results"""
    
    # Status choices for result workflow
    RESULT_STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('finalized', 'Finalized'),
    )
    
    # Contrast choices
    CONTRAST_CHOICES = (
        ('none', 'No Contrast'),
        ('oral', 'Oral Contrast'),
        ('iv', 'IV Contrast'),
        ('both', 'Oral + IV Contrast'),
        ('other', 'Other'),
    )
    
    # Image quality choices
    IMAGE_QUALITY_CHOICES = (
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('adequate', 'Adequate'),
        ('poor', 'Poor'),
        ('non_diagnostic', 'Non-diagnostic'),
    )
    
    # Study status choices
    STUDY_STATUS_CHOICES = (
        ('complete', 'Complete'),
        ('incomplete', 'Incomplete'),
        ('limited', 'Limited'),
        ('cancelled', 'Cancelled'),
    )
    
    # Basic fields (existing)
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
    
    # Enhanced fields
    study_date = models.DateField(default=timezone.now)
    study_time = models.TimeField(default=timezone.now)
    radiologist = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reported_radiology'
    )
    technique = models.CharField(max_length=200, blank=True, null=True)
    contrast_used = models.CharField(max_length=20, choices=CONTRAST_CHOICES, default='none')
    contrast_amount = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    images = models.FileField(upload_to='radiology_studies/', blank=True, null=True)
    report_file = models.FileField(upload_to='radiology_reports/', blank=True, null=True)
    image_quality = models.CharField(max_length=20, choices=IMAGE_QUALITY_CHOICES, default='good')
    study_status = models.CharField(max_length=20, choices=STUDY_STATUS_CHOICES, default='complete')
    notes = models.TextField(blank=True, null=True)
    result_status = models.CharField(max_length=20, choices=RESULT_STATUS_CHOICES, default='draft')
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='verified_radiology'
    )
    verified_date = models.DateTimeField(blank=True, null=True)
    verification_notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Result for {self.order}"

    class Meta:
        ordering = ['-result_date']
