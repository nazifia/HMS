from django.db import models
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class OphthalmicRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='ophthalmic_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Visual Acuity
    visual_acuity_right = models.CharField(max_length=50, blank=True, null=True)
    visual_acuity_left = models.CharField(max_length=50, blank=True, null=True)
    
    # Refraction
    refraction_right_sphere = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    refraction_right_cylinder = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    refraction_right_axis = models.IntegerField(blank=True, null=True)
    
    refraction_left_sphere = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    refraction_left_cylinder = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    refraction_left_axis = models.IntegerField(blank=True, null=True)
    
    # Intraocular Pressure
    iop_right = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Intraocular Pressure (mmHg)")
    iop_left = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Intraocular Pressure (mmHg)")
    
    # Clinical Findings
    clinical_findings = models.TextField(blank=True, null=True)
    
    # Diagnosis
    diagnosis = models.TextField(blank=True, null=True)
    
    # Treatment Plan
    treatment_plan = models.TextField(blank=True, null=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)
    
    # Authorization Code
    authorization_code = models.CharField(max_length=50, blank=True, null=True, help_text="Authorization code from desk office")
    
    # Additional Notes
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ophthalmic Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Ophthalmic Record'
        verbose_name_plural = 'Ophthalmic Records'
