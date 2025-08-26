import uuid
from django.db import models
from patients.models import Patient
from typing import TYPE_CHECKING

class AuthorizationCode(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('used', 'Used'),
        ('expired', 'Expired'),
    )

    SERVICE_TYPE_CHOICES = (
        ('laboratory', 'Laboratory'),
        ('radiology', 'Radiology'),
        ('theatre', 'Theatre/Surgery'),
        ('inpatient', 'Inpatient'),
        ('dental', 'Dental'),
        ('opthalmic', 'Ophthalmic'),
        ('ent', 'ENT'),
        ('oncology', 'Oncology'),
        ('gynae_emergency', 'Gynae Emergency'),
        ('labor', 'Labor & Delivery'),
        ('scbu', 'SCBU'),
        ('icu', 'ICU'),
        ('general', 'General Consultation'),
        ('other', 'Other Services'),
    )

    code = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES, default='general')
    service_description = models.TextField(blank=True, null=True, help_text="Description of the specific service requested")
    department = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    
    if TYPE_CHECKING:
        def get_service_type_display(self) -> str: ...

    def __str__(self):
        return f"{self.patient} - {self.get_service_type_display()} - {self.status}"

    def is_valid(self):
        """Check if the authorization code is still valid"""
        from django.utils import timezone
        if self.status != 'pending':
            return False
        # Add any additional validation logic here if needed
        return True

    def mark_as_used(self):
        """Mark the authorization code as used"""
        from django.utils import timezone
        self.status = 'used'
        self.used_at = timezone.now()
        self.save()