import math

from django.db import models
from saas.models import TenantModel
from core.clinical_notes import NigerianClerkingNote
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
from django.utils import timezone


class CardiologyRecord(TenantModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='cardiology_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    visit_date = models.DateTimeField(default=timezone.now)
    
    # Cardiology-specific fields
    chest_pain_type = models.CharField(max_length=50, blank=True, null=True, help_text='Type of chest pain (e.g., Angina, Myocardial Infarction, Non-cardiac)')

    # ECG structured measurements (used by compute_ecg)
    ECG_AXIS_CHOICES = (
        ('normal', 'Normal Axis (-30° to +90°)'),
        ('lad', 'Left Axis Deviation'),
        ('rad', 'Right Axis Deviation'),
        ('extreme', 'Extreme Axis Deviation'),
    )
    ecg_pr_interval = models.IntegerField(blank=True, null=True, help_text='PR interval in ms (normal 120-200)')
    ecg_qrs_duration = models.IntegerField(blank=True, null=True, help_text='QRS duration in ms (normal < 120)')
    ecg_qt_interval = models.IntegerField(blank=True, null=True, help_text='Measured QT interval in ms')
    ecg_qtc_interval = models.DecimalField(max_digits=6, decimal_places=1, blank=True, null=True, help_text='Corrected QT (Bazett), auto-calculated in ms')
    ecg_axis = models.CharField(max_length=10, choices=ECG_AXIS_CHOICES, blank=True, null=True, help_text='QRS electrical axis')
    ecg_interpretation = models.TextField(blank=True, null=True, help_text='Auto-generated ECG interpretation summary')

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

    def compute_ecg(self):
        """Derive QTc (Bazett) and an auto-interpretation from ECG measurements + vitals.

        Sets ecg_qtc_interval and ecg_interpretation. Safe to call repeatedly.
        Returns the list of interpretation lines.
        """
        findings = []

        # --- Rate ---
        hr = self.heart_rate
        if hr:
            if hr < 60:
                findings.append(f"Bradycardia (HR {hr} bpm).")
            elif hr > 100:
                findings.append(f"Tachycardia (HR {hr} bpm).")
            else:
                findings.append(f"Normal rate (HR {hr} bpm).")

        # --- Rhythm ---
        if self.rhythm:
            r = self.rhythm.lower()
            if 'fib' in r:
                findings.append("Atrial fibrillation pattern reported — irregularly irregular rhythm.")
            elif 'flutter' in r:
                findings.append("Atrial flutter pattern reported.")

        # --- PR interval ---
        pr = self.ecg_pr_interval
        if pr:
            if pr < 120:
                findings.append(f"Short PR interval ({pr} ms) — consider pre-excitation (e.g. WPW).")
            elif pr > 200:
                findings.append(f"Prolonged PR interval ({pr} ms) — first-degree AV block.")

        # --- QRS duration ---
        qrs = self.ecg_qrs_duration
        if qrs and qrs >= 120:
            findings.append(f"Wide QRS ({qrs} ms) — bundle branch block / IVCD.")

        # --- QTc (Bazett: QTc = QT / sqrt(RR)), RR in seconds from HR ---
        qtc = None
        if self.ecg_qt_interval and hr:
            rr = 60.0 / hr  # seconds
            qtc = self.ecg_qt_interval / math.sqrt(rr)
            self.ecg_qtc_interval = round(qtc, 1)

            # Sex-specific prolongation thresholds
            sex = getattr(self.patient, 'gender', None)
            upper = 470 if sex == 'F' else 450
            if qtc >= 500:
                findings.append(f"QTc {qtc:.0f} ms — markedly prolonged, high torsades risk.")
            elif qtc > upper:
                findings.append(f"QTc {qtc:.0f} ms — prolonged (threshold {upper} ms).")
            elif qtc < 350:
                findings.append(f"QTc {qtc:.0f} ms — short QT.")
            else:
                findings.append(f"QTc {qtc:.0f} ms — normal.")
        else:
            self.ecg_qtc_interval = None

        # --- Axis ---
        if self.ecg_axis and self.ecg_axis != 'normal':
            findings.append(f"{self.get_ecg_axis_display()}.")

        self.ecg_interpretation = "\n".join(findings) if findings else None
        return findings

    def save(self, *args, **kwargs):
        # Recompute ECG-derived values on every save
        if self.patient_id:
            self.compute_ecg()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cardiology Record for {self.patient.get_full_name()} - {self.visit_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Cardiology Record'
        verbose_name_plural = 'Cardiology Records'


class CardiologyClinicalNote(NigerianClerkingNote, TenantModel):
    """Nigerian clerking proforma clinical notes for cardiology records"""
    cardiology_record = models.ForeignKey(CardiologyRecord, on_delete=models.CASCADE, related_name='clinical_notes')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='cardiology_clinical_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinical Note for {self.cardiology_record.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Cardiology Clinical Note"
        verbose_name_plural = "Cardiology Clinical Notes"
