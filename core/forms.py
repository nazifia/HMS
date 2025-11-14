from django import forms
from django.contrib.auth.models import User
from .models import HMSPermission, RolePermissionAssignment, UserPermissionAssignment, SidebarMenuItem, FeatureFlag
from accounts.models import Role, CustomUser


class HMSPermissionForm(forms.ModelForm):
    """
    Form for creating and editing HMS Custom Permissions
    """
    
    class Meta:
        model = HMSPermission
        fields = ['name', 'display_name', 'codename', 'description', 'category', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Internal permission name'
            }),
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Human-readable permission name'
            }),
            'codename': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'System identifier (e.g., view_dashboard)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detailed description of what this permission allows'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_codename(self):
        codename = self.cleaned_data.get('codename')
        if codename:
            # Ensure codename only contains alphanumeric characters and underscores
            import re
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', codename):
                raise forms.ValidationError('Codename can only contain letters, numbers, and underscores.')
            
            # Check for uniqueness (excluding current instance in edit mode)
            if self.instance.pk:
                if HMSPermission.objects.exclude(pk=self.instance.pk).filter(codename=codename).exists():
                    raise forms.ValidationError('A permission with this codename already exists.')
            else:
                if HMSPermission.objects.filter(codename=codename).exists():
                    raise forms.ValidationError('A permission with this codename already exists.')
        
        return codename
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check for uniqueness (excluding current instance in edit mode)
            if self.instance.pk:
                if HMSPermission.objects.exclude(pk=self.instance.pk).filter(name=name).exists():
                    raise forms.ValidationError('A permission with this name already exists.')
            else:
                if HMSPermission.objects.filter(name=name).exists():
                    raise forms.ValidationError('A permission with this name already exists.')
        
        return name


class RolePermissionAssignmentForm(forms.ModelForm):
    """
    Form for assigning HMS Permissions to Roles
    """
    
    class Meta:
        model = RolePermissionAssignment
        fields = ['role', 'permission']
        widgets = {
            'role': forms.Select(attrs={
                'class': 'form-select'
            }),
            'permission': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active permissions
        self.fields['permission'].queryset = HMSPermission.objects.filter(is_active=True).order_by('display_name')
        self.fields['role'].queryset = Role.objects.all().order_by('name')
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        permission = cleaned_data.get('permission')
        
        if role and permission:
            # Check if this assignment already exists
            if RolePermissionAssignment.objects.filter(role=role, permission=permission).exists():
                raise forms.ValidationError(
                    f'This permission is already assigned to the role "{role.name}".'
                )
        
        return cleaned_data


class UserPermissionAssignmentForm(forms.ModelForm):
    """
    Form for directly assigning HMS Permissions to Users
    """
    
    class Meta:
        model = UserPermissionAssignment
        fields = ['user', 'permission', 'reason']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-select'
            }),
            'permission': forms.Select(attrs={
                'class': 'form-select'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for direct permission assignment (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active permissions
        self.fields['permission'].queryset = HMSPermission.objects.filter(is_active=True).order_by('display_name')
        self.fields['user'].queryset = CustomUser.objects.all().order_by('username')
    
    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        permission = cleaned_data.get('permission')
        
        if user and permission:
            # Check if this assignment already exists
            if UserPermissionAssignment.objects.filter(user=user, permission=permission).exists():
                raise forms.ValidationError(
                    f'This permission is already directly assigned to user "{user.username}".'
                )
        
        return cleaned_data


class SidebarMenuItemForm(forms.ModelForm):
    """
    Form for creating and editing Sidebar Menu Items
    """
    
    class Meta:
        model = SidebarMenuItem
        fields = [
            'title', 'url_name', 'url_path', 'icon', 'category', 
            'parent', 'order', 'is_active', 'permission_required', 'required_roles'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Menu item title'
            }),
            'url_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Django URL name (e.g., dashboard:dashboard)'
            }),
            'url_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Static URL path (if no URL name)'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Font Awesome icon class (e.g., fas fa-tachometer-alt)'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'parent': forms.Select(attrs={
                'class': 'form-select'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'permission_required': forms.Select(attrs={
                'class': 'form-select'
            }),
            'required_roles': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active permissions for requirement
        self.fields['permission_required'].queryset = HMSPermission.objects.filter(is_active=True).order_by('display_name')
        self.fields['required_roles'].queryset = Role.objects.all().order_by('name')
        # Exclude current item from parent choices to prevent circular references
        if self.instance.pk:
            self.fields['parent'].queryset = SidebarMenuItem.objects.exclude(pk=self.instance.pk)
        else:
            self.fields['parent'].queryset = SidebarMenuItem.objects.all()
    
    def clean(self):
        cleaned_data = super().clean()
        url_name = cleaned_data.get('url_name')
        url_path = cleaned_data.get('url_path')
        
        if not url_name and not url_path:
            raise forms.ValidationError('Either URL name or URL path must be provided.')
        
        return cleaned_data


class FeatureFlagForm(forms.ModelForm):
    """
    Form for creating and editing Feature Flags
    """
    
    class Meta:
        model = FeatureFlag
        fields = ['name', 'display_name', 'description', 'feature_type', 'permission_required', 'is_enabled']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Feature flag name (e.g., enhanced_pharmacy_workflow)'
            }),
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Human-readable feature name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description of the feature'
            }),
            'feature_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'permission_required': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['permission_required'].queryset = HMSPermission.objects.filter(is_active=True).order_by('display_name')
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check for uniqueness (excluding current instance in edit mode)
            if self.instance.pk:
                if FeatureFlag.objects.exclude(pk=self.instance.pk).filter(name=name).exists():
                    raise forms.ValidationError('A feature flag with this name already exists.')
            else:
                if FeatureFlag.objects.filter(name=name).exists():
                    raise forms.ValidationError('A feature flag with this name already exists.')
        
        return name


class PermissionBulkUpdateForm(forms.Form):
    """
    Form for bulk permission updates
    """
    ACTION_CHOICES = [
        ('assign', 'Assign Permissions'),
        ('remove', 'Remove Permissions'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Action'
    )
    
    target_type = forms.ChoiceField(
        choices=[('role', 'Roles'), ('user', 'Users')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Target Type'
    )
    
    permission_ids = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Permissions'
    )
    
    target_ids = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Targets'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate permission choices
        self.fields['permission_ids'].choices = [
            (p.id, f"{p.display_name} ({p.codename})") 
            for p in HMSPermission.objects.filter(is_active=True).order_by('display_name')
        ]
        
        # Will be populated based on target_type via JavaScript
        self.fields['target_ids'].choices = []


class PermissionSearchForm(forms.Form):
    """
    Form for searching and filtering permissions
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search permissions...',
            'autocomplete': 'off'
        })
    )
    
    category = forms.ChoiceField(
        choices=[('', 'All Categories')] + list(HMSPermission.PERMISSION_CATEGORIES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
