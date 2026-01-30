from django.db import models
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class EmergencyRecord(models.Model):
    TRIAGE_LEVELS = (
        ('resuscitation', 'Resuscitation (Immediate)'),
        ('emergency', 'Emergency (Within 10 min)'),
        ('urgent', 'Urgent (Within 30 min)'),
        ('less_urgent', 'Less Urgent (Within 1 hour)'),
        ('non_urgent', 'Non-Urgent (Within 2 hours)'),
    )
    
    STATUS_CHOICES = (
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('under_observation', 'Under Observation'),
        ('admitted', 'Admitted'),
        ('discharged', 'Discharged'),
        ('transferred', 'Transferred'),
        ('died', 'Died'),
    )
    
    MODE_OF_ARRIVAL = (
        ('ambulance', 'Ambulance'),
        ('private_vehicle', 'Private Vehicle'),
        ('walk_in', 'Walk-in'),
        ('police', 'Police'),
        ('other', 'Other'),
    )
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='emergency_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    arrival_time = models.DateTimeField(default=timezone.now)
    
    # Triage Information
    triage_level = models.CharField(max_length=20, choices=TRIAGE_LEVELS, default='urgent')
    triage_notes = models.TextField(blank=True, null=True)
    
    # Arrival Information
    mode_of_arrival = models.CharField(max_length=20, choices=MODE_OF_ARRIVAL, default='walk_in')
    brought_by = models.CharField(max_length=100, blank=True, null=True, help_text='Name of person who brought patient')
    
    # Vital Signs on Arrival
    temperature = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    pulse_rate = models.IntegerField(blank=True, null=True)
    respiratory_rate = models.IntegerField(blank=True, null=True)
    blood_pressure_systolic = models.IntegerField(blank=True, null=True)
    blood_pressure_diastolic = models.IntegerField(blank=True, null=True)
    oxygen_saturation = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    gcs_score = models.IntegerField(blank=True, null=True, help_text='Glasgow Coma Scale score')
    
    # Clinical Information
    chief_complaint = models.TextField()
    history_of_present_illness = models.TextField(blank=True, null=True)
    past_medical_history = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    medications = models.TextField(blank=True, null=True)
    
    # Examination Findings
    general_appearance = models.TextField(blank=True, null=True)
    physical_examination = models.TextField(blank=True, null=True)
    
    # Diagnosis and Management
    primary_diagnosis = models.TextField(blank=True, null=True)
    secondary_diagnosis = models.TextField(blank=True, null=True)
    investigations_done = models.TextField(blank=True, null=True)
    treatment_given = models.TextField(blank=True, null=True)
    
    # Status and Outcome
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    discharge_time = models.DateTimeField(blank=True, null=True)
    discharge_diagnosis = models.TextField(blank=True, null=True)
    discharge_medications = models.TextField(blank=True, null=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_instructions = models.TextField(blank=True, null=True)
    
    # Authorization Code
    authorization_code = models.CharField(max_length=50, blank=True, null=True, help_text="Authorization code from desk office")
    
    # Referrals
    referred_to_department = models.ForeignKey('accounts.Department', on_delete=models.SET_NULL, null=True, blank=True)
    referral_reason = models.TextField(blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Emergency Record for {self.patient.get_full_name()} - {self.arrival_time.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-arrival_time']
        verbose_name = 'Emergency Record'
        verbose_name_plural = 'Emergency Records'


class EmergencyClinicalNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) clinical notes for emergency records"""
    emergency_record = models.ForeignKey(EmergencyRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    subjective = models.TextField(help_text="Patient's description of symptoms, concerns, and history")
    objective = models.TextField(help_text="Observable findings, examination results, and measurements")
    assessment = models.TextField(help_text="Clinical assessment, diagnosis, and interpretation")
    plan = models.TextField(help_text="Treatment plan, interventions, and follow-up")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='emergency_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.emergency_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Emergency Clinical Note"
        verbose_name_plural = "Emergency Clinical Notes"
