from rest_framework import serializers

from core.clinical_notes import CLERKING_FIELDS

from ..models import (
    Consultation, ConsultationNote, ConsultingRoom, Referral, SOAPNote,
    WaitingList,
)


class ConsultingRoomSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source='department.name', read_only=True, default=''
    )

    class Meta:
        model = ConsultingRoom
        fields = ['id', 'room_number', 'floor', 'department',
                  'department_name', 'description', 'is_active']


class WaitingListSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    room_number = serializers.CharField(
        source='consulting_room.room_number', read_only=True
    )
    doctor_name = serializers.CharField(
        source='doctor.get_full_name', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model = WaitingList
        fields = [
            'id', 'patient', 'patient_name', 'patient_number',
            'consulting_room', 'room_number', 'clinic_type', 'doctor',
            'doctor_name', 'appointment', 'check_in_time', 'status',
            'status_display', 'priority', 'notes',
        ]
        # Status moves through the queue actions, not a blind PATCH.
        read_only_fields = ['status']


class ConsultationNoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )

    class Meta:
        model = ConsultationNote
        fields = ['id', 'consultation', 'note', 'created_by_name', 'created_at']


class ConsultationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    doctor_name = serializers.CharField(
        source='doctor.get_full_name', read_only=True, default=''
    )
    room_number = serializers.CharField(
        source='consulting_room.room_number', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    notes_log = ConsultationNoteSerializer(
        source='notes', many=True, read_only=True
    )

    class Meta:
        model = Consultation
        fields = [
            'id', 'patient', 'patient_name', 'patient_number', 'doctor',
            'doctor_name', 'appointment', 'consulting_room', 'room_number',
            'waiting_list_entry', 'vitals', 'clinic_type', 'consultation_date',
            'chief_complaint', 'symptoms', 'diagnosis', 'consultation_notes',
            'status', 'status_display', 'requires_authorization',
            'authorization_status', 'authorization_code', 'notes_log',
        ]
        # Authorization state is derived on save; status has its own endpoint.
        read_only_fields = [
            'status', 'requires_authorization', 'authorization_status',
        ]


class SOAPNoteSerializer(serializers.ModelSerializer):
    """The Nigerian clerking proforma. Every section is optional — a review
    visit may only update the management plan."""
    patient_name = serializers.CharField(
        source='consultation.patient.get_full_name', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True, default=''
    )
    # Only the sections that were filled in, in clinical order, for display.
    sections = serializers.SerializerMethodField()

    class Meta:
        model = SOAPNote
        fields = [
            'id', 'consultation', 'patient_name', 'created_by_name',
            'created_at', 'updated_at', 'sections', *CLERKING_FIELDS,
        ]

    def get_sections(self, note):
        return [
            {'label': label, 'value': value}
            for label, value in note.clerking_sections
        ]


class ReferralSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    referring_doctor_name = serializers.CharField(
        source='referring_doctor.get_full_name', read_only=True
    )
    assigned_doctor_name = serializers.CharField(
        source='assigned_doctor.get_full_name', read_only=True, default=''
    )
    destination = serializers.CharField(
        source='get_referral_destination', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    # Whether this caller may accept it, so the app only offers what will work.
    can_accept = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = [
            'id', 'consultation', 'patient', 'patient_name', 'patient_number',
            'referring_doctor', 'referring_doctor_name', 'referral_type',
            'referred_to_department', 'referred_to_specialty',
            'referred_to_unit', 'referred_to_ward', 'referred_to_doctor',
            'assigned_doctor', 'assigned_doctor_name', 'destination', 'reason',
            'notes', 'status', 'status_display', 'referral_date',
            'requires_authorization', 'authorization_status', 'can_accept',
        ]
        read_only_fields = [
            'status', 'assigned_doctor', 'referring_doctor',
            'requires_authorization', 'authorization_status',
        ]

    def get_can_accept(self, referral):
        request = self.context.get('request')
        if request is None:
            return False
        return referral.can_be_accepted_by(request.user)
