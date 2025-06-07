from django.contrib import admin
from .models import Ward, Bed, Admission, DailyRound, NursingNote

class BedInline(admin.TabularInline):
    model = Bed
    extra = 0

class DailyRoundInline(admin.TabularInline):
    model = DailyRound
    extra = 0

class NursingNoteInline(admin.TabularInline):
    model = NursingNote
    extra = 0

@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ('name', 'ward_type', 'floor', 'capacity', 'charge_per_day', 'get_available_beds_count', 'is_active', 'primary_doctor')
    list_filter = ('ward_type', 'floor', 'is_active')
    search_fields = ('name', 'description')
    inlines = [BedInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'ward_type', 'floor', 'capacity', 'charge_per_day', 'is_active', 'primary_doctor', 'description')
        }),
    )

@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('bed_number', 'ward', 'is_occupied', 'is_active')
    list_filter = ('ward', 'is_occupied', 'is_active')
    search_fields = ('bed_number', 'ward__name')

@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'admission_date', 'discharge_date', 'bed', 'status', 'attending_doctor')
    list_filter = ('status', 'admission_date', 'discharge_date')
    search_fields = ('patient__first_name', 'patient__last_name', 'diagnosis', 'attending_doctor__username')
    date_hierarchy = 'admission_date'
    inlines = [DailyRoundInline, NursingNoteInline]
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient', 'status')
        }),
        ('Admission Details', {
            'fields': ('admission_date', 'discharge_date', 'bed', 'attending_doctor')
        }),
        ('Medical Information', {
            'fields': ('diagnosis', 'reason_for_admission', 'admission_notes', 'discharge_notes')
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

@admin.register(DailyRound)
class DailyRoundAdmin(admin.ModelAdmin):
    list_display = ('admission', 'date_time', 'doctor')
    list_filter = ('date_time', 'doctor')
    search_fields = ('admission__patient__first_name', 'admission__patient__last_name', 'notes')
    date_hierarchy = 'date_time'

@admin.register(NursingNote)
class NursingNoteAdmin(admin.ModelAdmin):
    list_display = ('admission', 'date_time', 'nurse')
    list_filter = ('date_time', 'nurse')
    search_fields = ('admission__patient__first_name', 'admission__patient__last_name', 'notes')
    date_hierarchy = 'date_time'
