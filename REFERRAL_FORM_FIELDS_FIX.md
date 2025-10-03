# Referral Form Fields Fix - Department/Unit/Specialty Selection

## Issue Summary
**Problem**: Unable to select Department, Unit, or Specialty from the referral form  
**URL**: `http://127.0.0.1:8000/consultations/referrals/create/42/`  
**Root Cause**: Template was only displaying the "Refer To Doctor" field, missing all other referral type options  
**Status**: ✅ **FIXED**

## What Was Missing
The referral form supports 4 types of referrals:
1. **Department** - Refer to a department
2. **Specialty** - Refer to a specialty (e.g., Cardiology, Neurology)
3. **Unit** - Refer to a unit (e.g., ICU, Emergency)
4. **Doctor** - Refer to a specific doctor

However, the template was only showing the doctor field, making it impossible to create department, specialty, or unit referrals.

## Files Modified

### 1. `templates/consultations/referral_form.html`

#### Added Referral Type Selection Field
```html
<!-- Referral Type Selection -->
<div class="mb-3">
    <label for="{{ form.referral_type.id_for_label }}" class="form-label">
        <i class="fas fa-list me-1"></i>
        Referral Type <span class="text-danger">*</span>
    </label>
    {{ form.referral_type|add_class:"form-select" }}
    <div class="form-text">Select the type of referral (Department, Specialty, Unit, or Specific Doctor).</div>
</div>
```

#### Added Department Field
```html
<!-- Department Selection (shown when referral_type is 'department') -->
<div class="mb-3" id="department-field">
    <label for="{{ form.referred_to_department.id_for_label }}" class="form-label">
        <i class="fas fa-building me-1"></i>
        Department
    </label>
    {{ form.referred_to_department|add_class:"form-select select2" }}
    <div class="form-text">Select the department to refer the patient to.</div>
</div>
```

#### Added Specialty Field
```html
<!-- Specialty Input (shown when referral_type is 'specialty') -->
<div class="mb-3" id="specialty-field">
    <label for="{{ form.referred_to_specialty.id_for_label }}" class="form-label">
        <i class="fas fa-stethoscope me-1"></i>
        Specialty
    </label>
    {{ form.referred_to_specialty|add_class:"form-control" }}
    <div class="form-text">Enter the medical specialty (e.g., Cardiology, Neurology).</div>
</div>
```

#### Added Unit Field
```html
<!-- Unit Input (shown when referral_type is 'unit') -->
<div class="mb-3" id="unit-field">
    <label for="{{ form.referred_to_unit.id_for_label }}" class="form-label">
        <i class="fas fa-hospital me-1"></i>
        Unit
    </label>
    {{ form.referred_to_unit|add_class:"form-control" }}
    <div class="form-text">Enter the specific unit (e.g., ICU, Emergency).</div>
</div>
```

#### Updated Doctor Field
```html
<!-- Doctor Selection (shown when referral_type is 'doctor') -->
<div class="mb-3" id="doctor-field">
    <label for="{{ form.referred_to_doctor.id_for_label }}" class="form-label">
        <i class="fas fa-user-doctor me-1"></i>
        Refer To Doctor
    </label>
    {{ form.referred_to_doctor|add_class:"form-select select2" }}
    <div class="form-text">Select the specific doctor to refer the patient to.</div>
</div>
```

#### Added JavaScript for Dynamic Field Display
```javascript
// Function to show/hide fields based on referral type
function toggleReferralFields() {
    const referralType = $('#{{ form.referral_type.id_for_label }}').val();
    
    // Hide all conditional fields first
    $('#department-field').hide();
    $('#specialty-field').hide();
    $('#unit-field').hide();
    $('#doctor-field').hide();
    
    // Show relevant field based on selection
    if (referralType === 'department') {
        $('#department-field').show();
    } else if (referralType === 'specialty') {
        $('#specialty-field').show();
        $('#department-field').show(); // Can also select department for specialty
    } else if (referralType === 'unit') {
        $('#unit-field').show();
        $('#department-field').show(); // Can also select department for unit
    } else if (referralType === 'doctor') {
        $('#doctor-field').show();
    }
}

// Initialize field visibility on page load
toggleReferralFields();

// Update field visibility when referral type changes
$('#{{ form.referral_type.id_for_label }}').change(function() {
    toggleReferralFields();
});
```

#### Updated Form Validation
```javascript
// Form validation
$('#referralForm').on('submit', function(e) {
    const referralType = $('#{{ form.referral_type.id_for_label }}').val();
    const reason = $('#{{ form.reason.id_for_label }}').val().trim();
    let isValid = true;
    let errorMessage = '';

    // Validate based on referral type
    if (referralType === 'department') {
        const department = $('#{{ form.referred_to_department.id_for_label }}').val();
        if (!department) {
            isValid = false;
            errorMessage = 'Please select a department to refer the patient to.';
        }
    } else if (referralType === 'specialty') {
        const specialty = $('#{{ form.referred_to_specialty.id_for_label }}').val().trim();
        if (!specialty) {
            isValid = false;
            errorMessage = 'Please enter the specialty to refer the patient to.';
        }
    } else if (referralType === 'unit') {
        const unit = $('#{{ form.referred_to_unit.id_for_label }}').val().trim();
        if (!unit) {
            isValid = false;
            errorMessage = 'Please enter the unit to refer the patient to.';
        }
    } else if (referralType === 'doctor') {
        const doctor = $('#{{ form.referred_to_doctor.id_for_label }}').val();
        if (!doctor) {
            isValid = false;
            errorMessage = 'Please select a doctor to refer the patient to.';
        }
    }

    if (!isValid) {
        e.preventDefault();
        alert(errorMessage);
        return false;
    }
    
    if (!reason) {
        e.preventDefault();
        alert('Please provide a reason for the referral.');
        $('#{{ form.reason.id_for_label }}').focus();
        return false;
    }
});
```

### 2. `consultations/forms.py`

#### Added `referred_to_doctor` to Fields List
```python
class Meta:
    model = Referral
    fields = ['patient', 'referral_type', 'referred_to_department', 'referred_to_specialty', 
              'referred_to_unit', 'referred_to_doctor', 'reason', 'notes']
    widgets = {
        # ... existing widgets ...
        'referred_to_doctor': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_referred_to_doctor'}),
    }
```

#### Added Doctor Queryset Setup
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    # ... existing code ...
    
    # Get doctors using multiple role systems with fallback to all active users
    from django.db.models import Q
    
    doctors_queryset = CustomUser.objects.filter(
        Q(is_active=True) & (
            Q(roles__name__iexact='doctor') |
            Q(profile__role__iexact='doctor') |
            Q(groups__name__iexact='doctor') |
            Q(is_staff=True)
        )
    ).distinct().order_by('first_name', 'last_name')
    
    if not doctors_queryset.exists():
        doctors_queryset = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    self.fields['referred_to_doctor'].queryset = doctors_queryset
    self.fields['referred_to_doctor'].empty_label = "Select Doctor"
    
    # Make all referral destination fields not required (validation in clean method)
    self.fields['referred_to_department'].required = False
    self.fields['referred_to_specialty'].required = False
    self.fields['referred_to_unit'].required = False
    self.fields['referred_to_doctor'].required = False
```

#### Added Doctor Validation
```python
def clean(self):
    cleaned_data = super().clean()
    referral_type = cleaned_data.get('referral_type')
    
    # Validate based on referral type
    if referral_type == 'department':
        if not cleaned_data.get('referred_to_department'):
            raise forms.ValidationError("Please select a department for department referral.")
    elif referral_type == 'specialty':
        if not cleaned_data.get('referred_to_specialty'):
            raise forms.ValidationError("Please specify the specialty.")
        if not cleaned_data.get('referred_to_department'):
            raise forms.ValidationError("Please select a department for specialty referral.")
    elif referral_type == 'unit':
        if not cleaned_data.get('referred_to_unit'):
            raise forms.ValidationError("Please specify the unit.")
        if not cleaned_data.get('referred_to_department'):
            raise forms.ValidationError("Please select a department for unit referral.")
    elif referral_type == 'doctor':
        if not cleaned_data.get('referred_to_doctor'):
            raise forms.ValidationError("Please select a doctor for doctor referral.")
    
    return cleaned_data
```

## How It Works Now

1. **User selects Referral Type** from dropdown:
   - Department
   - Specialty
   - Unit
   - Doctor

2. **Form dynamically shows relevant fields**:
   - **Department**: Shows department dropdown
   - **Specialty**: Shows specialty input + department dropdown
   - **Unit**: Shows unit input + department dropdown
   - **Doctor**: Shows doctor dropdown

3. **Validation ensures** the correct field is filled based on referral type

4. **Submit creates referral** with the appropriate destination

## Testing Checklist
- [x] Referral Type dropdown displays
- [x] Department field shows when "Department" selected
- [x] Specialty field shows when "Specialty" selected
- [x] Unit field shows when "Unit" selected
- [x] Doctor field shows when "Doctor" selected
- [x] Fields hide/show dynamically on type change
- [x] Form validation works for each type
- [x] Form submission creates referral correctly

## Summary
**Before**: Only doctor referrals were possible  
**After**: All 4 referral types (Department, Specialty, Unit, Doctor) are now available  
**Result**: Complete referral functionality restored! ✅

