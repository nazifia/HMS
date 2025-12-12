from django.db import models
from django.utils import timezone
from patients.models import Patient
from django.conf import settings
from typing import Any
from decimal import Decimal

class DermatologyService(models.Model):
    """Model for dermatology services/procedures"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)  # type: ignore
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = "Dermatology Service"
        verbose_name_plural = "Dermatology Services"


class DermatologyRecord(models.Model):
    """Enhanced dermatology record model with comprehensive fields"""
    
    CONDITION_TYPE_CHOICES = [
        ('acne', 'Acne'),
        ('eczema', 'Eczema'),
        ('psoriasis', 'Psoriasis'),
        ('dermatitis', 'Dermatitis'),
        ('skin_cancer', 'Skin Cancer'),
        ('infection', 'Skin Infection'),
        ('allergy', 'Skin Allergy'),
        ('rosacea', 'Rosacea'),
        ('moles', 'Moles & Birthmarks'),
        ('other', 'Other Skin Condition'),
    ]
    
    TREATMENT_STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='dermatology_records')
    condition_type = models.CharField(max_length=20, choices=CONDITION_TYPE_CHOICES, blank=True, null=True)
    service = models.ForeignKey(DermatologyService, on_delete=models.SET_NULL, null=True, blank=True, related_name='dermatology_records')
    diagnosis = models.TextField(help_text="Diagnosis or findings")
    treatment_procedure = models.TextField(help_text="Treatment procedure performed")
    treatment_status = models.CharField(max_length=20, choices=TREATMENT_STATUS_CHOICES, default='planned')
    notes = models.TextField(blank=True, null=True)
    appointment_date = models.DateTimeField(default=timezone.now)
    next_appointment_date = models.DateTimeField(blank=True, null=True)
    dermatologist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dermatology_treatments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Billing fields
    invoice = models.OneToOneField('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='dermatology_record')
    # NHIA Authorization fields
    requires_authorization = models.BooleanField(
        default=False,
        help_text="True if this NHIA patient dermatology record requires desk office authorization"
    )
    AUTHORIZATION_STATUS_CHOICES = (
        ('not_required', 'Not Required'),
        ('required', 'Required'),
        ('pending', 'Pending Authorization'),
        ('authorized', 'Authorized'),
        ('rejected', 'Rejected'),
    )
    authorization_status = models.CharField(
        max_length=20,
        choices=AUTHORIZATION_STATUS_CHOICES,
        default='not_required',
        help_text="Status of authorization for this dermatology record"
    )
    authorization_code = models.ForeignKey('nhia.AuthorizationCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='dermatology_records')

    def __str__(self) -> str:
        condition_display = dict(self.CONDITION_TYPE_CHOICES).get(self.condition_type, 'N/A') if self.condition_type else 'N/A'  # type: ignore
        service_name = self.service.name if self.service else 'N/A'  # type: ignore
        return f"Dermatology Record: {service_name} for {self.patient.get_full_name()} - Condition: {condition_display}"  # type: ignore

    def get_condition_display(self) -> str:
        """Get human-readable condition name"""
        return dict(self.CONDITION_TYPE_CHOICES).get(self.condition_type, self.condition_type) if self.condition_type else 'Not specified'  # type: ignore

    def get_service_price(self) -> Any:
        """Get the price of the service"""
        return self.service.price if self.service else 0.00  # type: ignore

    def is_nhia_patient(self) -> bool:
        """Check if the patient is an NHIA patient"""
        return hasattr(self.patient, 'nhia_info') and self.patient.nhia_info is not None  # type: ignore

    def check_authorization_requirement(self) -> bool:
        """
        Check if this dermatology record requires authorization.
        All NHIA patient dermatology records require authorization.
        """
        if self.is_nhia_patient():
            self.requires_authorization = True
            if not self.authorization_code:
                self.authorization_status = 'required'
            elif self.authorization_code and hasattr(self.authorization_code, 'is_valid') and self.authorization_code.is_valid():  # type: ignore
                self.authorization_status = 'authorized'
            return True
        else:
            self.requires_authorization = False
            self.authorization_status = 'not_required'
            return False

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to auto-check authorization requirement"""
        self.check_authorization_requirement()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Dermatology Record"
        verbose_name_plural = "Dermatology Records"


class DermatologyPrescription(models.Model):
    """Model for dermatology prescriptions"""
    dermatology_record = models.ForeignKey(DermatologyRecord, on_delete=models.CASCADE, related_name='prescriptions')
    medication = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.TextField(blank=True, null=True)
    prescribed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    prescribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # type: ignore

    def __str__(self) -> str:
        return f"Prescription for {self.dermatology_record.patient.get_full_name()} - {self.medication}"  # type: ignore

    class Meta:
        ordering = ['-prescribed_at']
        verbose_name = "Dermatology Prescription"
        verbose_name_plural = "Dermatology Prescriptions"


class DermatologyTest(models.Model):
    """Model for dermatology diagnostic tests"""
    TEST_TYPE_CHOICES = [
        ('biopsy', 'Skin Biopsy'),
        ('patch_test', 'Patch Test'),
        ('culture', 'Skin Culture'),
        ('woods_lamp', 'Wood\'s Lamp Examination'),
        ('dermatoscopy', 'Dermatoscopy'),
        ('blood_test', 'Blood Test'),
        ('allergy_test', 'Allergy Test'),
        ('other', 'Other'),
    ]

    dermatology_record = models.ForeignKey(DermatologyRecord, on_delete=models.CASCADE, related_name='tests')
    test_type = models.CharField(max_length=30, choices=TEST_TYPE_CHOICES)
    results = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    performed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.get_test_type_display()} Test for {self.dermatology_record.patient.get_full_name()}"  # type: ignore

    class Meta:
        ordering = ['-performed_at']
        verbose_name = "Dermatology Test"
        verbose_name_plural = "Dermatology Tests"


class DermatologyClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for dermatology records"""
    dermatology_record = models.ForeignKey(DermatologyRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='dermatology_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Clinical Note for {self.dermatology_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"  # type: ignore

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Dermatology Clinical Note"
        verbose_name_plural = "Dermatology Clinical Notes"
