from django.contrib import admin
from .models import Designation, Shift, StaffSchedule, Leave, Attendance, Payroll

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'created_at')
    list_filter = ('department',)
    search_fields = ('name', 'department__name')

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'shift_type', 'start_time', 'end_time')
    list_filter = ('shift_type',)
    search_fields = ('name', 'description')

@admin.register(StaffSchedule)
class StaffScheduleAdmin(admin.ModelAdmin):
    list_display = ('staff', 'shift', 'weekday', 'is_active')
    list_filter = ('weekday', 'shift', 'is_active')
    search_fields = ('staff__username', 'staff__first_name', 'staff__last_name')

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('staff', 'leave_type', 'start_date', 'end_date', 'status', 'get_duration')
    list_filter = ('leave_type', 'status', 'start_date')
    search_fields = ('staff__username', 'staff__first_name', 'staff__last_name', 'reason')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Leave Information', {
            'fields': ('staff', 'leave_type', 'start_date', 'end_date', 'reason', 'status')
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'approval_date', 'rejection_reason')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'time_in', 'time_out', 'status')
    list_filter = ('status', 'date')
    search_fields = ('staff__username', 'staff__first_name', 'staff__last_name', 'notes')
    date_hierarchy = 'date'

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('staff', 'month', 'year', 'basic_salary', 'allowances', 'deductions', 'net_salary', 'status')
    list_filter = ('status', 'month', 'year', 'payment_method')
    search_fields = ('staff__username', 'staff__first_name', 'staff__last_name')
    readonly_fields = ('net_salary',)
    fieldsets = (
        ('Staff Information', {
            'fields': ('staff', 'month', 'year')
        }),
        ('Salary Details', {
            'fields': ('basic_salary', 'allowances', 'deductions', 'net_salary')
        }),
        ('Payment Information', {
            'fields': ('payment_date', 'payment_method', 'status')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by')
        }),
    )
