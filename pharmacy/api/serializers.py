from rest_framework import serializers
from ..models import Medication, MedicationCategory, Supplier, Prescription, PrescriptionItem

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
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'patient', 'doctor', 'prescription_date', 'diagnosis',
            'status', 'payment_status', 'prescription_type', 'notes',
            'created_at', 'updated_at', 'items'
        ]