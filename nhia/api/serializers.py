from rest_framework import serializers

from ..models import AuthorizationCode, NHIAPatient
from ..services import AUTHORIZABLE


class AuthorizationCodeSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    nhia_number = serializers.CharField(
        source='patient.nhia_info.nhia_reg_number', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    service_type_display = serializers.CharField(
        source='get_service_type_display', read_only=True
    )
    generated_by_name = serializers.CharField(
        source='generated_by.get_full_name', read_only=True, default=''
    )
    is_usable = serializers.BooleanField(source='is_valid', read_only=True)

    class Meta:
        model = AuthorizationCode
        fields = [
            'id', 'code', 'patient', 'patient_name', 'patient_number',
            'nhia_number', 'service_type', 'service_type_display', 'amount',
            'expiry_date', 'status', 'status_display', 'notes',
            'generated_by_name', 'generated_at', 'used_at', 'used_for',
            'is_usable',
        ]
        # The code, its status and who issued it are the server's to set.
        read_only_fields = [
            'code', 'status', 'generated_at', 'used_at', 'used_for',
        ]


class NHIAPatientSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )

    class Meta:
        model = NHIAPatient
        fields = [
            'id', 'patient', 'patient_name', 'patient_number',
            'nhia_reg_number', 'is_active', 'date_registered',
        ]


class PendingItemSerializer(serializers.Serializer):
    """One thing waiting on the desk office, whichever module it came from.

    The six models have nothing in common but the authorization fields, so the
    queue is flattened here rather than given six shapes to handle.
    """

    kind = serializers.CharField()
    kind_display = serializers.CharField()
    id = serializers.IntegerField()
    patient = serializers.IntegerField()
    patient_name = serializers.CharField()
    patient_number = serializers.CharField()
    description = serializers.CharField()
    requested_on = serializers.DateTimeField(allow_null=True)
    estimated_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    authorization_status = serializers.CharField()


KIND_LABELS = {
    'consultation': 'Consultation',
    'referral': 'Referral',
    'prescription': 'Prescription',
    'laboratory': 'Lab request',
    'radiology': 'Radiology order',
    'surgery': 'Surgery',
}

# Where each model keeps the date the request was raised.
KIND_DATE_FIELDS = {
    'consultation': 'consultation_date',
    'referral': 'referral_date',
    'prescription': 'prescription_date',
    'laboratory': 'request_date',
    'radiology': 'order_date',
    'surgery': 'scheduled_date',
}


def describe(kind, item):
    """A line the desk office can act on without opening the record."""
    if kind == 'consultation':
        return f"{item.chief_complaint or 'Consultation'} · {item.consulting_room or ''}".strip(' ·')
    if kind == 'referral':
        return f"To {item.get_referral_destination()}"
    if kind == 'prescription':
        return item.diagnosis or 'Prescription'
    if kind == 'laboratory':
        return ', '.join(item.tests.values_list('name', flat=True)) or 'Lab request'
    if kind == 'radiology':
        return getattr(item.test, 'name', 'Radiology order')
    if kind == 'surgery':
        return getattr(item.surgery_type, 'name', 'Surgery')
    return KIND_LABELS.get(kind, kind)


def pending_row(kind, item):
    from ..services import estimated_amount

    date_field = KIND_DATE_FIELDS.get(kind)
    return {
        'kind': kind,
        'kind_display': KIND_LABELS.get(kind, kind),
        'id': item.pk,
        'patient': item.patient_id,
        'patient_name': item.patient.get_full_name(),
        'patient_number': item.patient.patient_id,
        'description': describe(kind, item),
        'requested_on': getattr(item, date_field, None) if date_field else None,
        'estimated_amount': estimated_amount(kind, item),
        'authorization_status': item.authorization_status,
    }
