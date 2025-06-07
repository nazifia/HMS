from django.contrib import admin
from .models import Patient, MedicalHistory, Vitals, PatientWallet, WalletTransaction

class MedicalHistoryInline(admin.TabularInline):
    model = MedicalHistory
    extra = 0

class VitalsInline(admin.TabularInline):
    model = Vitals
    extra = 0

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_id', 'first_name', 'last_name', 'gender', 'phone_number', 'registration_date', 'is_active', 'primary_doctor')
    list_filter = ('gender', 'blood_group', 'is_active', 'registration_date')
    search_fields = ('patient_id', 'first_name', 'last_name', 'phone_number', 'email')
    date_hierarchy = 'registration_date'
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'gender', 'blood_group', 'marital_status', 'profile_picture')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone_number', 'address', 'city', 'state', 'postal_code', 'country')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_relation', 'emergency_contact_phone')
        }),
        ('Medical Information', {
            'fields': ('patient_id', 'registration_date', 'allergies', 'chronic_diseases', 'current_medications', 'primary_doctor')
        }),
        ('Insurance Information', {
            'fields': ('insurance_provider', 'insurance_policy_number', 'insurance_expiry_date')
        }),
        ('Additional Information', {
            'fields': ('occupation', 'notes', 'is_active')
        }),
    )
    readonly_fields = ('registration_date',)
    inlines = [MedicalHistoryInline, VitalsInline]

@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ('patient', 'diagnosis', 'date', 'doctor_name')
    list_filter = ('date',)
    search_fields = ('patient__first_name', 'patient__last_name', 'diagnosis', 'doctor_name')
    date_hierarchy = 'date'

@admin.register(Vitals)
class VitalsAdmin(admin.ModelAdmin):
    list_display = ('patient', 'date_time', 'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'pulse_rate')
    list_filter = ('date_time',)
    search_fields = ('patient__first_name', 'patient__last_name')
    date_hierarchy = 'date_time'


@admin.register(PatientWallet)
class PatientWalletAdmin(admin.ModelAdmin):
    list_display = ['patient', 'balance', 'is_active', 'created_at', 'last_updated']
    list_filter = ['is_active', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__patient_id']
    readonly_fields = ['created_at', 'last_updated']

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['patient']
        return self.readonly_fields


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'transaction_type', 'amount', 'balance_after', 'status', 'created_at', 'created_by']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['wallet__patient__first_name', 'wallet__patient__last_name', 'description', 'reference_number']
    readonly_fields = ['reference_number', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['wallet', 'transaction_type', 'amount', 'balance_after']
        return self.readonly_fields
