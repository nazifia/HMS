from django.contrib import admin
from .models import OphthalmicRecord

# Register your models here.
@admin.register(OphthalmicRecord)
class OphthalmicRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'visit_date', 'diagnosis', 'follow_up_required')
    list_filter = ('follow_up_required', 'visit_date', 'doctor')
    search_fields = ('patient__first_name', 'patient__last_name', 'diagnosis')
    readonly_fields = ('created_at', 'updated_at')