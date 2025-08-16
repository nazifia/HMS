from django.db import models
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class OncologyRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='oncology_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Add specific fields for oncology module here
    # Specific fields
    cancer_type = models.CharField(max_length=100, blank=True, null=True)
    stage = models.CharField(max_length=20, blank=True, null=True)
    tumor_size = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Tumor size in cm')
    metastasis = models.BooleanField(default=False)
    treatment_protocol = models.TextField(blank=True, null=True)
    chemotherapy_cycle = models.IntegerField(blank=True, null=True)
    radiation_dose = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text='Radiation dose in Gy')
    surgery_details = models.TextField(blank=True, null=True)
    biopsy_results = models.TextField(blank=True, null=True)
    oncology_marker = models.TextField(blank=True, null=True)

    
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
        return f"Oncology Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Oncology Record'
        verbose_name_plural = 'Oncology Records'
