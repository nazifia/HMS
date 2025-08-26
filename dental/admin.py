from django.contrib import admin
from .models import DentalRecord, DentalService, DentalPrescription, DentalXRay

@admin.register(DentalService)
class DentalServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_active')

@admin.register(DentalRecord)
class DentalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'service', 'tooth', 'treatment_status', 'dentist', 'created_at')
    list_filter = ('treatment_status', 'service', 'tooth', 'dentist', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__patient_id', 'diagnosis')
    date_hierarchy = 'created_at'
    raw_id_fields = ('patient', 'service', 'dentist', 'invoice', 'authorization_code')

@admin.register(DentalPrescription)
class DentalPrescriptionAdmin(admin.ModelAdmin):
    list_display = ('dental_record', 'medication', 'dosage', 'prescribed_by', 'prescribed_at', 'is_active')
    list_filter = ('is_active', 'prescribed_at')
    search_fields = ('medication', 'dental_record__patient__first_name', 'dental_record__patient__last_name')
    raw_id_fields = ('dental_record', 'prescribed_by')

@admin.register(DentalXRay)
class DentalXRayAdmin(admin.ModelAdmin):
    list_display = ('dental_record', 'xray_type', 'taken_by', 'taken_at')
    list_filter = ('xray_type', 'taken_at')
    search_fields = ('dental_record__patient__first_name', 'dental_record__patient__last_name')
    raw_id_fields = ('dental_record', 'taken_by')