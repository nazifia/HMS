"""
Forms for User Activity Monitoring
"""
from django import forms
from django.contrib.auth import get_user_model
from .models import UserActivity, ActivityAlert, UserSession

User = get_user_model()


class ActivityFilterForm(forms.Form):
    """Form for filtering user activities"""
    
    ACTION_TYPES = [('', 'All')] + UserActivity.ACTION_TYPES
    ACTIVITY_LEVELS = [('', 'All')] + UserActivity.ACTIVITY_LEVELS
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    action_type = forms.ChoiceField(
        choices=ACTION_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    activity_level = forms.ChoiceField(
        choices=ACTIVITY_LEVELS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search activities...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values to empty to show placeholder
        self.fields['user'].empty_label = 'All Users'
        self.fields['action_type'].empty_label = 'All Actions'
        self.fields['activity_level'].empty_label = 'All Levels'


class AlertFilterForm(forms.Form):
    """Form for filtering activity alerts"""
    
    ALERT_TYPES = [('', 'All')] + ActivityAlert.ALERT_TYPES
    SEVERITY_LEVELS = [('', 'All')] + ActivityAlert.SEVERITY_LEVELS
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    alert_type = forms.ChoiceField(
        choices=ALERT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    severity = forms.ChoiceField(
        choices=SEVERITY_LEVELS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_resolved = forms.ChoiceField(
        choices=[
            ('', 'All Status'),
            ('true', 'Resolved'),
            ('false', 'Open'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['user'].empty_label = 'All Users'
        self.fields['alert_type'].empty_label = 'All Alert Types'
        self.fields['severity'].empty_label = 'All Severities'


class SessionFilterForm(forms.Form):
    """Form for filtering user sessions"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('all', 'All'),
    ]
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial='active',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].empty_label = 'All Users'


class ActivityReportForm(forms.Form):
    """Form for generating activity reports"""
    
    REPORT_TYPES = [
        ('user_summary', 'User Activity Summary'),
        ('risk_report', 'Risk Assessment Report'),
        ('session_report', 'Session Analysis Report'),
        ('alert_report', 'Alert Summary Report'),
        ('time_analysis', 'Time-Based Activity Analysis'),
    ]
    
    TIME_RANGES = [
        ('1h', 'Last Hour'),
        ('24h', 'Last 24 Hours'),
        ('7d', 'Last 7 Days'),
        ('30d', 'Last 30 Days'),
        ('90d', 'Last 90 Days'),
        ('custom', 'Custom Range'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    time_range = forms.ChoiceField(
        choices=TIME_RANGES,
        initial='24h',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '5'
        })
    )
    
    include_details = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    format = forms.ChoiceField(
        choices=[
            ('html', 'HTML Report'),
            ('csv', 'CSV Export'),
            ('json', 'JSON Export'),
        ],
        initial='html',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        time_range = cleaned_data.get('time_range')
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if time_range == 'custom':
            if not date_from or not date_to:
                raise forms.ValidationError(
                    'Both date from and date to are required for custom time range.'
                )
            if date_from > date_to:
                raise forms.ValidationError(
                    'Date from must be before date to.'
                )
        
        return cleaned_data


class AlertResolutionForm(forms.ModelForm):
    """Form for resolving activity alerts"""
    
    class Meta:
        model = ActivityAlert
        fields = ['resolution_notes']
        widgets = {
            'resolution_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add resolution notes...'
            })
        }
    
    resolution_notes = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add resolution notes...'
        })
    )


class UserActivitySearchForm(forms.Form):
    """Form for searching user activities"""
    
    SEARCH_FIELDS = [
        ('all', 'All Fields'),
        ('description', 'Description'),
        ('module', 'Module'),
        ('ip_address', 'IP Address'),
        ('user_agent', 'User Agent'),
    ]
    
    search_term = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search activities...'
        })
    )
    
    search_field = forms.ChoiceField(
        choices=SEARCH_FIELDS,
        initial='all',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    include_inactive = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    max_results = forms.IntegerField(
        initial=50,
        min_value=10,
        max_value=500,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '10',
            'max': '500'
        })
    )


class SessionActionForm(forms.Form):
    """Form for taking actions on user sessions"""
    
    ACTIONS = [
        ('end_session', 'End Session'),
        ('flag_suspicious', 'Flag as Suspicious'),
        ('send_notification', 'Send Notification'),
        ('create_alert', 'Create Security Alert'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTIONS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    reason = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for action...'
        })
    )
    
    notify_user = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        reason = cleaned_data.get('reason')
        
        if action in ['end_session', 'flag_suspicious', 'create_alert'] and not reason:
            raise forms.ValidationError(
                'Reason is required for this action.'
            )
        
        return cleaned_data


class BulkActionForm(forms.Form):
    """Form for bulk actions on activities or alerts"""
    
    TARGET_TYPES = [
        ('activities', 'Activities'),
        ('alerts', 'Alerts'),
        ('sessions', 'Sessions'),
    ]
    
    ACTIONS = [
        ('export', 'Export to CSV'),
        ('delete', 'Delete (Activities Only)'),
        ('mark_resolved', 'Mark as Resolved (Alerts Only)'),
        ('create_backup', 'Create Backup'),
        ('archive', 'Archive'),
    ]
    
    target_type = forms.ChoiceField(
        choices=TARGET_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    action = forms.ChoiceField(
        choices=ACTIONS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    confirm_action = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    backup_path = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Backup file path (optional)'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        confirm_action = cleaned_data.get('confirm_action')
        
        if action in ['delete', 'archive'] and not confirm_action:
            raise forms.ValidationError(
                'You must confirm this action by checking the confirmation box.'
            )
        
        return cleaned_data
