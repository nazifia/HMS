from django.db import models
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class Gynae_emergencyRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='gynae_emergency_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for gynae_emergency module here
    # Specific fields
    emergency_type = models.CharField(max_length=100, blank=True, null=True)
    pain_level = models.IntegerField(blank=True, null=True, help_text='Pain level on scale of 1-10')
    bleeding_amount = models.CharField(max_length=50, blank=True, null=True)
    contractions = models.BooleanField(default=False)
    contraction_frequency = models.CharField(max_length=50, blank=True, null=True)
    rupture_of_membranes = models.BooleanField(default=False)
    fetal_movement = models.CharField(max_length=50, blank=True, null=True)
    vaginal_discharge = models.TextField(blank=True, null=True)
    emergency_intervention = models.TextField(blank=True, null=True)
    stabilization_status = models.CharField(max_length=50, blank=True, null=True)

    
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
        return f"Gynae_emergency Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Gynae_emergency Record'
        verbose_name_plural = 'Gynae_emergency Records'
