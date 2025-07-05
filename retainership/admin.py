from django.contrib import admin
from .models import RetainershipPatient

@admin.register(RetainershipPatient)
class RetainershipPatientAdmin(admin.ModelAdmin):
    list_display = ('patient_full_name', 'retainership_reg_number', 'is_active', 'date_registered')
    search_fields = ('patient__first_name', 'patient__last_name', 'retainership_reg_number')
    list_filter = ('is_active', 'date_registered')
    raw_id_fields = ('patient',)

    def patient_full_name(self, obj):
        return obj.patient.get_full_name()
    patient_full_name.admin_order_field = 'patient__last_name'
    patient_full_name.short_description = 'Patient Name'
