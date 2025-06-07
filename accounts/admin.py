from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, Role
from .forms import CustomUserCreationForm, CustomUserChangeForm

# class CustomUserAdmin(BaseUserAdmin):
#     form = CustomUserChangeForm
#     add_form = CustomUserCreationForm

#     list_display = ('phone_number', 'email', 'first_name', 'last_name', 'is_staff')
#     fieldsets = BaseUserAdmin.fieldsets + (
#         (None, {'fields': ('roles',)}), # Add 'roles' field to the admin
#     )
#     add_fieldsets = BaseUserAdmin.add_fieldsets + (
#         (None, {'fields': ('roles',)}),
#     )
#     ordering = ('phone_number',)

class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ('username', 'phone_number', 'email', 'first_name', 'last_name', 'is_staff')

    # Replace fieldsets entirely, removing 'username'
    fieldsets = (
        (None, {'fields': ('username', 'phone_number', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'roles', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'phone_number', 'password1', 'password2', 'roles', 'is_staff', 'is_active')}
        ),
    )

    ordering = ('phone_number',)

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Role)
# admin.site.register(CustomUser, CustomUserAdmin)
# admin.site.register(Role)

from .models import CustomUserProfile, Department

@admin.register(CustomUserProfile)
class CustomUserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department', 'phone_number', 'is_active')
    list_filter = ('is_active', 'joining_date')
    search_fields = ('user__phone_number', 'user__email', 'employee_id', 'phone_number')
    date_hierarchy = 'joining_date'

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'head', 'created_at')
    search_fields = ('name', 'head__phone_number')
