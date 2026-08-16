from rest_framework import serializers
from ..cart_models import PrescriptionCart, PrescriptionCartItem
from ..models import (
    ActiveStoreInventory, DispensingLog, Dispensary, InterDispensaryTransfer,
    Medication, MedicationCategory, MedicationTransfer, MedicalPack,
    MedicalPackItem, PackOrder, PharmacistDispensaryAssignment,
    PharmacyExpense, Purchase, PurchaseItem, PurchasePayment, Supplier,
    Prescription, PrescriptionItem,
)
from core.validators import normalize_nigerian_phone

class MedicationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicationCategory
        fields = ['id', 'name', 'description']

class MedicationSerializer(serializers.ModelSerializer):
    category = MedicationCategorySerializer(read_only=True)
    
    class Meta:
        model = Medication
        fields = [
            'id', 'name', 'generic_name', 'category', 'description', 
            'dosage_form', 'strength', 'manufacturer', 'price',
            'reorder_level', 'expiry_date', 'is_active'
        ]

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_person', 'email', 'phone_number',
            'address', 'city', 'state', 'country', 'is_active'
        ]

    def to_internal_value(self, data):
        # Normalize before field validation so max_length applies to the
        # normalized value (e.g. '+234 806 123 4567' -> '08061234567').
        if hasattr(data, 'get') and data.get('phone_number'):
            data = {**data, 'phone_number': normalize_nigerian_phone(data['phone_number'])}
        return super().to_internal_value(data)

class PrescriptionItemSerializer(serializers.ModelSerializer):
    medication = MedicationSerializer(read_only=True)
    
    class Meta:
        model = PrescriptionItem
        fields = [
            'id', 'medication', 'dosage', 'frequency', 'duration',
            'instructions', 'quantity', 'quantity_dispensed_so_far',
            'is_dispensed'
        ]

class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    # A list of patient/doctor ids is useless on a phone screen; ship the names.
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    doctor_name = serializers.CharField(
        source='doctor.get_full_name', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    payment_status_display = serializers.CharField(
        source='get_payment_status_display', read_only=True
    )

    class Meta:
        model = Prescription
        fields = [
            'id', 'patient', 'patient_name', 'patient_number', 'doctor',
            'doctor_name', 'prescription_date', 'diagnosis', 'status',
            'status_display', 'payment_status', 'payment_status_display',
            'prescription_type', 'notes', 'authorization_status',
            'created_at', 'updated_at', 'items'
        ]


class DispensarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispensary
        fields = ['id', 'name', 'location', 'is_active']


class MedicationStockSerializer(serializers.Serializer):
    """Per-dispensary stock for one medication."""
    dispensary_id = serializers.IntegerField()
    dispensary = serializers.CharField()
    stock_quantity = serializers.IntegerField()


class MedicalPackItemSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(
        source='medication.name', read_only=True
    )
    medication_strength = serializers.CharField(
        source='medication.strength', read_only=True, default=''
    )
    total_cost = serializers.DecimalField(
        source='get_total_cost', max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = MedicalPackItem
        fields = [
            'id', 'pack', 'medication', 'medication_name',
            'medication_strength', 'quantity', 'item_type',
            'usage_instructions', 'is_critical', 'is_optional', 'order',
            'total_cost',
        ]


class MedicalPackSerializer(serializers.ModelSerializer):
    items = MedicalPackItemSerializer(many=True, read_only=True)
    pack_type_display = serializers.CharField(
        source='get_pack_type_display', read_only=True
    )
    total_value = serializers.DecimalField(
        source='get_total_value', max_digits=12, decimal_places=2, read_only=True
    )
    item_count = serializers.IntegerField(source='get_item_count', read_only=True)

    class Meta:
        model = MedicalPack
        fields = [
            'id', 'name', 'description', 'pack_type', 'pack_type_display',
            'surgery_type', 'labor_type', 'risk_level', 'requires_approval',
            'is_active', 'total_value', 'item_count', 'items',
        ]


class PackOrderSerializer(serializers.ModelSerializer):
    pack_name = serializers.CharField(source='pack.name', read_only=True)
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    ordered_by_name = serializers.CharField(
        source='ordered_by.get_full_name', read_only=True, default=''
    )
    can_be_processed = serializers.BooleanField(read_only=True)
    can_be_approved = serializers.BooleanField(read_only=True)
    can_be_dispensed = serializers.BooleanField(read_only=True)

    class Meta:
        model = PackOrder
        fields = [
            'id', 'pack', 'pack_name', 'patient', 'patient_name', 'status',
            'status_display', 'ordered_by_name', 'ordered_at',
            'scheduled_date', 'order_notes', 'processing_notes',
            'approved_at', 'dispensed_at', 'authorization_code',
            'can_be_processed', 'can_be_approved', 'can_be_dispensed',
        ]
        read_only_fields = ['status', 'approved_at', 'dispensed_at']


class PharmacyExpenseSerializer(serializers.ModelSerializer):
    expense_type_display = serializers.CharField(
        source='get_expense_type_display', read_only=True
    )
    payment_status_display = serializers.CharField(
        source='get_payment_status_display', read_only=True
    )
    supplier_name = serializers.CharField(
        source='supplier.name', read_only=True, default=''
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = PharmacyExpense
        fields = [
            'id', 'expense_type', 'expense_type_display', 'description',
            'amount', 'expense_date', 'payment_status',
            'payment_status_display', 'supplier', 'supplier_name',
            'reference_number', 'notes', 'created_by_name', 'created_at',
        ]


class PharmacistAssignmentSerializer(serializers.ModelSerializer):
    pharmacist_name = serializers.CharField(
        source='pharmacist.get_full_name', read_only=True
    )
    dispensary_name = serializers.CharField(
        source='dispensary.name', read_only=True
    )

    class Meta:
        model = PharmacistDispensaryAssignment
        fields = [
            'id', 'pharmacist', 'pharmacist_name', 'dispensary',
            'dispensary_name', 'start_date', 'end_date', 'is_active', 'notes',
        ]
        read_only_fields = ['is_active']  # derived from end_date on save


class DispensaryWriteSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(
        source='manager.get_full_name', read_only=True, default=''
    )
    pharmacist_count = serializers.SerializerMethodField()

    class Meta:
        model = Dispensary
        fields = [
            'id', 'name', 'location', 'description', 'manager', 'manager_name',
            'is_active', 'pharmacist_count',
        ]

    def get_pharmacist_count(self, dispensary):
        return dispensary.pharmacist_assignments.filter(is_active=True).count()


class PurchaseItemSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(
        source='medication.name', read_only=True
    )
    medication_strength = serializers.CharField(
        source='medication.strength', read_only=True, default=''
    )
    quantity_outstanding = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchaseItem
        fields = [
            'id', 'purchase', 'medication', 'medication_name',
            'medication_strength', 'quantity', 'quantity_received',
            'quantity_outstanding', 'unit_price', 'total_price',
            'batch_number', 'expiry_date',
        ]
        read_only_fields = ['quantity_received', 'total_price']


class PurchasePaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(
        source='received_by.get_full_name', read_only=True, default=''
    )
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True
    )

    class Meta:
        model = PurchasePayment
        fields = [
            'id', 'amount', 'payment_date', 'payment_method',
            'payment_method_display', 'transaction_id', 'notes',
            'received_by_name',
        ]


class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True, read_only=True)
    payments = PurchasePaymentSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    approval_status_display = serializers.CharField(
        source='get_approval_status_display', read_only=True
    )
    payment_status_display = serializers.CharField(
        source='get_payment_status_display', read_only=True
    )
    delivery_status_display = serializers.CharField(
        source='get_delivery_status_display', read_only=True
    )
    amount_paid = serializers.DecimalField(
        source='get_amount_paid', max_digits=12, decimal_places=2, read_only=True
    )
    outstanding = serializers.DecimalField(
        source='get_outstanding_amount', max_digits=12, decimal_places=2,
        read_only=True,
    )
    # The app shows an action only when the server would allow it.
    can_be_approved = serializers.BooleanField(read_only=True)
    can_be_paid = serializers.BooleanField(read_only=True)
    can_receive_delivery = serializers.BooleanField(read_only=True)

    class Meta:
        model = Purchase
        fields = [
            'id', 'supplier', 'supplier_name', 'invoice_number',
            'purchase_date', 'total_amount', 'amount_paid', 'outstanding',
            'payment_status', 'payment_status_display', 'approval_status',
            'approval_status_display', 'approval_notes', 'delivery_status',
            'delivery_status_display', 'priority_level',
            'expected_delivery_date', 'actual_delivery_date', 'dispensary',
            'notes', 'created_at', 'can_be_approved', 'can_be_paid',
            'can_receive_delivery', 'items', 'payments',
        ]
        read_only_fields = [
            'total_amount', 'payment_status', 'approval_status',
            'delivery_status',
        ]


class ActiveStoreInventorySerializer(serializers.ModelSerializer):
    medication = MedicationSerializer(read_only=True)
    dispensary = serializers.IntegerField(
        source='active_store.dispensary_id', read_only=True
    )
    dispensary_name = serializers.CharField(
        source='active_store.dispensary.name', read_only=True
    )
    is_low_stock = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ActiveStoreInventory
        fields = [
            'id', 'medication', 'dispensary', 'dispensary_name',
            'stock_quantity', 'reorder_level', 'batch_number', 'expiry_date',
            'is_low_stock', 'is_expired', 'last_restock_date',
        ]


class TransferSerializerBase(serializers.ModelSerializer):
    """Shared display fields for both transfer models."""
    medication_name = serializers.CharField(
        source='medication.name', read_only=True
    )
    medication_strength = serializers.CharField(
        source='medication.strength', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    requested_by_name = serializers.CharField(
        source='requested_by.get_full_name', read_only=True, default=''
    )
    can_approve = serializers.BooleanField(read_only=True)
    can_execute = serializers.BooleanField(read_only=True)


class InterDispensaryTransferSerializer(TransferSerializerBase):
    from_dispensary_name = serializers.CharField(
        source='from_dispensary.name', read_only=True
    )
    to_dispensary_name = serializers.CharField(
        source='to_dispensary.name', read_only=True
    )
    can_reject = serializers.BooleanField(read_only=True)

    class Meta:
        model = InterDispensaryTransfer
        fields = [
            'id', 'medication', 'medication_name', 'medication_strength',
            'from_dispensary', 'from_dispensary_name', 'to_dispensary',
            'to_dispensary_name', 'quantity', 'status', 'status_display',
            'requested_by_name', 'rejection_reason', 'notes', 'created_at',
            'can_approve', 'can_reject', 'can_execute',
        ]
        read_only_fields = ['status', 'rejection_reason']


class MedicationTransferSerializer(TransferSerializerBase):
    """Bulk store -> active store."""
    from_bulk_store_name = serializers.CharField(
        source='from_bulk_store.name', read_only=True
    )
    to_dispensary_name = serializers.CharField(
        source='to_active_store.dispensary.name', read_only=True
    )

    class Meta:
        model = MedicationTransfer
        fields = [
            'id', 'medication', 'medication_name', 'medication_strength',
            'from_bulk_store', 'from_bulk_store_name', 'to_active_store',
            'to_dispensary_name', 'quantity', 'batch_number', 'status',
            'status_display', 'requested_by_name', 'notes', 'created_at',
            'can_approve', 'can_execute',
        ]
        read_only_fields = ['status']


class DispensingLogSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(
        source='prescription_item.medication.name', read_only=True
    )
    patient_name = serializers.CharField(
        source='prescription_item.prescription.patient.get_full_name',
        read_only=True,
    )
    dispensed_by_name = serializers.CharField(
        source='dispensed_by.get_full_name', read_only=True, default=''
    )
    dispensary_name = serializers.CharField(
        source='dispensary.name', read_only=True, default=''
    )

    class Meta:
        model = DispensingLog
        fields = [
            'id', 'medication_name', 'patient_name', 'dispensed_by_name',
            'dispensary_name', 'dispensed_quantity', 'unit_price_at_dispense',
            'total_price_for_this_log', 'dispensed_date',
        ]


class CartItemSerializer(serializers.ModelSerializer):
    medication = serializers.SerializerMethodField()
    prescribed_quantity = serializers.IntegerField(
        source='prescription_item.quantity', read_only=True
    )
    remaining = serializers.IntegerField(
        source='get_remaining_quantity', read_only=True
    )
    available_now = serializers.IntegerField(
        source='get_available_to_dispense_now', read_only=True
    )
    subtotal = serializers.DecimalField(
        source='get_subtotal', max_digits=12, decimal_places=2, read_only=True
    )
    patient_pays = serializers.DecimalField(
        source='get_patient_pays', max_digits=12, decimal_places=2, read_only=True
    )
    stock_status = serializers.CharField(source='get_stock_status', read_only=True)
    is_substituted = serializers.BooleanField(read_only=True)

    class Meta:
        model = PrescriptionCartItem
        fields = [
            'id', 'medication', 'prescribed_quantity', 'quantity',
            'quantity_dispensed', 'remaining', 'available_now',
            'available_stock', 'unit_price', 'subtotal', 'patient_pays',
            'stock_status', 'is_substituted', 'substitute_reason',
        ]

    def get_medication(self, item):
        # What will actually be handed over: the substitute if there is one.
        return MedicationSerializer(item.get_effective_medication()).data


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(
        source='prescription.patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='prescription.patient.patient_id', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    dispensary_name = serializers.CharField(
        source='dispensary.name', read_only=True, default=''
    )
    subtotal = serializers.DecimalField(
        source='get_subtotal', max_digits=12, decimal_places=2, read_only=True
    )
    patient_payable = serializers.DecimalField(
        source='get_patient_payable', max_digits=12, decimal_places=2, read_only=True
    )
    nhia_coverage = serializers.DecimalField(
        source='get_nhia_coverage', max_digits=12, decimal_places=2, read_only=True
    )
    progress = serializers.DictField(
        source='get_dispensing_progress', read_only=True
    )
    invoice_status = serializers.CharField(
        source='invoice.status', read_only=True, default=''
    )
    can_dispense = serializers.SerializerMethodField()
    dispense_blocked_reason = serializers.SerializerMethodField()

    class Meta:
        model = PrescriptionCart
        fields = [
            'id', 'prescription', 'patient_name', 'patient_number', 'status',
            'status_display', 'dispensary', 'dispensary_name', 'invoice',
            'invoice_status', 'subtotal', 'patient_payable', 'nhia_coverage',
            'progress', 'can_dispense', 'dispense_blocked_reason', 'notes',
            'created_at', 'items',
        ]

    def _dispensing_check(self, cart):
        if not hasattr(cart, '_dispensing_check_cache'):
            cart._dispensing_check_cache = cart.can_complete_dispensing()
        return cart._dispensing_check_cache

    def get_can_dispense(self, cart):
        return self._dispensing_check(cart)[0]

    def get_dispense_blocked_reason(self, cart):
        can, message = self._dispensing_check(cart)
        return '' if can else message