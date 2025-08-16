from django.db import models
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class LaborRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='labor_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for labor module here
    # Specific fields
    onset_time = models.DateTimeField(blank=True, null=True)
    presentation = models.CharField(max_length=50, blank=True, null=True)
    fetal_heart_rate = models.IntegerField(blank=True, null=True)
    cervical_dilation = models.IntegerField(blank=True, null=True, help_text='Cervical dilation in cm')
    effacement = models.IntegerField(blank=True, null=True, help_text='Effacement in percentage')
    rupture_of_membranes = models.BooleanField(default=False)
    rupture_time = models.DateTimeField(blank=True, null=True)
    mode_of_delivery = models.CharField(max_length=50, blank=True, null=True)
    duration_first_stage = models.DurationField(blank=True, null=True)
    placenta_delivery_time = models.DateTimeField(blank=True, null=True)

    
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
        return f"Labor Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Labor Record'
        verbose_name_plural = 'Labor Records'
