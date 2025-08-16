from django.db import models
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class IcuRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='icu_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for icu module here
    # Specific fields
    gcs_score = models.IntegerField(blank=True, null=True, help_text='Glasgow Coma Scale Score')
    respiratory_rate = models.IntegerField(blank=True, null=True)
    oxygen_saturation = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Oxygen saturation in percentage')
    blood_pressure_systolic = models.IntegerField(blank=True, null=True)
    blood_pressure_diastolic = models.IntegerField(blank=True, null=True)
    heart_rate = models.IntegerField(blank=True, null=True)
    body_temperature = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text='Body temperature in Celsius')
    mechanical_ventilation = models.BooleanField(default=False)
    vasopressor_use = models.BooleanField(default=False)
    dialysis_required = models.BooleanField(default=False)

    
    diagnosis = models.TextField(blank=True, null=True)
    treatment_plan = models.TextField(blank=True, null=True)
    
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)
    
    
    # Authorization Code
    authorization_code = models.CharField(max_length=50, blank=True, null=True, help_text="Authorization code from desk office")
    
    notes = models.TextField(blank=True, null=True)

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Icu Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Icu Record'
        verbose_name_plural = 'Icu Records'
