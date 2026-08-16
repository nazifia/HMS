from rest_framework import serializers

from ..models import (
    EquipmentUsage, OperationTheatre, PostOperativeNote, PreOperativeChecklist,
    Surgery, SurgeryType, SurgicalEquipment, SurgicalTeam,
)
from ..services import CHECKLIST_FIELDS, checklist_is_complete


class OperationTheatreSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationTheatre
        fields = [
            'id', 'name', 'theatre_number', 'floor', 'description',
            'is_available',
        ]


class SurgeryTypeSerializer(serializers.ModelSerializer):
    risk_level_display = serializers.CharField(
        source='get_risk_level_display', read_only=True
    )

    class Meta:
        model = SurgeryType
        fields = [
            'id', 'name', 'description', 'average_duration',
            'preparation_time', 'recovery_time', 'risk_level',
            'risk_level_display', 'instructions', 'fee',
        ]


class SurgicalEquipmentSerializer(serializers.ModelSerializer):
    equipment_type_display = serializers.CharField(
        source='get_equipment_type_display', read_only=True
    )

    class Meta:
        model = SurgicalEquipment
        fields = [
            'id', 'name', 'equipment_type', 'equipment_type_display',
            'description', 'quantity_available', 'is_available',
            'last_maintenance_date', 'next_maintenance_date',
        ]


class SurgicalTeamSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(
        source='staff.get_full_name', read_only=True
    )
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = SurgicalTeam
        fields = [
            'id', 'surgery', 'staff', 'staff_name', 'role', 'role_display',
            'usage_notes',
        ]


class EquipmentUsageSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(
        source='equipment.name', read_only=True
    )

    class Meta:
        model = EquipmentUsage
        fields = [
            'id', 'surgery', 'equipment', 'equipment_name', 'quantity_used',
            'notes',
        ]


class PostOperativeNoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = PostOperativeNote
        fields = [
            'id', 'surgery', 'notes', 'complications',
            'follow_up_instructions', 'created_by_name', 'created_at',
        ]
        read_only_fields = ['created_by']


class PreOperativeChecklistSerializer(serializers.ModelSerializer):
    completed_by_name = serializers.CharField(
        source='completed_by.get_full_name', read_only=True, default=''
    )
    is_complete = serializers.SerializerMethodField()
    outstanding = serializers.SerializerMethodField()

    class Meta:
        model = PreOperativeChecklist
        fields = [
            'id', 'surgery', *CHECKLIST_FIELDS, 'notes', 'completed_by_name',
            'completed_at', 'is_complete', 'outstanding',
        ]
        read_only_fields = ['surgery', 'completed_by']

    def get_is_complete(self, checklist):
        return checklist_is_complete(checklist)

    def get_outstanding(self, checklist):
        """The items still unticked, so the app can say what is missing."""
        return [
            name for name in CHECKLIST_FIELDS if not getattr(checklist, name)
        ]


class SurgerySerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    surgery_type_name = serializers.CharField(
        source='surgery_type.name', read_only=True
    )
    surgery_fee = serializers.DecimalField(
        source='surgery_type.fee', max_digits=10, decimal_places=2, read_only=True
    )
    theatre_name = serializers.CharField(
        source='theatre.name', read_only=True, default=''
    )
    surgeon_name = serializers.CharField(
        source='primary_surgeon.get_full_name', read_only=True, default=''
    )
    anesthetist_name = serializers.CharField(
        source='anesthetist.get_full_name', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    team_members = SurgicalTeamSerializer(many=True, read_only=True)
    equipment_used = EquipmentUsageSerializer(many=True, read_only=True)
    pre_op_checklist = PreOperativeChecklistSerializer(read_only=True)
    # Packs are already native under pharmacy; this is the link, not a copy.
    pack_orders = serializers.SerializerMethodField()
    # What the app is allowed to offer next.
    can_perform = serializers.SerializerMethodField()
    blocked_reason = serializers.SerializerMethodField()
    checklist_complete = serializers.SerializerMethodField()

    class Meta:
        model = Surgery
        fields = [
            'id', 'patient', 'patient_name', 'patient_number', 'surgery_type',
            'surgery_type_name', 'surgery_fee', 'theatre', 'theatre_name',
            'primary_surgeon', 'surgeon_name', 'anesthetist',
            'anesthetist_name', 'scheduled_date', 'expected_duration',
            'pre_surgery_notes', 'post_surgery_notes', 'status',
            'status_display', 'requires_authorization', 'authorization_status',
            'team_members', 'equipment_used', 'pre_op_checklist',
            'pack_orders', 'can_perform', 'blocked_reason',
            'checklist_complete',
        ]
        # Status moves through the workflow endpoints; the invoice and the
        # authorization code are settled when the surgery is booked.
        read_only_fields = [
            'status', 'authorization_status', 'requires_authorization',
        ]

    def _check(self, surgery):
        if not hasattr(surgery, '_perform_cache'):
            surgery._perform_cache = surgery.can_be_performed()
        return surgery._perform_cache

    def get_can_perform(self, surgery):
        return self._check(surgery)[0]

    def get_blocked_reason(self, surgery):
        can, message = self._check(surgery)
        return '' if can else message

    def get_checklist_complete(self, surgery):
        return checklist_is_complete(
            getattr(surgery, 'pre_op_checklist', None)
        )

    def get_pack_orders(self, surgery):
        return [
            {
                'id': order.id,
                'pack_name': order.pack.name,
                'status': order.status,
                'ordered_at': order.ordered_at,
            }
            for order in surgery.pack_orders.all()
        ]
