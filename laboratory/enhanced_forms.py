from django import forms
from django.contrib.auth import get_user_model
from .models import TestResult, TestResultParameter, Test, TestRequest

User = get_user_model()


class EnhancedTestResultForm(forms.ModelForm):
    """Enhanced form for laboratory test result entry"""
    
    class Meta:
        model = TestResult
        fields = [
            'test', 'result_date', 'sample_collection_date', 'sample_collected_by',
            'result_file', 'notes', 'performed_by'
        ]
        widgets = {
            'test': forms.Select(attrs={'class': 'form-select'}),
            'result_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'sample_collection_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'sample_collected_by': forms.Select(attrs={'class': 'form-select'}),
            'result_file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'}),
            'notes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Clinical notes, observations, interpretations...'}),
            'performed_by': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.test_request = kwargs.pop('test_request', None)
        super().__init__(*args, **kwargs)
        
        # Filter tests to only those in the test request
        if self.test_request:
            self.fields['test'].queryset = self.test_request.tests.all()
        
        # Filter users to lab staff
        lab_staff = User.objects.filter(
            is_active=True,
            groups__name__in=['Laboratory Staff', 'Lab Technicians', 'Medical Laboratory Scientists']
        ).distinct()
        
        self.fields['sample_collected_by'].queryset = lab_staff
        self.fields['performed_by'].queryset = lab_staff
        
        # Set default values
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['result_date'].initial = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        test = cleaned_data.get('test')
        
        # Validate that test belongs to the test request
        if self.test_request and test and test not in self.test_request.tests.all():
            raise forms.ValidationError("Selected test is not part of this test request.")
        
        return cleaned_data


class TestResultParameterFormSet(forms.BaseFormSet):
    """Formset for test result parameters"""
    
    def __init__(self, *args, **kwargs):
        self.test = kwargs.pop('test', None)
        super().__init__(*args, **kwargs)
    
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['test'] = self.test
        return kwargs


class TestResultParameterForm(forms.ModelForm):
    """Form for individual test result parameters"""
    
    STATUS_CHOICES = [
        ('normal', 'Normal'),
        ('abnormal', 'Abnormal'),
        ('critical', 'Critical'),
        ('pending', 'Pending'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = TestResultParameter
        fields = ['parameter', 'value', 'is_normal', 'notes']
        widgets = {
            'parameter': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter result value'}),
            'is_normal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Additional notes'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.test = kwargs.pop('test', None)
        super().__init__(*args, **kwargs)
        
        # Filter parameters to only those for the selected test
        if self.test:
            self.fields['parameter'].queryset = self.test.parameters.all()
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        
        # Set is_normal based on status
        if status:
            cleaned_data['is_normal'] = status == 'normal'
        
        return cleaned_data


class BulkResultEntryForm(forms.Form):
    """Form for entering results for multiple tests at once"""
    
    test_request = forms.ModelChoiceField(
        queryset=TestRequest.objects.filter(status='in_progress'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    result_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    performed_by = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'General notes for all results'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default values
        from django.utils import timezone
        self.fields['result_date'].initial = timezone.now().date()
        
        # Filter performed_by to lab staff
        lab_staff = User.objects.filter(
            is_active=True,
            groups__name__in=['Laboratory Staff', 'Lab Technicians', 'Medical Laboratory Scientists']
        ).distinct()
        self.fields['performed_by'].queryset = lab_staff


class ResultVerificationForm(forms.ModelForm):
    """Form for verifying test results"""
    
    verification_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Verification notes, comments, or corrections...'
        })
    )
    
    class Meta:
        model = TestResult
        fields = ['verified_by']
        widgets = {
            'verified_by': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter to senior lab staff or pathologists
        senior_staff = User.objects.filter(
            is_active=True,
            groups__name__in=['Senior Lab Staff', 'Pathologists', 'Medical Laboratory Scientists']
        ).distinct()
        self.fields['verified_by'].queryset = senior_staff


class ResultSearchForm(forms.Form):
    """Form for searching and filtering test results"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by patient name, test name, or request ID'
        })
    )
    
    test = forms.ModelChoiceField(
        queryset=Test.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('verified', 'Verified'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    performed_by = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class QuickResultForm(forms.Form):
    """Quick form for simple test results"""
    
    test = forms.ModelChoiceField(
        queryset=Test.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    result_value = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter result value'
        })
    )
    
    status = forms.ChoiceField(
        choices=[
            ('normal', 'Normal'),
            ('abnormal', 'Abnormal'),
            ('critical', 'Critical'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quick notes (optional)'
        })
    )


class ResultTemplateForm(forms.Form):
    """Form for creating result templates"""

    template_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Template name'
        })
    )

    test = forms.ModelChoiceField(
        queryset=Test.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    template_content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 6,
            'class': 'form-control',
            'placeholder': 'Template content with placeholders...'
        })
    )

    is_public = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class ManualResultEntryForm(forms.Form):
    """Comprehensive form for manual result entry"""

    RESULT_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('preliminary', 'Preliminary'),
        ('final', 'Final'),
        ('amended', 'Amended'),
        ('cancelled', 'Cancelled'),
    ]

    # Basic Information
    test = forms.ModelChoiceField(
        queryset=Test.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Choose a test..."
    )

    result_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    # Sample Information
    sample_collection_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )

    sample_collected_by = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select collector..."
    )

    # Result Content
    result_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Enter detailed result description, observations, or narrative results...'
        })
    )

    interpretation = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Clinical significance, recommendations, or interpretation of results...'
        })
    )

    technician_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control',
            'placeholder': 'Technical notes, sample quality, methodology notes...'
        })
    )

    # File Attachments
    result_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'
        })
    )

    # Quality Control
    performed_by = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select technician..."
    )

    result_status = forms.ChoiceField(
        choices=RESULT_STATUS_CHOICES,
        initial='draft',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        self.test_request = kwargs.pop('test_request', None)
        super().__init__(*args, **kwargs)

        # Filter tests to only those in the test request
        if self.test_request:
            self.fields['test'].queryset = self.test_request.tests.all()

        # Filter users to lab staff
        lab_staff = User.objects.filter(
            is_active=True,
            groups__name__in=['Laboratory Staff', 'Lab Technicians', 'Medical Laboratory Scientists']
        ).distinct()

        self.fields['sample_collected_by'].queryset = lab_staff
        self.fields['performed_by'].queryset = lab_staff

        # Set default values
        from django.utils import timezone
        self.fields['result_date'].initial = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        test = cleaned_data.get('test')
        result_text = cleaned_data.get('result_text')

        # Validate that test belongs to the test request
        if self.test_request and test and test not in self.test_request.tests.all():
            raise forms.ValidationError("Selected test is not part of this test request.")

        # Ensure at least some result content is provided
        if not result_text and not any(cleaned_data.get(f'parameter_value_{i}') for i in range(20)):
            raise forms.ValidationError("Please provide either result text or parameter values.")

        return cleaned_data


class ManualParameterForm(forms.Form):
    """Form for individual manual parameters"""

    PARAMETER_STATUS_CHOICES = [
        ('normal', 'Normal'),
        ('abnormal', 'Abnormal'),
        ('critical', 'Critical'),
        ('pending', 'Pending'),
    ]

    parameter_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Hemoglobin'
        })
    )

    parameter_value = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter value'
        })
    )

    parameter_unit = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'g/dL'
        })
    )

    parameter_range = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12-16'
        })
    )

    parameter_status = forms.ChoiceField(
        choices=PARAMETER_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    parameter_notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Additional notes'
        })
    )
