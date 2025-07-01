from django.db import models
from patients.models import Patient

class NHIAPatient(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='nhia_info')
    nhia_reg_number = models.CharField(max_length=50, unique=True, help_text="Unique NHIA registration number")
    is_active = models.BooleanField(default=True)
    date_registered = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.patient.get_full_name()} (NHIA: {self.nhia_reg_number})"

    class Meta:
        verbose_name = "NHIA Patient"
        verbose_name_plural = "NHIA Patients"