from django.db import models
from patients.models import Patient
from django.core.validators import MinValueValidator, MaxValueValidator

class RetainershipPatient(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='retainership_info')
    retainership_reg_number = models.BigIntegerField(
        unique=True, 
        help_text="Unique Retainership registration number starting with 3, 10 digits long",
        validators=[
            MinValueValidator(3000000000),
            MaxValueValidator(3999999999)
        ]
    )
    is_active = models.BooleanField(default=True)
    date_registered = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.patient.get_full_name()} (Retainership: {self.retainership_reg_number})"

    class Meta:
        verbose_name = "Retainership Patient"
        verbose_name_plural = "Retainership Patients"
