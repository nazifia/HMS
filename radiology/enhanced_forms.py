from django import forms
from django.contrib.auth import get_user_model
from .models import RadiologyResult, RadiologyOrder

User = get_user_model()


class EnhancedRadiologyResultForm(forms.ModelForm):
    """Enhanced form for radiology result entry"""
    
    CONTRAST_CHOICES = [
        ('none', 'No Contrast'),
        ('oral', 'Oral Contrast'),
        ('iv', 'IV Contrast'),
        ('both', 'Oral + IV Contrast'),
        ('other', 'Other'),
    ]
    
    IMAGE_QUALITY_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('adequate', 'Adequate'),
        ('poor', 'Poor'),
        ('non_diagnostic', 'Non-diagnostic'),
    ]
    
    STUDY_STATUS_CHOICES = [
        ('complete', 'Complete'),
        ('incomplete', 'Incomplete'),
        ('limited', 'Limited'),
        ('cancelled', 'Cancelled'),
    ]
    
    contrast_used = forms.ChoiceField(
        choices=CONTRAST_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    contrast_amount = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'min': '0'
        })
    )
    
    image_quality = forms.ChoiceField(
        choices=IMAGE_QUALITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    study_status = forms.ChoiceField(
        choices=STUDY_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = RadiologyResult
        fields = [
            'study_date', 'study_time', 'performed_by', 'radiologist',
            'technique', 'findings', 'impression', 'recommendations',
            'images', 'report_file', 'notes'
        ]
        widgets = {
            'study_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'study_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'performed_by': forms.Select(attrs={'class': 'form-select'}),
            'radiologist': forms.Select(attrs={'class': 'form-select'}),
            'technique': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Technical parameters (kVp, mAs, slice thickness, etc.)'
            }),
            'findings': forms.Textarea(attrs={
                'rows': 6,
                'class': 'form-control',
                'placeholder': 'Detailed description of radiological findings...'
            }),
            'impression': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Clinical interpretation and diagnosis...'
            }),
            'recommendations': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Follow-up recommendations or additional studies...'
            }),
            'images': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.dcm,.jpg,.jpeg,.png,.pdf',
                'multiple': True
            }),
            'report_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Technical notes, patient cooperation, limitations...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.radiology_order = kwargs.pop('radiology_order', None)
        super().__init__(*args, **kwargs)
        
        # Filter users to radiology staff
        radiology_staff = User.objects.filter(
            is_active=True,
            groups__name__in=['Radiology Staff', 'Radiologic Technologists', 'Radiologists']
        ).distinct()
        
        radiologists = User.objects.filter(
            is_active=True,
            groups__name__in=['Radiologists', 'Radiology Consultants']
        ).distinct()
        
        self.fields['performed_by'].queryset = radiology_staff
        self.fields['radiologist'].queryset = radiologists
        
        # Set default values
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['study_date'].initial = timezone.now().date()
            self.fields['study_time'].initial = timezone.now().time()
    
    def clean(self):
        cleaned_data = super().clean()
        contrast_used = cleaned_data.get('contrast_used')
        contrast_amount = cleaned_data.get('contrast_amount')
        
        # Validate contrast amount if contrast is used
        if contrast_used in ['oral', 'iv', 'both'] and not contrast_amount:
            self.add_error('contrast_amount', 'Contrast amount is required when contrast is used.')
        
        return cleaned_data


class RadiologyResultVerificationForm(forms.ModelForm):
    """Form for verifying radiology results"""
    
    verification_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Verification notes, comments, or corrections...'
        })
    )
    
    class Meta:
        model = RadiologyResult
        fields = ['verified_by']
        widgets = {
            'verified_by': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter to senior radiologists
        senior_radiologists = User.objects.filter(
            is_active=True,
            groups__name__in=['Senior Radiologists', 'Radiology Consultants', 'Department Heads']
        ).distinct()
        self.fields['verified_by'].queryset = senior_radiologists


class RadiologyResultSearchForm(forms.Form):
    """Form for searching and filtering radiology results"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by patient name, study type, or order ID'
        })
    )
    
    test = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
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
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('verified', 'Verified'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    radiologist = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        from .models import RadiologyTest, RadiologyCategory
        
        # Set querysets
        self.fields['test'].queryset = RadiologyTest.objects.filter(is_active=True)
        self.fields['category'].queryset = RadiologyCategory.objects.all()
        
        # Filter radiologist to actual radiologists
        radiologists = User.objects.filter(
            is_active=True,
            groups__name__in=['Radiologists', 'Radiology Consultants']
        ).distinct()
        self.fields['radiologist'].queryset = radiologists


class QuickRadiologyResultForm(forms.Form):
    """Quick form for simple radiology results"""
    
    findings = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Brief findings...'
        })
    )
    
    impression = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control',
            'placeholder': 'Clinical impression...'
        })
    )
    
    status = forms.ChoiceField(
        choices=[
            ('normal', 'Normal'),
            ('abnormal', 'Abnormal'),
            ('urgent', 'Urgent - Requires immediate attention'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class RadiologyTemplateForm(forms.Form):
    """Form for creating radiology report templates"""
    
    template_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Template name'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    findings_template = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 6,
            'class': 'form-control',
            'placeholder': 'Findings template with placeholders...'
        })
    )
    
    impression_template = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Impression template with placeholders...'
        })
    )
    
    is_public = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        from .models import RadiologyCategory
        self.fields['category'].queryset = RadiologyCategory.objects.all()


class BulkRadiologyResultForm(forms.Form):
    """Form for bulk operations on radiology results"""
    
    action = forms.ChoiceField(
        choices=[
            ('verify', 'Verify Selected Results'),
            ('export', 'Export Selected Results'),
            ('print', 'Print Selected Results'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Bulk operation notes...'
        })
    )


class RadiologyQualityAssuranceForm(forms.Form):
    """Form for radiology quality assurance"""
    
    QUALITY_METRICS = [
        ('image_quality', 'Image Quality'),
        ('positioning', 'Patient Positioning'),
        ('technique', 'Technical Factors'),
        ('artifacts', 'Artifacts'),
        ('radiation_dose', 'Radiation Dose'),
    ]
    
    metric = forms.ChoiceField(
        choices=QUALITY_METRICS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    score = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '5'
        })
    )
    
    comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Quality assurance comments...'
        })
    )
    
    corrective_action = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control',
            'placeholder': 'Recommended corrective actions...'
        })
    )
