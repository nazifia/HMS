from django.contrib import admin
from .models import AuditLog, InternalNotification, SOAPNote

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp', 'user']
    search_fields = ['user__username', 'action', 'details']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']


@admin.register(InternalNotification)
class InternalNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at', 'read_at']


@admin.register(SOAPNote)
class SOAPNoteAdmin(admin.ModelAdmin):
    list_display = ['consultation', 'created_by', 'created_at']
    list_filter = ['created_at', 'created_by']
    search_fields = ['subjective', 'objective', 'assessment', 'plan']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['consultation', 'created_by']
