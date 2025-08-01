from django import forms
from django.utils import timezone
from accounts.models import CustomUser
from .models import Designation, Shift, StaffSchedule, Leave, Attendance, Payroll
from accounts.models import Department

class DesignationForm(forms.ModelForm):
    class Meta:
        model = Designation
        fields = ['name', 'department', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['name', 'shift_type', 'start_time', 'end_time', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'shift_type': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time:
            # Convert to datetime for comparison
            start_dt = timezone.datetime.combine(timezone.datetime.today(), start_time)
            end_dt = timezone.datetime.combine(timezone.datetime.today(), end_time)
            
            # If end time is earlier than start time, assume it's the next day
            if end_dt < start_dt:
                end_dt += timezone.timedelta(days=1)
            
            # Check if shift is too long (more than 16 hours)
            duration = (end_dt - start_dt).total_seconds() / 3600
            if duration > 16:
                self.add_error('end_time', 'Shift duration cannot exceed 16 hours')
        
        return cleaned_data

class StaffScheduleForm(forms.ModelForm):
    class Meta:
        model = StaffSchedule
        fields = ['staff', 'shift', 'weekday', 'is_active']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select select2'}),
            'shift': forms.Select(attrs={'class': 'form-select'}),
            'weekday': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter staff to only include active users
        self.fields['staff'].queryset = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        weekday = cleaned_data.get('weekday')
        
        if staff and weekday and not self.instance.pk:
            # Check if this staff already has a schedule for this weekday
            if StaffSchedule.objects.filter(staff=staff, weekday=weekday).exists():
                self.add_error('weekday', f'This staff member already has a schedule for {dict(StaffSchedule.WEEKDAY_CHOICES)[weekday]}')
        
        return cleaned_data

class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['staff', 'leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select select2'}),
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # If this is a staff member requesting leave for themselves
        if user and not user.is_superuser and not user.profile.role == 'admin':
            self.fields['staff'].initial = user
            self.fields['staff'].widget = forms.HiddenInput()
        else:
            # Filter staff to only include active users
            self.fields['staff'].queryset = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        staff = cleaned_data.get('staff')
        
        if start_date and end_date:
            if start_date > end_date:
                self.add_error('end_date', 'End date cannot be before start date')
            
            # Check if leave dates overlap with existing approved leaves
            if staff:
                overlapping_leaves = Leave.objects.filter(
                    staff=staff,
                    status='approved',
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
                
                # Exclude current instance if editing
                if self.instance.pk:
                    overlapping_leaves = overlapping_leaves.exclude(pk=self.instance.pk)
                
                if overlapping_leaves.exists():
                    self.add_error('start_date', 'This leave period overlaps with an existing approved leave')
        
        return cleaned_data

class LeaveApprovalForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['status', 'rejection_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit status choices to approved, rejected, or cancelled
        self.fields['status'].choices = [
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if status == 'rejected' and not rejection_reason:
            self.add_error('rejection_reason', 'Please provide a reason for rejecting this leave request')
        
        return cleaned_data

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['staff', 'date', 'time_in', 'time_out', 'status', 'notes']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select select2'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'time_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter staff to only include active users
        self.fields['staff'].queryset = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # Set default date to today
        if not self.instance.pk and not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()
            self.initial['time_in'] = timezone.now().time().strftime('%H:%M')
    
    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        date = cleaned_data.get('date')
        time_in = cleaned_data.get('time_in')
        time_out = cleaned_data.get('time_out')
        status = cleaned_data.get('status')
        
        if staff and date:
            # Check if attendance record already exists for this staff and date
            existing = Attendance.objects.filter(staff=staff, date=date)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                self.add_error('date', 'Attendance record already exists for this staff member on this date')
        
        if time_in and time_out:
            # Convert to datetime for comparison
            time_in_dt = timezone.datetime.combine(timezone.datetime.today(), time_in)
            time_out_dt = timezone.datetime.combine(timezone.datetime.today(), time_out)
            
            # If time_out is earlier than time_in, assume it's the next day
            if time_out_dt < time_in_dt:
                time_out_dt += timezone.timedelta(days=1)
            
            # Check if shift is too long (more than 16 hours)
            duration = (time_out_dt - time_in_dt).total_seconds() / 3600
            if duration > 16:
                self.add_error('time_out', 'Working hours cannot exceed 16 hours')
        
        if status == 'absent' and time_in:
            self.add_error('time_in', 'Time in should not be set for absent status')
        
        if status == 'absent' and time_out:
            self.add_error('time_out', 'Time out should not be set for absent status')
        
        return cleaned_data

class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = ['staff', 'month', 'year', 'basic_salary', 'allowances', 'deductions', 
                  'payment_date', 'payment_method', 'status', 'notes']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select select2'}),
            'month': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2000, 'max': 2100}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'allowances': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'deductions': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter staff to only include active users
        self.fields['staff'].queryset = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # Set month choices
        self.fields['month'].widget.choices = [
            (1, 'January'),
            (2, 'February'),
            (3, 'March'),
            (4, 'April'),
            (5, 'May'),
            (6, 'June'),
            (7, 'July'),
            (8, 'August'),
            (9, 'September'),
            (10, 'October'),
            (11, 'November'),
            (12, 'December'),
        ]
        
        # Set default month and year to current month
        if not self.instance.pk and not self.initial.get('month'):
            today = timezone.now().date()
            self.initial['month'] = today.month
            self.initial['year'] = today.year
    
    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')
        
        if staff and month and year:
            # Check if payroll record already exists for this staff, month, and year
            existing = Payroll.objects.filter(staff=staff, month=month, year=year)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                self.add_error('month', 'Payroll record already exists for this staff member for this month and year')
        
        return cleaned_data

class StaffSearchForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search by name or email'
    }))
    
    department = forms.ModelChoiceField(
        required=False,
        queryset=Department.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    role = forms.ChoiceField(
        required=False,
        choices=[('', 'All Roles')] + [
            ('doctor', 'Doctor'),
            ('nurse', 'Nurse'),
            ('receptionist', 'Receptionist'),
            ('pharmacist', 'Pharmacist'),
            ('lab_technician', 'Lab Technician'),
            ('admin', 'Administrator'),
        ],
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

class LeaveSearchForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search by staff name'
    }))
    
    leave_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(Leave.LEAVE_TYPE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + list(Leave.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

class AttendanceSearchForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search by staff name'
    }))
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + [
            ('present', 'Present'),
            ('absent', 'Absent'),
            ('half_day', 'Half Day'),
            ('late', 'Late'),
            ('leave', 'Leave'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    department = forms.ModelChoiceField(
        required=False,
        queryset=Department.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class PayrollSearchForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search by staff name'
    }))
    
    month = forms.ChoiceField(
        required=False,
        choices=[('', 'All Months')] + [
            (1, 'January'),
            (2, 'February'),
            (3, 'March'),
            (4, 'April'),
            (5, 'May'),
            (6, 'June'),
            (7, 'July'),
            (8, 'August'),
            (9, 'September'),
            (10, 'October'),
            (11, 'November'),
            (12, 'December'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    year = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 2000, 'max': 2100})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + [
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    department = forms.ModelChoiceField(
        required=False,
        queryset=Department.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
