from django.contrib import admin
from .models import ConsultingRoom, WaitingList, Consultation, ConsultationNote, Referral

class ConsultationNoteInline(admin.TabularInline):
    model = ConsultationNote
    extra = 0

class ReferralInline(admin.TabularInline):
    model = Referral
    extra = 0
    fk_name = 'consultation'
    fields = ('referral_type', 'referred_to_department', 'referred_to_specialty', 'referred_to_unit', 'reason', 'status')

@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'consulting_room', 'consultation_date', 'status')
    list_filter = ('status', 'consultation_date', 'doctor', 'consulting_room')
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__patient_id', 'doctor__username', 'doctor__first_name', 'doctor__last_name')
    date_hierarchy = 'consultation_date'
    inlines = [ConsultationNoteInline, ReferralInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('patient', 'doctor', 'consulting_room', 'waiting_list_entry', 'appointment', 'vitals')
        }),
        ('Consultation Details', {
            'fields': ('consultation_date', 'chief_complaint', 'symptoms', 'diagnosis', 'consultation_notes', 'status')
        }),
    )

@admin.register(ConsultationNote)
class ConsultationNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'consultation', 'created_by', 'created_at')
    list_filter = ('created_at', 'created_by')
    search_fields = ('consultation__patient__first_name', 'consultation__patient__last_name', 'note')

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'referring_doctor', 'get_referral_destination', 'referral_type', 'referral_date', 'status', 'assigned_doctor')
    list_filter = ('status', 'referral_type', 'referral_date', 'referring_doctor', 'referred_to_department', 'assigned_doctor')
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__patient_id', 'referring_doctor__username', 'assigned_doctor__username', 'referred_to_specialty', 'referred_to_unit')
    date_hierarchy = 'referral_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('patient', 'referring_doctor', 'consultation', 'referral_date', 'status')
        }),
        ('Referral Destination', {
            'fields': ('referral_type', 'referred_to_department', 'referred_to_specialty', 'referred_to_unit', 'assigned_doctor')
        }),
        ('Details', {
            'fields': ('reason', 'notes')
        }),
        ('Authorization', {
            'fields': ('requires_authorization', 'authorization_status', 'authorization_code'),
            'classes': ('collapse',)
        }),
    )
    
    def get_referral_destination(self, obj):
        """Display referral destination in admin list"""
        return obj.get_referral_destination()
    get_referral_destination.short_description = 'Referred To'

@admin.register(ConsultingRoom)
class ConsultingRoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'floor', 'department', 'is_active')
    list_filter = ('floor', 'department', 'is_active')
    search_fields = ('room_number', 'description')

@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
    list_display = ('patient', 'consulting_room', 'doctor', 'check_in_time', 'status', 'priority')
    list_filter = ('status', 'priority', 'consulting_room', 'doctor')
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__patient_id', 'doctor__username', 'notes')
    date_hierarchy = 'check_in_time'
