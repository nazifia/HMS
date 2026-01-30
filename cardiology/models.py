from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class CardiologyRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='cardiology_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Cardiology-specific fields
    chest_pain_type = models.CharField(max_length=50, blank=True, null=True, help_text='Type of chest pain (e.g., Angina, Myocardial Infarction, Non-cardiac)')
    ecg_findings = models.TextField(blank=True, null=True, help_text='ECG/EKG findings and interpretation')
    echocardiogram_results = models.TextField(blank=True, null=True, help_text='Echocardiogram results and findings')
    stress_test_results = models.TextField(blank=True, null=True, help_text='Stress test results and interpretation')
    cardiac_enzymes = models.TextField(blank=True, null=True, help_text='Cardiac enzyme levels (Troponin, CK-MB, etc.)')
    lipid_profile = models.TextField(blank=True, null=True, help_text='Lipid profile results (Total Cholesterol, HDL, LDL, Triglycerides)')
    blood_pressure_systolic = models.IntegerField(blank=True, null=True, help_text='Systolic blood pressure in mmHg')
    blood_pressure_diastolic = models.IntegerField(blank=True, null=True, help_text='Diastolic blood pressure in mmHg')
    heart_rate = models.IntegerField(blank=True, null=True, help_text='Heart rate in beats per minute')
    rhythm = models.CharField(max_length=50, blank=True, null=True, help_text='Cardiac rhythm (e.g., Normal Sinus, Atrial Fibrillation, Bradycardia)')
    ejection_fraction = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text='Ejection fraction percentage (e.g., 55.0)')
    
    diagnosis = models.CharField(max_length=100, blank=True, null=True, help_text='Primary diagnosis (e.g., Hypertension, Heart Failure, Arrhythmia, CAD)')
    treatment_plan = models.TextField(blank=True, null=True, help_text='Treatment plan and recommendations')
    
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)
    
    # Authorization Code
    authorization_code = models.CharField(max_length=50, blank=True, null=True, help_text="Authorization code from desk office")
    
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cardiology Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Cardiology Record'
        verbose_name_plural = 'Cardiology Records'


class CardiologyClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for cardiology records"""
    cardiology_record = models.ForeignKey(CardiologyRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='cardiology_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.cardiology_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Cardiology Clinical Note"
        verbose_name_plural = "Cardiology Clinical Notes"
