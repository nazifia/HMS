from django.db import models
from django.utils import timezone
from patients.models import Patient
from django.conf import settings
from typing import Any
from decimal import Decimal

class DentalService(models.Model):
    """Model for dental services/procedures"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)  # type: ignore
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = "Dental Service"
        verbose_name_plural = "Dental Services"


class DentalRecord(models.Model):
    """Enhanced dental record model with comprehensive fields"""
    
    TEETH_CHOICES = [
        ('11', 'Upper Right Central Incisor (11)'),
        ('12', 'Upper Right Lateral Incisor (12)'),
        ('13', 'Upper Right Canine (13)'),
        ('14', 'Upper Right First Premolar (14)'),
        ('15', 'Upper Right Second Premolar (15)'),
        ('16', 'Upper Right First Molar (16)'),
        ('17', 'Upper Right Second Molar (17)'),
        ('18', 'Upper Right Third Molar/Wisdom Tooth (18)'),
        ('21', 'Upper Left Central Incisor (21)'),
        ('22', 'Upper Left Lateral Incisor (22)'),
        ('23', 'Upper Left Canine (23)'),
        ('24', 'Upper Left First Premolar (24)'),
        ('25', 'Upper Left Second Premolar (25)'),
        ('26', 'Upper Left First Molar (26)'),
        ('27', 'Upper Left Second Molar (27)'),
        ('28', 'Upper Left Third Molar/Wisdom Tooth (28)'),
        ('31', 'Lower Left Central Incisor (31)'),
        ('32', 'Lower Left Lateral Incisor (32)'),
        ('33', 'Lower Left Canine (33)'),
        ('34', 'Lower Left First Premolar (34)'),
        ('35', 'Lower Left Second Premolar (35)'),
        ('36', 'Lower Left First Molar (36)'),
        ('37', 'Lower Left Second Molar (37)'),
        ('38', 'Lower Left Third Molar/Wisdom Tooth (38)'),
        ('41', 'Lower Right Central Incisor (41)'),
        ('42', 'Lower Right Lateral Incisor (42)'),
        ('43', 'Lower Right Canine (43)'),
        ('44', 'Lower Right First Premolar (44)'),
        ('45', 'Lower Right Second Premolar (45)'),
        ('46', 'Lower Right First Molar (46)'),
        ('47', 'Lower Right Second Molar (47)'),
        ('48', 'Lower Right Third Molar/Wisdom Tooth (48)'),
        ('all', 'All Teeth'),
        ('upper', 'All Upper Teeth'),
        ('lower', 'All Lower Teeth'),
    ]
    
    TREATMENT_STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='dental_records')
    tooth = models.CharField(max_length=10, choices=TEETH_CHOICES, blank=True, null=True)
    service = models.ForeignKey(DentalService, on_delete=models.SET_NULL, null=True, blank=True, related_name='dental_records')
    diagnosis = models.TextField(help_text="Diagnosis or findings")
    treatment_procedure = models.TextField(help_text="Treatment procedure performed")
    treatment_status = models.CharField(max_length=20, choices=TREATMENT_STATUS_CHOICES, default='planned')
    notes = models.TextField(blank=True, null=True)
    appointment_date = models.DateTimeField(default=timezone.now)
    next_appointment_date = models.DateTimeField(blank=True, null=True)
    dentist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dental_treatments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Billing fields
    invoice = models.OneToOneField('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='dental_record')
    authorization_code = models.ForeignKey('nhia.AuthorizationCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='dental_records')

    def __str__(self) -> str:
        tooth_display = dict(self.TEETH_CHOICES).get(self.tooth, 'N/A') if self.tooth else 'N/A'  # type: ignore
        service_name = self.service.name if self.service else 'N/A'  # type: ignore
        return f"Dental Record: {service_name} for {self.patient.get_full_name()} - Tooth: {tooth_display}"  # type: ignore

    def get_tooth_display(self) -> str:
        """Get human-readable tooth name"""
        return dict(self.TEETH_CHOICES).get(self.tooth, self.tooth) if self.tooth else 'Not specified'  # type: ignore

    def get_service_price(self) -> Any:
        """Get the price of the service"""
        return self.service.price if self.service else 0.00  # type: ignore

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Dental Record"
        verbose_name_plural = "Dental Records"


class DentalPrescription(models.Model):
    """Model for dental prescriptions"""
    dental_record = models.ForeignKey(DentalRecord, on_delete=models.CASCADE, related_name='prescriptions')
    medication = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.TextField(blank=True, null=True)
    prescribed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    prescribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # type: ignore

    def __str__(self) -> str:
        return f"Prescription for {self.dental_record.patient.get_full_name()} - {self.medication}"  # type: ignore

    class Meta:
        ordering = ['-prescribed_at']
        verbose_name = "Dental Prescription"
        verbose_name_plural = "Dental Prescriptions"


class DentalXRay(models.Model):
    """Model for dental X-rays"""
    XRAY_TYPE_CHOICES = [
        ('bitewing', 'Bitewing'),
        ('periapical', 'Periapical'),
        ('panoramic', 'Panoramic'),
        ('cephalometric', 'Cephalometric'),
        ('occlusal', 'Occlusal'),
        ('other', 'Other'),
    ]
    
    dental_record = models.ForeignKey(DentalRecord, on_delete=models.CASCADE, related_name='xrays')
    xray_type = models.CharField(max_length=20, choices=XRAY_TYPE_CHOICES)
    image = models.ImageField(upload_to='dental_xrays/', blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    taken_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    taken_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.get_xray_type_display()} X-Ray for {self.dental_record.patient.get_full_name()}"  # type: ignore

    class Meta:
        ordering = ['-taken_at']
        verbose_name = "Dental X-Ray"
        verbose_name_plural = "Dental X-Rays"