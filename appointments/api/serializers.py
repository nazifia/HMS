from rest_framework import serializers

from ..models import (
    Appointment, AppointmentFollowUp, DoctorLeave, DoctorSchedule,
)


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    doctor_name = serializers.CharField(
        source='doctor.get_full_name', read_only=True
    )
    department_name = serializers.CharField(
        source='department.name', read_only=True, default=''
    )
    consulting_room_name = serializers.CharField(
        source='consulting_room.__str__', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    is_today = serializers.BooleanField(read_only=True)
    is_past_due = serializers.BooleanField(read_only=True)
    # Reception needs to know whether the fee is settled before confirming.
    payment_verified = serializers.BooleanField(
        source='consultation_payment_verified', read_only=True
    )
    requires_authorization = serializers.BooleanField(
        source='is_nhia_patient', read_only=True
    )

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'patient_number', 'doctor',
            'doctor_name', 'department', 'department_name', 'consulting_room',
            'consulting_room_name', 'appointment_date', 'end_time', 'reason',
            'status', 'status_display', 'priority', 'notes', 'is_today',
            'is_past_due', 'payment_verified', 'requires_authorization',
            'authorization_code',
        ]
        # Status moves through the workflow endpoint, not a blind PATCH.
        read_only_fields = ['status', 'authorization_code']


class AppointmentFollowUpSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='appointment.patient.get_full_name', read_only=True
    )
    is_booked = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentFollowUp
        fields = [
            'id', 'appointment', 'patient_name', 'follow_up_date', 'notes',
            'booked_appointment', 'is_booked',
        ]
        read_only_fields = ['booked_appointment']

    def get_is_booked(self, follow_up):
        return follow_up.booked_appointment_id is not None


class DoctorScheduleSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(
        source='doctor.get_full_name', read_only=True
    )
    weekday_display = serializers.CharField(
        source='get_weekday_display', read_only=True
    )

    class Meta:
        model = DoctorSchedule
        fields = [
            'id', 'doctor', 'doctor_name', 'weekday', 'weekday_display',
            'start_time', 'end_time', 'is_available',
        ]


class DoctorLeaveSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(
        source='doctor.get_full_name', read_only=True
    )
    duration = serializers.IntegerField(read_only=True)

    class Meta:
        model = DoctorLeave
        fields = [
            'id', 'doctor', 'doctor_name', 'start_date', 'end_date', 'reason',
            'is_approved', 'duration',
        ]
        # Approving is a separate action, not a field the requester can set.
        read_only_fields = ['is_approved']
