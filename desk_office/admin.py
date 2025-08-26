from django.contrib import admin
from .models import AuthorizationCode

@admin.register(AuthorizationCode)
class AuthorizationCodeAdmin(admin.ModelAdmin):
    list_display = ('patient', 'service_type', 'department', 'status', 'created_at')
    list_filter = ('status', 'department', 'created_at', 'service_type')
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__patient_id', 'service_type', 'department')
    readonly_fields = ('code', 'created_at', 'used_at')
    list_per_page = 20