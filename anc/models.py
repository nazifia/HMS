from django.db import models
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class AncRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='anc_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for anc module here
    # Specific fields
    gravida = models.IntegerField(blank=True, null=True)
    para = models.IntegerField(blank=True, null=True)
    abortions = models.IntegerField(blank=True, null=True)
    lmp = models.DateField(blank=True, null=True, help_text='Last Menstrual Period')
    edd = models.DateField(blank=True, null=True, help_text='Expected Date of Delivery')
    fundal_height = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text='Fundal height in cm')
    fetal_heartbeat = models.BooleanField(default=False)
    fetal_position = models.CharField(max_length=50, blank=True, null=True)
    blood_pressure = models.CharField(max_length=20, blank=True, null=True)
    urine_protein = models.CharField(max_length=20, blank=True, null=True)

    
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
        return f"Anc Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Anc Record'
        verbose_name_plural = 'Anc Records'
