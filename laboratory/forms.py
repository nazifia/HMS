from django import forms
from django.utils import timezone
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import (
    TestCategory, Test, TestParameter, TestRequest,
    TestResult, TestResultParameter
)
from patients.models import Patient
from django.forms import inlineformset_factory, BaseInlineFormSet

class TestCategoryForm(forms.ModelForm):
    """Form for creating and editing test categories"""

    class Meta:
        model = TestCategory
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class TestForm(forms.ModelForm):
    """Form for creating and editing tests"""

    class Meta:
        model = Test
        fields = [
            'name', 'category', 'description', 'price',
            'preparation_instructions', 'normal_range', 'unit',
            'sample_type', 'duration', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'preparation_instructions': forms.Textarea(attrs={'rows': 3}),
        }

class TestParameterForm(forms.ModelForm):
    """Form for creating and editing test parameters"""

    class Meta:
        model = TestParameter
        fields = ['name', 'normal_range', 'unit', 'order']

class TestRequestForm(forms.ModelForm):
    """Form for creating and editing test requests"""

    patient = forms.ModelChoiceField(
        queryset=Patient.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Patient"
    )

    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, custom_profile__specialization__isnull=False),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Doctor"
    )

    tests = forms.ModelMultipleChoiceField(
        queryset=Test.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-select select2'}),
        required=True
    )

    request_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = TestRequest
        fields = [
            'patient', 'doctor', 'tests', 'request_date',
            'status', 'priority', 'notes'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        patient_id = None
        if request:
            patient_id = request.GET.get('patient')
        if not patient_id:
            patient_id = self.initial.get('patient')
        if patient_id:
            self.fields['patient'].initial = patient_id
            self.fields['patient'].widget = forms.HiddenInput()

        # Ensure all patients are available for selection
        self.fields['patient'].queryset = Patient.objects.all()

class TestResultForm(forms.ModelForm):
    """Form for creating and editing test results"""

    result_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    sample_collection_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )

    sample_collected_by = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        required=False,
        empty_label="Select Staff"
    )

    performed_by = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        required=True,
        empty_label="Select Staff"
    )

    verified_by = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        required=False,
        empty_label="Select Staff"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide the 'test' field on edit (instance exists)
        if self.instance and self.instance.pk:
            self.fields['test'].widget = forms.HiddenInput()
            self.fields['test'].required = False

    def save(self, commit=True):
        # Always set 'test' from the DB instance if editing
        if self.instance and self.instance.pk:
            self.instance.test = type(self.instance).objects.get(pk=self.instance.pk).test
        return super().save(commit=commit)

    class Meta:
        model = TestResult
        fields = [
            'test', 'result_date', 'sample_collection_date',
            'sample_collected_by', 'result_file', 'notes',
            'performed_by', 'verified_by'
        ]
        widgets = {
            'test': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class TestResultParameterForm(forms.ModelForm):
    """Form for creating and editing test result parameters"""
    # Make parameter field read-only when editing as it shouldn't change
    # This can be done in __init__ or by setting widget attrs if always read-only for this form
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.parameter:
            self.fields['parameter'].widget.attrs['disabled'] = True 
            self.fields['parameter'].required = False # Disabled fields don't submit data

    class Meta:
        model = TestResultParameter
        fields = ['parameter', 'value', 'is_normal', 'notes']
        widgets = {
            # 'parameter': forms.Select(attrs={'class': 'form-select'}), # Keep for creation, disable for edit
            'value': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'is_normal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'rows': 1, 'class': 'form-control form-control-sm'}),
        }

class BaseTestResultParameterFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for form in self.forms:
            # You can customize individual forms here if needed
            # For example, to make the 'parameter' field appear as plain text or disabled
            if form.instance and form.instance.pk and form.instance.parameter:
                form.fields['parameter'].widget.attrs['disabled'] = True
                form.fields['parameter'].required = False
                # To display the parameter name as text instead of a disabled select:
                # form.fields['parameter'].widget = forms.HiddenInput() # Hide it
                # And then display {{ form.instance.parameter.name }} in the template

    def clean(self):
        super().clean()
        # Add any custom validation for the formset here
        # For example, ensure at least one parameter has a value if required
        pass

TestResultParameterFormSet = inlineformset_factory(
    TestResult,  # Parent model
    TestResultParameter,  # Child model
    form=TestResultParameterForm,  # Form for each child
    formset=BaseTestResultParameterFormSet, # Custom base formset
    fields=['parameter', 'value', 'is_normal', 'notes'],
    extra=0,  # Number of empty forms to display
    can_delete=False  # Set to True if you want to allow deleting parameters from this interface
)

# class TestSearchForm(forms.Form):
#     """Form for searching tests"""

#     search = forms.CharField(
#         required=False,
#         widget=forms.TextInput(attrs={'placeholder': 'Search by name or category'})
#     )

#     category = forms.ModelChoiceField(
#         queryset=TestCategory.objects.all(),
#         required=False,
#         empty_label="All Categories"
#     )

#     sample_type = forms.ChoiceField(
#         choices=[('', 'All')] + [(t, t) for t in Test.objects.values_list('sample_type', flat=True).distinct()],
#         required=False
#     )

#     is_active = forms.ChoiceField(
#         choices=[
#             ('', 'All'),
#             ('active', 'Active'),
#             ('inactive', 'Inactive')
#         ],
#         required=False
#     )

class TestSearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            sample_type_choices = [('', 'All')] + list(
                (t, t) for t in Test.objects.values_list('sample_type', flat=True).distinct()
            )
        except Exception:
            sample_type_choices = [('', 'All')]  # fallback if table doesn't exist
        self.fields['sample_type'] = forms.ChoiceField(
            choices=sample_type_choices,
            required=False
        )



class TestRequestSearchForm(forms.Form):
    """Form for searching test requests"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search by patient name or ID'})
    )

    status = forms.ChoiceField(
        choices=[('', 'All')] + list(TestRequest.STATUS_CHOICES),
        required=False
    )

    priority = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('normal', 'Normal'),
            ('urgent', 'Urgent'),
            ('emergency', 'Emergency')
        ],
        required=False
    )

    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, custom_profile__specialization__isnull=False),
        required=False,
        empty_label="All Doctors"
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
