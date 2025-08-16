
from django.contrib import admin
from .models import AuthorizationCode

@admin.register(AuthorizationCode)
class AuthorizationCodeAdmin(admin.ModelAdmin):
    list_display = ('patient', 'service', 'department', 'status', 'created_at')
    list_filter = ('status', 'department', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name', 'service')
