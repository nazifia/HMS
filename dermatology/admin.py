from django.contrib import admin
from .models import DermatologyService, DermatologyRecord, DermatologyPrescription, DermatologyTest, DermatologyClinicalNote

class DermatologyServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)

class DermatologyRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'condition_type', 'treatment_status', 'created_at')
    list_filter = ('condition_type', 'treatment_status', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__patient_id', 'diagnosis')
    raw_id_fields = ('patient', 'service', 'dermatologist')
    ordering = ('-created_at',)

class DermatologyPrescriptionAdmin(admin.ModelAdmin):
    list_display = ('dermatology_record', 'medication', 'prescribed_at')
    list_filter = ('prescribed_at',)
    search_fields = ('dermatology_record__patient__first_name', 'dermatology_record__patient__last_name', 'medication')
    raw_id_fields = ('dermatology_record', 'prescribed_by')
    ordering = ('-prescribed_at',)

class DermatologyTestAdmin(admin.ModelAdmin):
    list_display = ('dermatology_record', 'test_type', 'performed_at')
    list_filter = ('test_type', 'performed_at')
    search_fields = ('dermatology_record__patient__first_name', 'dermatology_record__patient__last_name', 'test_type')
    raw_id_fields = ('dermatology_record', 'performed_by')
    ordering = ('-performed_at',)

class DermatologyClinicalNoteAdmin(admin.ModelAdmin):
    list_display = ('dermatology_record', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('dermatology_record__patient__first_name', 'dermatology_record__patient__last_name', 'subjective', 'assessment')
    raw_id_fields = ('dermatology_record', 'created_by')
    ordering = ('-created_at',)

admin.site.register(DermatologyService, DermatologyServiceAdmin)
admin.site.register(DermatologyRecord, DermatologyRecordAdmin)
admin.site.register(DermatologyPrescription, DermatologyPrescriptionAdmin)
admin.site.register(DermatologyTest, DermatologyTestAdmin)
admin.site.register(DermatologyClinicalNote, DermatologyClinicalNoteAdmin)
