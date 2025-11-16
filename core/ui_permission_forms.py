"""
Forms for UI Permission Management
"""

from django import forms
from django.contrib.auth.models import Permission
from core.models import UIPermission, PermissionGroup
from accounts.models import Role


class UIPermissionForm(forms.ModelForm):
    """Form for creating and editing UI permissions"""

    required_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all().order_by('content_type__app_label', 'codename'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',
            'size': '10',
        }),
        help_text='Select the Django permissions required to access this UI element'
    )

    required_roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all().order_by('name'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',
            'size': '10',
        }),
        help_text='Select the roles that can access this UI element'
    )

    class Meta:
        model = UIPermission
        fields = [
            'element_id', 'element_label', 'element_type', 'module',
            'required_permissions', 'required_roles',
            'description', 'url_pattern', 'icon_class',
            'is_active', 'display_order'
        ]
        widgets = {
            'element_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., btn_create_patient, menu_pharmacy',
            }),
            'element_label': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Create Patient Button',
            }),
            'element_type': forms.Select(attrs={'class': 'form-control'}),
            'module': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detailed description of what this element does',
            }),
            'url_pattern': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., patients:register',
            }),
            'icon_class': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., fas fa-user-plus',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
        }

    def clean_element_id(self):
        """Validate element_id format"""
        element_id = self.cleaned_data['element_id']
        if not element_id:
            raise forms.ValidationError('Element ID is required')

        # Check format (alphanumeric, underscore, dash)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', element_id):
            raise forms.ValidationError(
                'Element ID can only contain letters, numbers, underscores, and dashes'
            )

        return element_id


class PermissionGroupForm(forms.ModelForm):
    """Form for creating and editing permission groups"""

    ui_permissions = forms.ModelMultipleChoiceField(
        queryset=UIPermission.objects.all().order_by('module', 'element_label'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',
            'size': '15',
        }),
        help_text='Select UI permissions to include in this group'
    )

    class Meta:
        model = PermissionGroup
        fields = ['name', 'description', 'module', 'ui_permissions', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Pharmacy Management',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description of this permission group',
            }),
            'module': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BulkUIPermissionAssignForm(forms.Form):
    """Form for bulk assigning UI permissions to roles"""

    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all().order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        help_text='Select roles to assign these permissions to'
    )

    ui_permissions = forms.ModelMultipleChoiceField(
        queryset=UIPermission.objects.filter(is_active=True).order_by('module', 'element_label'),
        widget=forms.CheckboxSelectMultiple,
        help_text='Select UI permissions to assign'
    )

    action = forms.ChoiceField(
        choices=[
            ('add', 'Add permissions to roles'),
            ('remove', 'Remove permissions from roles'),
            ('replace', 'Replace role permissions'),
        ],
        widget=forms.RadioSelect,
        initial='add',
    )


class UIPermissionFilterForm(forms.Form):
    """Form for filtering UI permissions"""

    module = forms.ChoiceField(
        choices=[('', 'All Modules')] + list(UIPermission.MODULE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    element_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(UIPermission.ELEMENT_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    is_active = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('true', 'Active'),
            ('false', 'Inactive'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by element ID or label...',
        }),
    )


class RoleUIPermissionForm(forms.Form):
    """Form for managing UI permissions for a specific role"""

    def __init__(self, *args, **kwargs):
        role = kwargs.pop('role', None)
        super().__init__(*args, **kwargs)

        if role:
            # Get all UI permissions grouped by module
            for module_key, module_label in UIPermission.MODULE_CHOICES:
                ui_perms = UIPermission.objects.filter(
                    module=module_key,
                    is_active=True
                ).order_by('display_order', 'element_label')

                if ui_perms.exists():
                    field_name = f'module_{module_key}'
                    self.fields[field_name] = forms.ModelMultipleChoiceField(
                        queryset=ui_perms,
                        required=False,
                        initial=role.ui_elements.filter(module=module_key),
                        widget=forms.CheckboxSelectMultiple,
                        label=module_label,
                    )
