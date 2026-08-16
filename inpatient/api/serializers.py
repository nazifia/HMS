from rest_framework import serializers

from ..models import (
    Admission, Bed, ClinicalRecord, DailyRound, InpatientMedication,
    NursingNote, Ward,
)


class WardSerializer(serializers.ModelSerializer):
    ward_type_display = serializers.CharField(
        source='get_ward_type_display', read_only=True
    )
    total_beds = serializers.IntegerField(source='beds.count', read_only=True)
    available_beds = serializers.IntegerField(
        source='get_available_beds_count', read_only=True
    )
    occupied_beds = serializers.IntegerField(
        source='get_occupied_beds_count', read_only=True
    )

    class Meta:
        model = Ward
        fields = [
            'id', 'name', 'ward_type', 'ward_type_display', 'floor',
            'description', 'capacity', 'charge_per_day', 'is_active',
            'total_beds', 'available_beds', 'occupied_beds',
        ]


class BedSerializer(serializers.ModelSerializer):
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = Bed
        fields = [
            'id', 'ward', 'ward_name', 'bed_number', 'description',
            'is_occupied', 'is_active', 'patient_name',
        ]

    def get_patient_name(self, bed):
        """Who is in it, so the bed map does not need a second call."""
        current = getattr(bed, 'current_admissions_list', None)
        if current is None:
            current = list(bed.admissions.filter(status='admitted')[:1])
        return current[0].patient.get_full_name() if current else ''


class DailyRoundSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(
        source='doctor.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = DailyRound
        fields = [
            'id', 'admission', 'date_time', 'doctor', 'doctor_name', 'notes',
            'treatment_instructions', 'medication_instructions',
            'diet_instructions',
        ]
        read_only_fields = ['doctor']


class NursingNoteSerializer(serializers.ModelSerializer):
    nurse_name = serializers.CharField(
        source='nurse.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = NursingNote
        fields = [
            'id', 'admission', 'date_time', 'nurse', 'nurse_name', 'notes',
            'vital_signs', 'medication_given',
        ]
        read_only_fields = ['nurse']


class ClinicalRecordSerializer(serializers.ModelSerializer):
    record_type_display = serializers.CharField(
        source='get_record_type_display', read_only=True
    )
    recorded_by_name = serializers.CharField(
        source='recorded_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = ClinicalRecord
        fields = [
            'id', 'admission', 'record_type', 'record_type_display',
            'date_time', 'notes', 'temperature', 'blood_pressure_systolic',
            'blood_pressure_diastolic', 'heart_rate', 'respiratory_rate',
            'oxygen_saturation', 'medication_name', 'dosage', 'route',
            'treatment_description', 'patient_condition', 'recorded_by_name',
        ]
        read_only_fields = ['recorded_by']


class InpatientMedicationSerializer(serializers.ModelSerializer):
    ordered_by_name = serializers.CharField(
        source='ordered_by.get_full_name', read_only=True, default=''
    )
    total_cost = serializers.DecimalField(
        source='get_total_cost', max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = InpatientMedication
        fields = [
            'id', 'admission', 'prescription', 'ordered_by', 'ordered_by_name',
            'order_date', 'is_paid', 'payment_source', 'notes', 'total_cost',
        ]
        read_only_fields = ['ordered_by']


class AdmissionSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    doctor_name = serializers.CharField(
        source='attending_doctor.get_full_name', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    bed_number = serializers.CharField(
        source='bed.bed_number', read_only=True, default=''
    )
    ward_name = serializers.CharField(
        source='bed.ward.name', read_only=True, default=''
    )
    ward = serializers.IntegerField(source='bed.ward_id', read_only=True)
    duration_days = serializers.IntegerField(
        source='get_duration', read_only=True
    )
    total_cost = serializers.DecimalField(
        source='get_total_cost', max_digits=12, decimal_places=2, read_only=True
    )
    outstanding_cost = serializers.DecimalField(
        source='get_outstanding_admission_cost', max_digits=12,
        decimal_places=2, read_only=True,
    )
    # What the app may offer next.
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Admission
        fields = [
            'id', 'patient', 'patient_name', 'patient_number',
            'admission_date', 'discharge_date', 'bed', 'bed_number', 'ward',
            'ward_name', 'diagnosis', 'status', 'status_display',
            'attending_doctor', 'doctor_name', 'reason_for_admission',
            'admission_notes', 'discharge_notes', 'authorization_code',
            'duration_days', 'total_cost', 'outstanding_cost', 'is_active',
        ]
        # Bed, status and dates move through the workflow endpoints, not by
        # editing the row: a bed swapped here would leave both beds wrong.
        read_only_fields = [
            'bed', 'status', 'admission_date', 'discharge_date',
            'authorization_code',
        ]

    def get_is_active(self, admission):
        return admission.status == 'admitted'


class AdmissionChargesSerializer(serializers.Serializer):
    """The money view of one admission, as the wards and billing office see it."""

    billed = serializers.DecimalField(max_digits=12, decimal_places=2)
    paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding = serializers.DecimalField(max_digits=12, decimal_places=2)
    wallet_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    wallet_impact = serializers.DecimalField(max_digits=12, decimal_places=2)
    daily_charge = serializers.DecimalField(max_digits=12, decimal_places=2)
    duration_days = serializers.IntegerField()
