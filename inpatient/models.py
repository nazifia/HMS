from django.db import models
from django.utils import timezone
from django.conf import settings
from patients.models import Patient, PatientWallet
from decimal import Decimal

class Ward(models.Model):
    WARD_TYPE_CHOICES = (
        ('general', 'General Ward'),
        ('private', 'Private Ward'),
        ('semi_private', 'Semi-Private Ward'),
        ('icu', 'Intensive Care Unit'),
        ('nicu', 'Neonatal ICU'),
        ('picu', 'Pediatric ICU'),
        ('emergency', 'Emergency Ward'),
        ('maternity', 'Maternity Ward'),
        ('pediatric', 'Pediatric Ward'),
        ('psychiatric', 'Psychiatric Ward'),
        ('isolation', 'Isolation Ward'),
        ('a_and_e', 'A & E'),
        ('epu', 'EPU'),
        ('g_e', 'G/E (Gynaecology emergency)'),
        ('scbu', 'SCBU'),
        # ('icu', 'Intensive Care Unit'), # Already exists
        ('theater', 'Theater'),
        ('nhia', 'NHIA (For Insurance)'), # This ward type is for categorization, NHIA patients can be admitted to any ward.
        ('opthalmic', 'Opthalmic'),
        ('ent', 'ENT'),
        ('dental', 'Dental'),
        ('gopd', 'GOPD'),
        ('anc', 'ANC'),
        ('oncology', 'Oncology'),
        ('physiotherapy', 'Physiotherapy'),
        ('retainership', 'Retainership'),
        ('arvc', 'ARVC'),
    )

    name = models.CharField(max_length=100)
    ward_type = models.CharField(max_length=20, choices=WARD_TYPE_CHOICES)
    floor = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    capacity = models.IntegerField()  # Total number of beds
    charge_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    primary_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='primary_wards', help_text='Primary doctor responsible for this ward')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_ward_type_display()})"

    def get_available_beds_count(self):
        return self.beds.filter(is_occupied=False, is_active=True).count()

    def get_occupied_beds_count(self):
        return self.beds.filter(is_occupied=True, is_active=True).count()

class Bed(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='beds')
    bed_number = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    is_occupied = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)  # For maintenance or decommissioning
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "Occupied" if self.is_occupied else "Available"
        return f"Bed {self.bed_number} in {self.ward.name} - {status}"

    class Meta:
        unique_together = ('ward', 'bed_number')

class Admission(models.Model):
    STATUS_CHOICES = (
        ('admitted', 'Admitted'),
        ('discharged', 'Discharged'),
        ('transferred', 'Transferred'),
        ('deceased', 'Deceased'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='admissions', db_index=True)
    admission_date = models.DateTimeField(default=timezone.now, db_index=True)
    discharge_date = models.DateTimeField(blank=True, null=True, db_index=True)
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, related_name='admissions', db_index=True)
    diagnosis = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='admitted', db_index=True)
    attending_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attending_admissions', db_index=True)
    reason_for_admission = models.TextField()
    admission_notes = models.TextField(blank=True, null=True)
    discharge_notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_admissions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    billed_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bed_history = models.ManyToManyField(Bed, through='BedTransfer', related_name='admission_history', through_fields=('admission', 'to_bed'))
    ward_history = models.ManyToManyField(Ward, through='WardTransfer', related_name='admission_history', through_fields=('admission', 'to_ward'))

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.admission_date.strftime('%Y-%m-%d')}"

    def get_duration(self):
        if self.discharge_date:
            return (self.discharge_date - self.admission_date).days
        return (timezone.now() - self.admission_date).days

    def get_total_cost(self):
        """Calculate the total cost of the admission based on duration and bed charges"""
        duration = self.get_duration()
        if duration < 1:
            duration = 1  # Minimum 1 day charge

        if self.bed and self.bed.ward:
            daily_charge = self.bed.ward.charge_per_day
            return daily_charge * duration  # Return as a positive value
        return 0

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_instance = None

        if not is_new:
            try:
                old_instance = Admission.objects.get(pk=self.pk)
            except Admission.DoesNotExist:
                pass

        # Calculate billed_amount before saving
        self.billed_amount = self.get_total_cost()

        super().save(*args, **kwargs) # Save the instance first to ensure it has a PK

        # Update bed status when admission is created or status changes
        if is_new and self.bed and self.status == 'admitted':
            self.bed.is_occupied = True
            self.bed.save()
        elif old_instance and old_instance.status == 'admitted' and self.status != 'admitted':
            if self.bed:
                self.bed.is_occupied = False
                self.bed.save()

        # No redirect from model save method

class DailyRound(models.Model):
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='daily_rounds')
    date_time = models.DateTimeField(default=timezone.now)
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_rounds')
    notes = models.TextField()
    treatment_instructions = models.TextField(blank=True, null=True)
    medication_instructions = models.TextField(blank=True, null=True)
    diet_instructions = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Round for {self.admission.patient.get_full_name()} on {self.date_time.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-date_time']

class NursingNote(models.Model):
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='nursing_notes')
    date_time = models.DateTimeField(default=timezone.now)
    nurse = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nurse_notes')
    notes = models.TextField()
    vital_signs = models.TextField(blank=True, null=True)
    medication_given = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Nursing note for {self.admission.patient.get_full_name()} on {self.date_time.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-date_time']

class BedTransfer(models.Model):
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='bed_transfers')
    from_bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='transfers_from')
    to_bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='transfers_to')
    transfer_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Transfer for {self.admission.patient.get_full_name()} from {self.from_bed} to {self.to_bed}"

class WardTransfer(models.Model):
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='ward_transfers')
    from_ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='transfers_from')
    to_ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='transfers_to')
    transfer_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Transfer for {self.admission.patient.get_full_name()} from {self.from_ward} to {self.to_ward}"

class ClinicalRecord(models.Model):
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='clinical_records')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    record_type = models.CharField(max_length=50, choices=(
        ('vitals', 'Vital Signs'),
        ('medication', 'Medication Administration'),
        ('treatment', 'Treatment Plan'),
        ('progress', 'Progress Note'),
        ('other', 'Other'),
    ))
    date_time = models.DateTimeField(default=timezone.now)
    notes = models.TextField()
    # Fields for vital signs
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    respiratory_rate = models.IntegerField(null=True, blank=True)
    oxygen_saturation = models.IntegerField(null=True, blank=True)
    # Fields for medication administration
    medication_name = models.CharField(max_length=255, null=True, blank=True)
    dosage = models.CharField(max_length=100, null=True, blank=True)
    route = models.CharField(max_length=100, null=True, blank=True)
    # Fields for treatment plan
    treatment_description = models.TextField(null=True, blank=True)
    # Fields for progress note
    patient_condition = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_record_type_display()} for {self.admission.patient.get_full_name()} on {self.date_time.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-date_time']