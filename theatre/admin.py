from django.contrib import admin
from .models import (
    OperationTheatre, 
    SurgeryType, 
    Surgery, 
    SurgicalTeam, 
    SurgicalEquipment,
    EquipmentUsage,
    SurgerySchedule,
    PostOperativeNote
)

@admin.register(OperationTheatre)
class OperationTheatreAdmin(admin.ModelAdmin):
    list_display = ('name', 'theatre_number', 'floor', 'is_available', 'last_sanitized')
    list_filter = ('is_available', 'floor')
    search_fields = ('name', 'theatre_number')


@admin.register(SurgeryType)
class SurgeryTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'average_duration', 'risk_level')
    list_filter = ('risk_level',)
    search_fields = ('name',)


@admin.register(Surgery)
class SurgeryAdmin(admin.ModelAdmin):
    list_display = ('patient', 'surgery_type', 'theatre', 'scheduled_date', 'status')
    list_filter = ('status', 'surgery_type', 'theatre')
    search_fields = ('patient__first_name', 'patient__last_name', 'surgery_type__name')
    date_hierarchy = 'scheduled_date'
    raw_id_fields = ('patient', 'primary_surgeon', 'anesthetist')


@admin.register(SurgicalTeam)
class SurgicalTeamAdmin(admin.ModelAdmin):
    list_display = ('surgery', 'staff', 'role')
    list_filter = ('role',)
    search_fields = ('surgery__patient__first_name', 'surgery__patient__last_name', 'staff__first_name', 'staff__last_name')


@admin.register(SurgicalEquipment)
class SurgicalEquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'equipment_type', 'is_available', 'last_maintenance_date')
    list_filter = ('equipment_type', 'is_available')
    search_fields = ('name',)


@admin.register(EquipmentUsage)
class EquipmentUsageAdmin(admin.ModelAdmin):
    list_display = ('surgery', 'equipment', 'quantity_used')
    list_filter = ('equipment',)
    search_fields = ('surgery__patient__first_name', 'surgery__patient__last_name', 'equipment__name')


@admin.register(SurgerySchedule)
class SurgeryScheduleAdmin(admin.ModelAdmin):
    list_display = ('surgery', 'start_time', 'end_time', 'status')
    list_filter = ('status',)
    search_fields = ('surgery__patient__first_name', 'surgery__patient__last_name')
    date_hierarchy = 'start_time'


@admin.register(PostOperativeNote)
class PostOperativeNoteAdmin(admin.ModelAdmin):
    list_display = ('surgery', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('surgery__patient__first_name', 'surgery__patient__last_name', 'notes')
    date_hierarchy = 'created_at'
    raw_id_fields = ('surgery', 'created_by')