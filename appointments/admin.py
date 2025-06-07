from django.contrib import admin
from .models import Appointment, AppointmentFollowUp, DoctorSchedule, DoctorLeave

class AppointmentFollowUpInline(admin.TabularInline):
    model = AppointmentFollowUp
    extra = 0

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_date', 'appointment_time', 'status', 'priority')
    list_filter = ('status', 'priority', 'appointment_date', 'doctor')
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__username', 'reason')
    date_hierarchy = 'appointment_date'
    inlines = [AppointmentFollowUpInline]
    fieldsets = (
        ('Appointment Information', {
            'fields': ('patient', 'doctor', 'appointment_date', 'appointment_time', 'end_time')
        }),
        ('Details', {
            'fields': ('reason', 'status', 'priority', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

@admin.register(AppointmentFollowUp)
class AppointmentFollowUpAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'follow_up_date', 'created_by', 'created_at')
    list_filter = ('follow_up_date', 'created_at')
    search_fields = ('appointment__patient__first_name', 'appointment__patient__last_name', 'notes')
    date_hierarchy = 'follow_up_date'

@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'weekday', 'start_time', 'end_time', 'is_available')
    list_filter = ('weekday', 'is_available')
    search_fields = ('doctor__username', 'doctor__first_name', 'doctor__last_name')

@admin.register(DoctorLeave)
class DoctorLeaveAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'start_date', 'end_date', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'start_date')
    search_fields = ('doctor__username', 'doctor__first_name', 'doctor__last_name', 'reason')
    date_hierarchy = 'start_date'
