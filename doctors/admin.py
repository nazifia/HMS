from django.contrib import admin
from .models import (
    Specialization, Doctor, DoctorAvailability, DoctorLeave,
    DoctorEducation, DoctorExperience, DoctorReview
)

class DoctorAvailabilityInline(admin.TabularInline):
    model = DoctorAvailability
    extra = 1

class DoctorEducationInline(admin.TabularInline):
    model = DoctorEducation
    extra = 1

class DoctorExperienceInline(admin.TabularInline):
    model = DoctorExperience
    extra = 1

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'specialization', 'license_number', 'experience', 'available_for_appointments')
    list_filter = ('specialization', 'available_for_appointments', 'experience')
    search_fields = ('user__first_name', 'user__last_name', 'license_number')
    inlines = [DoctorAvailabilityInline, DoctorEducationInline, DoctorExperienceInline]

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Doctor Name'

@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(DoctorLeave)
class DoctorLeaveAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'start_date')
    search_fields = ('doctor__user__first_name', 'doctor__user__last_name')

@admin.register(DoctorReview)
class DoctorReviewAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'patient', 'rating', 'created_at', 'is_public')
    list_filter = ('rating', 'is_public', 'created_at')
    search_fields = ('doctor__user__first_name', 'doctor__user__last_name', 'patient__first_name', 'patient__last_name')
