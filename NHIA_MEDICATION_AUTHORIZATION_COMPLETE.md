# NHIA Medication Authorization - Complete Implementation

## Overview
Complete implementation ensuring NHIA patients seen/consulted from units other than NHIA must get authorization from Desk Office before their medications can be dispensed.

**Date:** 2025-09-30
**Status:** ✅ Complete and Enforced

---

## Business Rule

**NHIA patients seen in non-NHIA units MUST obtain Desk Office authorization before medications can be dispensed.**

### Authorization Flow:
1. **Consultation Created** → System detects NHIA patient in non-NHIA room
2. **Authorization Required** → Desk Office generates authorization code
3. **Prescription Created** → Inherits authorization requirement from consultation
4. **Dispensing Blocked** → Cannot dispense without valid authorization code
5. **Authorization Provided** → Medications can be dispensed

---

## Implementation Details

### 1. Consultation Level (Entry Point)

**File:** `consultations/models.py`

#### Automatic Detection
When a consultation is created, the system automatically checks:
- Is the patient an NHIA patient?
- Is the consulting room a non-NHIA room?

<augment_code_snippet path="consultations/models.py" mode="EXCERPT">
````python
def check_authorization_requirement(self):
    """
    Check if this consultation requires authorization.
    NHIA patients seen in non-NHIA rooms require authorization.
    """
    if self.is_nhia_patient() and not self.is_nhia_consulting_room():
        self.requires_authorization = True
        if not self.authorization_code:
            self.authorization_status = 'required'
        return True
    else:
        self.requires_authorization = False
        self.authorization_status = 'not_required'
        return False

def save(self, *args, **kwargs):
    # Auto-check authorization requirement on save
    self.check_authorization_requirement()
    super().save(*args, **kwargs)
````
</augment_code_snippet>

**Result:** Every consultation automatically sets `requires_authorization = True` if NHIA patient is in non-NHIA room.

---

### 2. Prescription Level (Inheritance)

**File:** `pharmacy/models.py`

#### Authorization Inheritance
When a prescription is created from a consultation, it inherits the authorization requirement:

<augment_code_snippet path="pharmacy/models.py" mode="EXCERPT">
````python
def check_authorization_requirement(self):
    """
    Check if this prescription requires authorization.
    NHIA patients with prescriptions from non-NHIA consultations require authorization.
    """
    if self.is_nhia_patient():
        # Check if linked to a consultation that requires authorization
        if self.consultation and self.consultation.requires_authorization:
            self.requires_authorization = True
            if not self.authorization_code:
                self.authorization_status = 'required'
            return True

    self.requires_authorization = False
    self.authorization_status = 'not_required'
    return False

def save(self, *args, **kwargs):
    """Override save to auto-check authorization requirement"""
    # Auto-check authorization requirement on save
    self.check_authorization_requirement()
    super().save(*args, **kwargs)
````
</augment_code_snippet>

**Result:** Prescriptions automatically inherit authorization requirement from consultations.

---

### 3. Dispensing Level (Enforcement)

**File:** `pharmacy/views.py`

#### Authorization Enforcement
Before dispensing, the system checks if authorization is required and valid:

<augment_code_snippet path="pharmacy/views.py" mode="EXCERPT">
````python
@login_required
def dispense_prescription(request, prescription_id):
    """View for dispensing a prescription"""
    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Check authorization requirement BEFORE allowing dispensing
    can_dispense, message = prescription.can_be_dispensed()
    if not can_dispense:
        messages.error(request, message)
        return redirect('pharmacy:prescription_detail', prescription_id=prescription.id)
    
    # ... rest of dispensing logic
````
</augment_code_snippet>

**File:** `pharmacy/models.py`

<augment_code_snippet path="pharmacy/models.py" mode="EXCERPT">
````python
def can_be_dispensed(self):
    """Check if prescription can be dispensed based on payment, authorization, and other conditions"""
    # Check if prescription is in a dispensable state
    if self.status in ['cancelled', 'dispensed']:
        return False, f'Cannot dispense prescription with status: {self.get_status_display()}'

    # Check authorization requirement for NHIA patients from non-NHIA consultations
    if self.requires_authorization:
        if not self.authorization_code:
            return False, 'Desk office authorization required for NHIA patient from non-NHIA unit. Please obtain authorization code before dispensing.'
        elif not self.authorization_code.is_valid():
            return False, f'Authorization code is {self.authorization_code.status}. Please obtain a valid authorization code.'

    # Check payment verification
    if not self.is_payment_verified():
        return False, 'Payment must be completed before dispensing medications'

    return True, 'Prescription is ready for dispensing'
````
</augment_code_snippet>

**Result:** Medications CANNOT be dispensed without valid authorization code.

---

## Complete Workflow Example

### Scenario: NHIA Patient in General Outpatient

#### Step 1: Consultation Created
```
Patient: John Doe (NHIA Patient)
Consulting Room: General Outpatient (Non-NHIA)
Doctor: Dr. Smith

System Action:
✅ Consultation saved
✅ requires_authorization = True
✅ authorization_status = 'required'
✅ Warning displayed to doctor
```

#### Step 2: Prescription Created
```
Doctor creates prescription for:
- Paracetamol 500mg
- Amoxicillin 250mg

System Action:
✅ Prescription saved
✅ Inherits requires_authorization = True from consultation
✅ authorization_status = 'required'
✅ Warning displayed on prescription detail page
```

#### Step 3: Dispensing Attempted (Without Authorization)
```
Pharmacist tries to dispense prescription

System Action:
❌ Dispensing BLOCKED
❌ Error message: "Desk office authorization required for NHIA patient from non-NHIA unit. Please obtain authorization code before dispensing."
❌ Redirected to prescription detail page
```

#### Step 4: Desk Office Authorization
```
Desk Office Staff:
1. Views authorization dashboard
2. Sees pending consultation/prescription
3. Generates authorization code: AUTH-2025-001
4. Sets expiry date and amount covered
5. Provides code to patient/pharmacist

System Action:
✅ Authorization code created
✅ Code status = 'active'
✅ Code linked to patient
```

#### Step 5: Authorization Code Applied
```
Pharmacist enters authorization code: AUTH-2025-001

System Action:
✅ Code validated
✅ prescription.authorization_code = AUTH-2025-001
✅ authorization_status = 'authorized'
✅ Prescription now ready for dispensing
```

#### Step 6: Dispensing Successful
```
Pharmacist dispenses medications

System Action:
✅ Authorization check PASSED
✅ Payment check PASSED
✅ Medications dispensed
✅ Authorization code marked as 'used'
```

---

## Key Features

### 1. Automatic Detection
- ✅ No manual intervention needed
- ✅ System automatically detects NHIA patients in non-NHIA rooms
- ✅ Authorization requirement set on save

### 2. Inheritance Chain
- ✅ Consultation → Prescription
- ✅ Authorization requirement flows through the system
- ✅ Consistent enforcement across all services

### 3. Multiple Enforcement Points
- ✅ Consultation level (detection)
- ✅ Prescription level (inheritance)
- ✅ Dispensing level (enforcement)

### 4. User-Friendly Messages
- ✅ Clear error messages
- ✅ Guidance on what to do
- ✅ Visual warnings on pages

---

## Desk Office Dashboard

**URL:** `/desk-office/authorization-dashboard/`

### Features:
1. **Pending Consultations** - Shows consultations requiring authorization
2. **Pending Prescriptions** - Shows prescriptions requiring authorization
3. **Pending Lab Tests** - Shows lab tests requiring authorization
4. **Pending Radiology** - Shows radiology orders requiring authorization
5. **Generate Codes** - Quick authorization code generation
6. **View All Codes** - List of all authorization codes

---

## Testing Checklist

### Test 1: NHIA Patient in Non-NHIA Room
- [ ] Create consultation for NHIA patient in General Outpatient
- [ ] Verify `requires_authorization = True`
- [ ] Verify warning banner shows
- [ ] Create prescription from consultation
- [ ] Verify prescription inherits authorization requirement
- [ ] Try to dispense without authorization
- [ ] Verify dispensing is BLOCKED

### Test 2: Authorization Code Generation
- [ ] Access Desk Office dashboard
- [ ] View pending consultations
- [ ] Generate authorization code
- [ ] Verify code is created with correct details
- [ ] Verify code status is 'active'

### Test 3: Dispensing with Authorization
- [ ] Apply authorization code to prescription
- [ ] Verify authorization_status = 'authorized'
- [ ] Try to dispense
- [ ] Verify dispensing is ALLOWED
- [ ] Verify code is marked as 'used'

### Test 4: NHIA Patient in NHIA Room (No Authorization)
- [ ] Create consultation for NHIA patient in NHIA room
- [ ] Verify `requires_authorization = False`
- [ ] Create prescription
- [ ] Verify prescription does NOT require authorization
- [ ] Dispense without authorization code
- [ ] Verify dispensing is ALLOWED

---

## Important Notes

### 1. Payment vs Authorization
- **Payment:** NHIA patients pay 10% of prescription cost (NOT exempt)
- **Authorization:** Required for non-NHIA consultations (separate from payment)
- **Both Required:** NHIA patients need BOTH authorization AND payment

### 2. NHIA Room Identification
- NHIA rooms are identified by department name = 'NHIA'
- Case-insensitive check
- Must be set correctly in system

### 3. Authorization Code Validity
- Codes have expiry dates
- Codes can be cancelled
- Codes are single-use (marked as 'used' after dispensing)
- Codes are service-type specific or general

---

## Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `pharmacy/models.py` | Added `save()` method to Prescription | Auto-check authorization on save |

---

## Related Documentation

1. **NHIA_AUTHORIZATION_IMPLEMENTATION.md** - Complete system implementation
2. **NHIA_AUTHORIZATION_TESTING_GUIDE.md** - Testing procedures
3. **NHIA_AUTHORIZATION_QUICK_START.md** - Quick start guide
4. **NHIA_EXEMPTION_COMPLETE_SUMMARY.md** - Payment exemption details

---

## Summary

### ✅ What Was Implemented
1. **Automatic authorization detection** at consultation level
2. **Authorization inheritance** from consultation to prescription
3. **Dispensing enforcement** - Cannot dispense without authorization
4. **Desk Office dashboard** for authorization management
5. **User-friendly error messages** and warnings

### ✅ Result
**NHIA patients seen in non-NHIA units CANNOT receive medications without Desk Office authorization.**

The system enforces this at multiple levels:
- Detection (Consultation)
- Inheritance (Prescription)
- Enforcement (Dispensing)

**Status:** ✅ Complete and Fully Enforced

---

**Document Version:** 1.0
**Last Updated:** 2025-09-30
**Status:** Complete

