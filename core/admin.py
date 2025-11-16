from django.contrib import admin
from .models import AuditLog, InternalNotification, SOAPNote, UIPermission, PermissionGroup

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


@admin.register(UIPermission)
class UIPermissionAdmin(admin.ModelAdmin):
    list_display = ['element_id', 'element_label', 'element_type', 'module', 'is_active', 'is_system', 'display_order']
    list_filter = ['module', 'element_type', 'is_active', 'is_system']
    search_fields = ['element_id', 'element_label', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    filter_horizontal = ['required_permissions', 'required_roles']

    fieldsets = (
        ('Basic Information', {
            'fields': ('element_id', 'element_label', 'element_type', 'module')
        }),
        ('Access Control', {
            'fields': ('required_permissions', 'required_roles')
        }),
        ('Configuration', {
            'fields': ('description', 'url_pattern', 'icon_class')
        }),
        ('Status', {
            'fields': ('is_active', 'is_system', 'display_order')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PermissionGroup)
class PermissionGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'is_active', 'created_at']
    list_filter = ['module', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['ui_permissions']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'module', 'description')
        }),
        ('Permissions', {
            'fields': ('ui_permissions',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
