from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import (
    Specialization, Doctor, DoctorAvailability, DoctorLeave,
    DoctorEducation, DoctorExperience, DoctorReview
)
from accounts.models import Department

class SpecializationForm(forms.ModelForm):
    """Form for creating and editing specializations"""
    class Meta:
        model = Specialization
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class DoctorUserCreationForm(UserCreationForm):
    """Form for creating a new user account for a doctor"""
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=True, help_text="Required for login. Use digits only.")
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'phone_number']
    
    def clean_phone_number(self):
        """Validate that the phone number contains only digits"""
        phone_number = self.cleaned_data.get('phone_number')
        
        # Check if phone number contains only digits
        if phone_number and not phone_number.isdigit():
            raise ValidationError("Phone number must contain only digits.")
        
        # Check if phone number is already in use
        from accounts.models import UserProfile
        if UserProfile.objects.filter(phone_number=phone_number).exists():
            raise ValidationError("This phone number is already in use.")
        
        return phone_number
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # Set the user's profile role to 'doctor'
            user.profile.role = 'doctor'
            user.profile.phone_number = self.cleaned_data['phone_number']
            user.profile.save()
        
        return user

def get_specialization_choices():
    """Utility to get all specializations as choices for forms."""
    from .models import Specialization
    return [(s.id, s.name) for s in Specialization.objects.all()]

class DoctorForm(forms.ModelForm):
    specialization = forms.ModelChoiceField(queryset=Specialization.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))
    """Form for creating and editing doctor profiles"""
    class Meta:
        model = Doctor
        fields = [
            'specialization', 'department', 'license_number', 'experience',
            'qualification', 'bio', 'consultation_fee', 'available_for_appointments',
            'signature'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'specialization': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'experience': forms.Select(attrs={'class': 'form-select'}),
        }

class DoctorAvailabilityForm(forms.ModelForm):
    """Form for setting doctor availability"""
    class Meta:
        model = DoctorAvailability
        fields = ['weekday', 'start_time', 'end_time', 'is_available', 'max_appointments']
        widgets = {
            'weekday': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise ValidationError("End time must be after start time.")
        
        return cleaned_data

class DoctorLeaveForm(forms.ModelForm):
    """Form for doctor leave requests"""
    class Meta:
        model = DoctorLeave
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("End date must be after or equal to start date.")
        
        return cleaned_data

class DoctorEducationForm(forms.ModelForm):
    """Form for doctor education details"""
    class Meta:
        model = DoctorEducation
        fields = ['degree', 'institution', 'year_of_completion', 'additional_info']
        widgets = {
            'additional_info': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

class DoctorExperienceForm(forms.ModelForm):
    """Form for doctor work experience"""
    class Meta:
        model = DoctorExperience
        fields = ['hospital_name', 'position', 'start_date', 'end_date', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("End date must be after or equal to start date.")
        
        return cleaned_data

class DoctorReviewForm(forms.ModelForm):
    """Form for patient reviews of doctors"""
    class Meta:
        model = DoctorReview
        fields = ['rating', 'review_text']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'review_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class DoctorSearchForm(forms.Form):
    """Form for searching doctors"""
    name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Doctor name'}))
    specialization = forms.ModelChoiceField(
        queryset=Specialization.objects.all(),
        required=False,
        empty_label="All Specializations",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="All Departments",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    available_only = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
