from django.contrib import admin
from .models import NeurologyService, NeurologyRecord, NeurologyPrescription, NeurologyTest, NeurologyClinicalNote

class NeurologyServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)

class NeurologyRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'condition_type', 'treatment_status', 'created_at')
    list_filter = ('condition_type', 'treatment_status', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__patient_id', 'diagnosis')
    raw_id_fields = ('patient', 'service', 'neurologist')
    ordering = ('-created_at',)

class NeurologyPrescriptionAdmin(admin.ModelAdmin):
    list_display = ('neurology_record', 'medication', 'prescribed_at')
    list_filter = ('prescribed_at',)
    search_fields = ('neurology_record__patient__first_name', 'neurology_record__patient__last_name', 'medication')
    raw_id_fields = ('neurology_record', 'prescribed_by')
    ordering = ('-prescribed_at',)

class NeurologyTestAdmin(admin.ModelAdmin):
    list_display = ('neurology_record', 'test_type', 'performed_at')
    list_filter = ('test_type', 'performed_at')
    search_fields = ('neurology_record__patient__first_name', 'neurology_record__patient__last_name', 'test_type')
    raw_id_fields = ('neurology_record', 'performed_by')
    ordering = ('-performed_at',)

class NeurologyClinicalNoteAdmin(admin.ModelAdmin):
    list_display = ('neurology_record', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('neurology_record__patient__first_name', 'neurology_record__patient__last_name', 'subjective', 'assessment')
    raw_id_fields = ('neurology_record', 'created_by')
    ordering = ('-created_at',)

admin.site.register(NeurologyService, NeurologyServiceAdmin)
admin.site.register(NeurologyRecord, NeurologyRecordAdmin)
admin.site.register(NeurologyPrescription, NeurologyPrescriptionAdmin)
admin.site.register(NeurologyTest, NeurologyTestAdmin)
admin.site.register(NeurologyClinicalNote, NeurologyClinicalNoteAdmin)
