from django.db import models
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class ScbuRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='scbu_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for scbu module here
    # Specific fields
    gestational_age = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True, help_text='Gestational age in weeks')
    birth_weight = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, help_text='Birth weight in kg')
    apgar_score_1min = models.IntegerField(blank=True, null=True, help_text='APGAR score at 1 minute')
    apgar_score_5min = models.IntegerField(blank=True, null=True, help_text='APGAR score at 5 minutes')
    respiratory_support = models.BooleanField(default=False)
    ventilation_type = models.CharField(max_length=50, blank=True, null=True)
    feeding_method = models.CharField(max_length=50, blank=True, null=True)
    infection_status = models.BooleanField(default=False)
    antibiotic_name = models.CharField(max_length=100, blank=True, null=True)
    discharge_weight = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, help_text='Discharge weight in kg')

    
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
        return f"Scbu Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Scbu Record'
        verbose_name_plural = 'Scbu Records'
