from django.contrib import admin
from django.utils.html import format_html
from .models import HMSPermission, RolePermissionAssignment, UserPermissionAssignment, SidebarMenuItem, FeatureFlag

@admin.register(HMSPermission)
class HMSPermissionAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'codename', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'codename', 'display_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('name', 'display_name', 'codename', 'description')
        }),
        ('Organization', {
            'fields': ('category', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers can only see active permissions
            qs = qs.filter(is_active=True)
        return qs


@admin.register(RolePermissionAssignment)
class RolePermissionAssignmentAdmin(admin.ModelAdmin):
    list_display = ['role', 'permission', 'granted_at', 'granted_by']
    list_filter = ['granted_at', 'permission__category']
    search_fields = ['role__name', 'permission__name']
    readonly_fields = ['granted_at']
    raw_id_fields = ['role', 'permission', 'granted_by']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers can only see assignments for their accessible permissions
            accessible_permissions = request.user.hms_permissions.values_list('permission__id', flat=True)
            qs = qs.filter(permission__id__in=accessible_permissions)
        return qs


@admin.register(UserPermissionAssignment)
class UserPermissionAssignmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'permission', 'granted_at', 'granted_by']
    list_filter = ['granted_at', 'permission__category']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'permission__name']
    readonly_fields = ['granted_at']
    raw_id_fields = ['user', 'permission', 'granted_by']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Users can only see their own permissions and permissions they granted
            qs = qs.filter(
                models.Q(user=request.user) | 
                models.Q(granted_by=request.user)
            )
        return qs


@admin.register(SidebarMenuItem)
class SidebarMenuItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'order', 'permission_required', 'is_active', 'url_name']
    list_filter = ['category', 'is_active', 'permission_required']
    search_fields = ['title', 'url_name', 'url_path']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['permission_required']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'url_name', 'url_path', 'icon')
        }),
        ('Organization', {
            'fields': ('category', 'parent', 'order', 'is_active')
        }),
        ('Permissions', {
            'fields': ('permission_required', 'required_roles'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers can only see active menu items
            qs = qs.filter(is_active=True)
        return qs


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'feature_type', 'permission_required', 'is_enabled', 'created_at']
    list_filter = ['feature_type', 'is_enabled', 'permission_required']
    search_fields = ['name', 'display_name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['permission_required']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'display_name', 'description')
        }),
        ('Configuration', {
            'fields': ('feature_type', 'permission_required', 'is_enabled')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers can only see enabled features
            qs = qs.filter(is_enabled=True)
        return qs


# Custom admin dashboard widgets
class HMSPermissionSummary:
    """Dashboard widget showing permission statistics"""
    
    def __init__(self, admin_site):
        self.admin_site = admin_site
    
    def get_context(self):
        from django.db.models import Count
        from accounts.models import Role, CustomUser
        
        context = {
            'total_permissions': HMSPermission.objects.count(),
            'active_permissions': HMSPermission.objects.filter(is_active=True).count(),
            'total_roles': Role.objects.count(),
            'total_role_assignments': RolePermissionAssignment.objects.count(),
            'total_user_assignments': UserPermissionAssignment.objects.count(),
            'sidebar_items': SidebarMenuItem.objects.filter(is_active=True).count(),
            'feature_flags': FeatureFlag.objects.count(),
            'enabled_features': FeatureFlag.objects.filter(is_enabled=True).count(),
        }
        
        # Permission distribution by category
        context['permissions_by_category'] = HMSPermission.objects.values(
            'category'
        ).annotate(
            count=Count('id')
        ).order_by('category')
        
        return context
