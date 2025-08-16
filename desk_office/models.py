
import uuid
from django.db import models
from patients.models import Patient

class AuthorizationCode(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('used', 'Used'),
        ('expired', 'Expired'),
    )

    code = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    service = models.CharField(max_length=255)
    department = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.patient} - {self.service} - {self.status}"
