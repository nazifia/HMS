"""
Admin interface configuration for accounts app.

Provides enhanced admin interfaces for:
- CustomUser with inline role assignment
- Role with permission statistics and inheritance visualization
- CustomUserProfile
- Department
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AuthenticationForm
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from .models import CustomUser, Role, CustomUserProfile, Department


# ============================================================================
# Admin Authentication Form
# ============================================================================


class AdminAuthenticationForm(AuthenticationForm):
    """
    Independent admin authentication form that uses standard Django username field.
    This separates admin authentication from the custom phone number authentication.
    """

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        # Use standard username field for admin authentication
        self.fields["username"].label = "Username"
        self.fields["username"].help_text = "Enter your admin username"


# ============================================================================
# Inline Role Assignment for CustomUser
# ============================================================================


class RoleInline(admin.TabularInline):
    """Inline for assigning roles to users."""

    model = CustomUser.roles.through
    extra = 1
    verbose_name = "Role"
    verbose_name_plural = "Roles"
    classes = ["collapse"]

    def get_queryset(self, request):
        """Only show roles that are not system-internal."""
        return super().get_queryset(request).select_related("role")


# ============================================================================
# CustomUser Admin - Enhanced
# ============================================================================


class CustomUserAdmin(BaseUserAdmin):
    """
    Enhanced admin interface for CustomUser.

    Features:
    - Shows role badges
    - Inline role assignment
    - Quick actions
    - Staff-only filtering
    """

    list_display = (
        "username",
        "phone_number",
        "email",
        "get_full_name",
        "get_role_badges",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "date_joined",
        "roles",  # Filter by role
    )
    search_fields = (
        "username",
        "phone_number",
        "email",
        "first_name",
        "last_name",
        "profile__employee_id",
    )
    ordering = ("username",)
    inlines = [RoleInline]

    fieldsets = (
        (None, {"fields": ("username", "phone_number", "password")}),
        ("Personal Information", {"fields": ("first_name", "last_name", "email")}),
        (
            "Roles",
            {
                "fields": ("roles",),
                "description": "Application roles assigned to this user. Use Ctrl/Cmd to select multiple roles.",
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "description": "Django authentication permissions. Note: Application permissions are managed via roles.",
            },
        ),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "phone_number",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
                "description": "Create new user. Roles can be assigned after creation.",
            },
        ),
    )

    def get_queryset(self, request):
        """Show all users, but can be filtered by is_staff."""
        return (
            super()
            .get_queryset(request)
            .select_related("profile")
            .prefetch_related("roles")
        )

    def get_role_badges(self, obj):
        """Display role badges in list view."""
        roles = obj.roles.all()
        if not roles:
            return format_html('<span class="text-muted">No roles</span>')

        badges = []
        from accounts.permissions import get_role_badge_class, get_role_display_name

        for role in roles:
            badge_class = get_role_badge_class(role.name)
            display_name = get_role_display_name(role.name)
            badges.append(f'<span class="badge {badge_class}">{display_name}</span>')
        return mark_safe(" ".join(badges))

    get_role_badges.short_description = "Roles"
    get_role_badges.allow_tags = True

    def get_full_name(self, obj):
        """Display full name or username."""
        name = obj.get_full_name()
        if name and name != f"User #{obj.pk}":
            return name
        return obj.username

    get_full_name.short_description = "Name"


# ============================================================================
# Role Admin - Enhanced
# ============================================================================


class RoleAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Role model.

    Features:
    - Shows permission count, user count, inheritance info
    - Filter by parent role
    - Search by name and description
    - Permission assignment via filter_horizontal
    - Read-only statistics
    """

    list_display = (
        "name",
        "description",
        "get_permission_count",
        "get_user_count",
        "get_parent_role",
        "get_child_count",
        "get_inherited_permission_count",
    )
    list_filter = ("parent",)
    search_fields = ("name", "description")
    filter_horizontal = ("permissions",)
    readonly_fields = (
        "get_permission_count",
        "get_user_count",
        "get_inherited_permission_count",
        "get_child_count",
        "get_all_permissions_list",
    )

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("name", "description", "parent"),
                "description": "Role name and hierarchical parent relationship (for inheritance).",
            },
        ),
        (
            "Permissions",
            {
                "fields": ("permissions",),
                "description": "Select permissions to assign to this role. Child roles inherit permissions from parent.",
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "get_permission_count",
                    "get_inherited_permission_count",
                    "get_user_count",
                    "get_child_count",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "All Permissions (Read-Only)",
            {"fields": ("get_all_permissions_list",), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        """Optimize queries with prefetch."""
        return (
            super()
            .get_queryset(request)
            .prefetch_related("permissions", "customuser_roles", "children")
        )

    def get_permission_count(self, obj):
        """Count of directly assigned permissions."""
        return obj.permissions.count()

    get_permission_count.short_description = "Direct Permissions"

    def get_inherited_permission_count(self, obj):
        """Count of permissions inherited from parent roles."""
        return len(obj.get_all_permissions()) - obj.permissions.count()

    get_inherited_permission_count.short_description = "Inherited Permissions"

    def get_user_count(self, obj):
        """Count of users assigned to this role."""
        return obj.customuser_roles.count()

    get_user_count.short_description = "Assigned Users"

    def get_parent_role(self, obj):
        """Display parent role as link."""
        if obj.parent:
            url = reverse("admin:accounts_role_change", args=[obj.parent.pk])
            return format_html('<a href="{}">{}</a>', url, obj.parent.name)
        return "-"

    get_parent_role.short_description = "Parent Role"
    get_parent_role.allow_tags = True

    def get_child_count(self, obj):
        """Count of child roles."""
        return obj.children.count()

    get_child_count.short_description = "Child Roles"

    def get_all_permissions_list(self, obj):
        """Display all permissions (including inherited) as a list."""
        all_perms = obj.get_all_permissions()
        perms_list = sorted(
            [f"{p.content_type.app_label}.{p.codename}" for p in all_perms]
        )
        if perms_list:
            return format_html("<pre>{}</pre>", "\n".join(perms_list[:50]))
        return "-"

    get_all_permissions_list.short_description = "All Permissions (Direct + Inherited)"
    get_all_permissions_list.allow_tags = True

    def get_model_perms(self, request):
        """
        Only superusers can manage application roles to maintain separation.
        """
        if request.user.is_superuser:
            return super().get_model_perms(request)
        return {}


# ============================================================================
# CustomUserProfile Admin
# ============================================================================


@admin.register(CustomUserProfile)
class CustomUserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for user profiles.

    Focused on profile data management, not authentication or roles.
    """

    list_display = (
        "user",
        "employee_id",
        "get_role_from_profile",
        "department",
        "phone_number",
        "is_active",
        "joining_date",
    )
    list_filter = (
        "is_active",
        "joining_date",
        "department",
    )
    search_fields = (
        "user__username",
        "user__phone_number",
        "user__email",
        "employee_id",
        "phone_number",
    )
    date_hierarchy = "joining_date"
    readonly_fields = ("joining_date", "updated_at")

    fieldsets = (
        ("User", {"fields": ("user",)}),
        (
            "Employment Information",
            {
                "fields": (
                    "employee_id",
                    "department",
                    "specialization",
                    "qualification",
                )
            },
        ),
        (
            "Contact Details",
            {"fields": ("phone_number", "address", "profile_picture", "date_of_birth")},
        ),
        ("Status", {"fields": ("is_active", "joining_date", "updated_at")}),
    )

    def get_role_from_profile(self, obj):
        """Display legacy profile role if set."""
        if obj.role:
            return obj.get_role_display()
        return "-"

    get_role_from_profile.short_description = "Legacy Profile Role"

    def get_queryset(self, request):
        """Optimize queries."""
        return super().get_queryset(request).select_related("user")


# ============================================================================
# Department Admin
# ============================================================================


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """
    Admin interface for departments.
    """

    list_display = ("name", "head", "created_at")
    search_fields = ("name", "head__username", "head__first_name", "head__last_name")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("head")


# ============================================================================
# Admin Site Configuration
# ============================================================================

# Use independent admin authentication (separate from phone-based auth)
admin.site.login_form = AdminAuthenticationForm
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Role, RoleAdmin)

# Site title and branding
admin.site.site_header = "HMS Administration"
admin.site.site_title = "HMS Admin"
admin.site.index_title = "Hospital Management System Admin"
