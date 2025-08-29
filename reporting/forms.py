from django import forms
from django.utils import timezone
from .models import Report, Dashboard, DashboardWidget, ReportExecution
from doctors.models import Doctor
from appointments.models import Appointment
from billing.models import Invoice
from laboratory.models import Test
from radiology.models import RadiologyTest
from hr.models import StaffProfile, Department, Designation

class PatientReportForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=[('', 'All'), ('male', 'Male'), ('female', 'Female')], required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lazy load the Patient queryset to avoid circular imports
        from patients.models import Patient
        # Note: This form doesn't actually use Patient in fields, but keeping for consistency

class AppointmentReportForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.all(), required=False)
    status = forms.ChoiceField(choices=[('', 'All')] + list(Appointment.STATUS_CHOICES), required=False)

class BillingReportForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    patient = forms.ModelChoiceField(queryset=Doctor.objects.none(), required=False)
    payment_status = forms.ChoiceField(
        choices=[('', 'All'), ('paid', 'Paid'), ('pending', 'Pending'), ('partially_paid', 'Partially Paid'), ('overdue', 'Overdue'), ('cancelled', 'Cancelled')],
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lazy load the Patient queryset to avoid circular imports
        from patients.models import Patient
        self.fields['patient'].queryset = Patient.objects.all()

class PharmacySalesReportForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    patient = forms.ModelChoiceField(queryset=Doctor.objects.none(), required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lazy load the Patient queryset to avoid circular imports
        from patients.models import Patient
        self.fields['patient'].queryset = Patient.objects.all()

class LaboratoryReportForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    patient = forms.ModelChoiceField(queryset=Doctor.objects.none(), required=False)
    test_type = forms.ModelChoiceField(queryset=Test.objects.all(), required=False)
    status = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('true', 'Active'),
            ('false', 'Inactive'),
        ],
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lazy load the Patient queryset to avoid circular imports
        from patients.models import Patient
        self.fields['patient'].queryset = Patient.objects.all()

class RadiologyReportForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    patient = forms.ModelChoiceField(queryset=Doctor.objects.none(), required=False)
    test_type = forms.ModelChoiceField(queryset=RadiologyTest.objects.all(), required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lazy load the Patient queryset to avoid circular imports
        from patients.models import Patient
        self.fields['patient'].queryset = Patient.objects.all()

class InpatientReportForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    patient = forms.ModelChoiceField(queryset=Doctor.objects.none(), required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lazy load the Patient queryset to avoid circular imports
        from patients.models import Patient
        self.fields['patient'].queryset = Patient.objects.all()

class HRReportForm(forms.Form):
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=False)
    designation = forms.ModelChoiceField(queryset=Designation.objects.all(), required=False)

class FinancialReportForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    report_type = forms.ChoiceField(choices=[
        ('', 'All'),
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('profit_loss', 'Profit/Loss'),
    ], required=False)


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['name', 'description', 'query', 'parameters', 'category', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'query': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'parameters': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ReportExecutionForm(forms.ModelForm):
    class Meta:
        model = ReportExecution
        fields = ['report', 'parameters']
        widgets = {
            'report': forms.Select(attrs={'class': 'form-select'}),
            'parameters': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        report = kwargs.pop('report', None)
        super().__init__(*args, **kwargs)
        
        if report:
            self.fields['report'].initial = report
            self.fields['report'].widget = forms.HiddenInput()
            
            # If the report has parameters, pre-fill the parameters field
            if report.parameters:
                self.fields['parameters'].help_text = f'Required parameters: {report.parameters}'

class DashboardForm(forms.ModelForm):
    class Meta:
        model = Dashboard
        fields = ['name', 'description', 'is_default', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class DashboardWidgetForm(forms.ModelForm):
    class Meta:
        model = DashboardWidget
        fields = ['dashboard', 'report', 'title', 'widget_type', 'position_x', 'position_y', 'width', 'height', 'parameters']
        widgets = {
            'dashboard': forms.Select(attrs={'class': 'form-select'}),
            'report': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'widget_type': forms.Select(attrs={'class': 'form-select'}),
            'position_x': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'position_y': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'width': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'parameters': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        dashboard = kwargs.pop('dashboard', None)
        super().__init__(*args, **kwargs)
        
        if dashboard:
            self.fields['dashboard'].initial = dashboard
            self.fields['dashboard'].widget = forms.HiddenInput()
    
    def clean(self):
        cleaned_data = super().clean()
        widget_type = cleaned_data.get('widget_type')
        width = cleaned_data.get('width')
        height = cleaned_data.get('height')
        
        if widget_type and width and height:
            # Validate width and height based on widget type
            if widget_type == 'table' and height < 2:
                self.add_error('height', 'Table widgets should have a minimum height of 2.')
            
            if widget_type in ['pie', 'donut'] and (width < 3 or height < 3):
                self.add_error('width', 'Pie/Donut charts should have a minimum width and height of 3.')
        
        return cleaned_data

class ReportSearchForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search by name or description'
    }))
    
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + list(Report.CATEGORY_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_active = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All'),
            ('true', 'Active'),
            ('false', 'Inactive'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class DashboardSearchForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search by name or description'
    }))
    
    is_public = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All'),
            ('true', 'Public'),
            ('false', 'Private'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
