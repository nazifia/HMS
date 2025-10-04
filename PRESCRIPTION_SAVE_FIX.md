# Prescription Save Fix - Doctor Field Required Error

## Issue Summary
**Problem**: Unable to save prescriptions created from consultations  
**Root Cause**: Prescription model requires a `doctor` field, but consultations can have `doctor=None`  
**Error**: Database constraint violation when trying to save prescription with `doctor=None`  
**Status**: ✅ **FIXED**

## Root Cause Analysis

### The Problem
1. **Consultation Model** (`consultations/models.py` line 77):
   ```python
   doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                              null=True, blank=True, related_name='doctor_consultations')
   ```
   - Consultation.doctor **CAN be None** (null=True, blank=True)

2. **Prescription Model** (`pharmacy/models.py` line 492):
   ```python
   doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                              related_name='doctor_prescriptions')
   ```
   - Prescription.doctor **CANNOT be None** (no null=True)

3. **QuickPrescriptionForm.save()** (original code):
   ```python
   prescription = Prescription(
       patient=self.consultation.patient,
       doctor=self.consultation.doctor,  # ← This can be None!
       ...
   )
   ```
   - When `consultation.doctor` is None, the prescription save fails

### Why This Happens
- Some consultations don't have an assigned doctor (e.g., walk-in consultations, emergency cases)
- The form was directly using `consultation.doctor` without checking if it's None
- Database rejects the save because the doctor field is required

## Solution Implemented

### 1. Modified `QuickPrescriptionForm.__init__` to Accept User
**File**: `consultations/forms.py`

```python
def __init__(self, *args, **kwargs):
    self.consultation = kwargs.pop('consultation', None)
    self.user = kwargs.pop('user', None)  # ← Added user parameter
    super().__init__(*args, **kwargs)
```

### 2. Updated `QuickPrescriptionForm.save()` with Fallback Logic
**File**: `consultations/forms.py`

```python
def save(self, commit=True):
    """Create a prescription from the form data"""
    if not self.consultation:
        raise ValueError("Consultation is required to create a prescription")
        
    from pharmacy.models import Prescription
    
    # Determine the doctor - use consultation doctor or fallback to current user
    doctor = self.consultation.doctor or self.user  # ← Fallback logic
    if not doctor:
        raise ValueError("A doctor must be specified for the prescription")
        
    # Create the prescription
    prescription = Prescription(
        patient=self.consultation.patient,
        doctor=doctor,  # ← Now guaranteed to have a value
        prescription_date=timezone.now().date(),
        diagnosis=self.cleaned_data['diagnosis'],
        prescription_type=self.cleaned_data['prescription_type'],
        notes=self.cleaned_data['notes']
    )
    
    if commit:
        prescription.save()
        
        # Create consultation order link
        content_type = ContentType.objects.get_for_model(Prescription)
        ConsultationOrder.objects.create(
            consultation=self.consultation,
            order_type='prescription',
            content_type=content_type,
            object_id=prescription.id,
            created_by=doctor  # ← Also updated to use the determined doctor
        )
        
    return prescription
```

### 3. Updated All Form Instantiations to Pass User
**File**: `consultations/views.py`

#### Change 1: `consultation_detail` view (line 75)
```python
# BEFORE
'prescription_form': QuickPrescriptionForm(consultation=consultation),

# AFTER
'prescription_form': QuickPrescriptionForm(consultation=consultation, user=request.user),
```

#### Change 2: `create_consultation_order` view (line 127)
```python
# BEFORE
form = QuickPrescriptionForm(request.POST, consultation=consultation)

# AFTER
form = QuickPrescriptionForm(request.POST, consultation=consultation, user=request.user)
```

#### Change 3: `create_prescription_ajax` view (line 214)
```python
# BEFORE
form = QuickPrescriptionForm(request.POST, consultation=consultation)

# AFTER
form = QuickPrescriptionForm(request.POST, consultation=consultation, user=request.user)
```

#### Change 4: Error handling context (line 144)
```python
# BEFORE
'prescription_form': QuickPrescriptionForm(consultation=consultation),

# AFTER
'prescription_form': QuickPrescriptionForm(consultation=consultation, user=request.user),
```

## How It Works Now

### Scenario 1: Consultation Has a Doctor
```python
consultation.doctor = Dr. Smith
request.user = Dr. Jones

# Result: prescription.doctor = Dr. Smith (uses consultation doctor)
```

### Scenario 2: Consultation Has No Doctor
```python
consultation.doctor = None
request.user = Dr. Jones

# Result: prescription.doctor = Dr. Jones (uses current user as fallback)
```

### Scenario 3: No Doctor Available (Edge Case)
```python
consultation.doctor = None
request.user = None  # Shouldn't happen in practice

# Result: Raises ValueError("A doctor must be specified for the prescription")
```

## Benefits

1. **Robust Error Handling**: Gracefully handles consultations without assigned doctors
2. **Maintains Data Integrity**: Ensures prescriptions always have a valid doctor
3. **Logical Fallback**: Uses the current user (who is creating the prescription) when consultation doctor is not set
4. **Clear Error Messages**: Provides helpful error messages if neither doctor is available
5. **Backward Compatible**: Doesn't break existing functionality

## Testing Checklist

- [x] Prescription creation from consultation with assigned doctor
- [x] Prescription creation from consultation without assigned doctor
- [x] AJAX prescription creation
- [x] Form validation and error handling
- [x] Consultation order creation
- [x] Database constraints satisfied

## Files Modified

1. **consultations/forms.py**
   - Modified `QuickPrescriptionForm.__init__` to accept `user` parameter
   - Updated `QuickPrescriptionForm.save()` with doctor fallback logic

2. **consultations/views.py**
   - Updated 4 locations where `QuickPrescriptionForm` is instantiated
   - All now pass `user=request.user` parameter

## Summary

**Before**: Prescriptions failed to save when consultation.doctor was None  
**After**: Prescriptions use current user as doctor when consultation.doctor is None  
**Result**: Prescription creation now works reliably in all scenarios! ✅

The fix ensures that prescriptions can always be saved by providing a fallback doctor (the current user) when the consultation doesn't have an assigned doctor, while maintaining data integrity and providing clear error messages.

