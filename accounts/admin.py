from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser, Role





from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create an admin user'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help='Username for the admin user')
        parser.add_argument('--phone', type=str, required=True, help='Phone number for the admin user')
        parser.add_argument('--email', type=str, required=True, help='Email for the admin user')
        parser.add_argument('--password', type=str, required=True, help='Password for the admin user')

    def handle(self, *args, **options):
        username = options['username']
        phone = options['phone']
        email = options['email']
        password = options['password']

        try:
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'User with username "{username}" already exists.')
                )
                return

            # Create the admin user
            user = User.objects.create_user(
                username=username,
                email=email,
                phone=phone,
                password=password
            )
            user.is_staff = True
            user.is_superuser = True
            user.save()

            self.stdout.write(
                self.style.SUCCESS(f'Admin user "{username}" created successfully.')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating user: {e}')
            )
            


class AdminAuthenticationForm(AuthenticationForm):
    """
    Independent admin authentication form that uses standard Django username field.
    This separates admin authentication from the custom phone number authentication.
    """
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        # Use standard username field for admin authentication
        self.fields['username'].label = "Username"
        self.fields['username'].help_text = "Enter your admin username"

class CustomUserAdmin(BaseUserAdmin):
    """
    Admin interface for CustomUser model.
    Simplified to focus only on essential user management without role coupling.
    """
    list_display = ('username', 'phone_number', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'phone_number', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    fieldsets = (
        (None, {'fields': ('username', 'phone_number', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'description': 'Admin permissions are independent of application roles'
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'phone_number', 'password1', 'password2', 'is_staff', 'is_active'),
            'description': 'Create admin users independently of application roles'
        }),
    )

    def get_queryset(self, request):
        """Only show staff users in admin interface"""
        qs = super().get_queryset(request)
        return qs.filter(is_staff=True)

# Use independent admin authentication
admin.site.login_form = AdminAuthenticationForm
admin.site.register(CustomUser, CustomUserAdmin)

# Role model registration (kept separate from user management)
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Admin interface for application roles.
    These are separate from Django admin permissions.
    """
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

    def get_model_perms(self, request):
        """
        Only superusers can manage application roles to maintain separation
        """
        if request.user.is_superuser:
            return super().get_model_perms(request)
        return {}

from .models import CustomUserProfile, Department

@admin.register(CustomUserProfile)
class CustomUserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for user profiles.
    Focused on data management, not role assignment.
    """
    list_display = ('user', 'employee_id', 'department', 'phone_number', 'is_active')
    list_filter = ('is_active', 'joining_date', 'department')
    search_fields = ('user__username', 'user__phone_number', 'user__email', 'employee_id', 'phone_number')
    date_hierarchy = 'joining_date'
    readonly_fields = ('joining_date', 'updated_at')

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'employee_id', 'phone_number')
        }),
        ('Profile Details', {
            'fields': ('address', 'profile_picture', 'date_of_birth', 'department', 'specialization', 'qualification')
        }),
        ('Status', {
            'fields': ('is_active', 'joining_date', 'updated_at')
        }),
    )

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """
    Admin interface for departments.
    Independent of role management.
    """
    list_display = ('name', 'head', 'created_at')
    search_fields = ('name', 'head__username', 'head__first_name', 'head__last_name')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
