# NHIA Authorization Implementation

## Overview
This document describes the implementation of desk office authorization requirements for NHIA patients seen in non-NHIA units or referred to other units.

## Implementation Progress

### ✅ Completed Tasks (10/13 - 77%)

1. **Database Models Updated** ✓
   - Added authorization fields to Consultation, Referral, Prescription, TestRequest, and RadiologyOrder models
   - All models now have `requires_authorization`, `authorization_status`, and `authorization_code` fields
   - Added `consultation` ForeignKey to Prescription, TestRequest, and RadiologyOrder for linking services to consultations

2. **Migrations Created and Applied** ✓
   - consultations: 0005_consultation_authorization_code_and_more.py
   - pharmacy: 0019_prescription_authorization_code_and_more.py
   - laboratory: 0003_testrequest_authorization_status_and_more.py
   - radiology: 0004_radiologyorder_authorization_status_and_more.py

3. **Authorization Logic Implemented** ✓
   - Automatic checking of authorization requirements on model save
   - Methods: `is_nhia_patient()`, `check_authorization_requirement()`, `can_be_processed()`/`can_be_dispensed()`

4. **Forms Updated** ✓
   - ConsultationForm, ReferralForm: Added authorization_code_input field with validation
   - PrescriptionForm: Added authorization_code_input field with validation
   - TestRequestForm: Added authorization_code_input field with validation
   - RadiologyOrderForm: Added authorization_code_input field with validation

5. **Utility Functions Created** ✓
   - nhia/authorization_utils.py with helper functions for authorization checking and validation

6. **UI Components Created** ✓
   - templates/includes/authorization_status.html - Displays authorization status badges and information
   - templates/includes/authorization_warning.html - Shows warning banners when authorization is required
   - templates/includes/authorization_code_input.html - Reusable authorization code input field

7. **Templates Updated** ✓
   - templates/consultations/consultation_detail.html - Shows authorization status and warnings
   - templates/consultations/doctor_consultation.html - Shows authorization status and warnings
   - consultations/templates/consultations/referral_detail.html - Shows authorization status and warnings

8. **Service Views Updated with Authorization Enforcement** ✓
   - pharmacy/views.py: dispense_prescription() - Checks authorization before allowing dispensing
   - laboratory/views.py: add_test_result(), update_test_request_status() - Checks authorization before processing
   - radiology/views.py: add_result(), schedule_order(), mark_completed() - Checks authorization before processing
   - radiology/enhanced_views.py: enhanced_add_result() - Checks authorization before result entry

9. **Desk Office Authorization Dashboard Created** ✓
   - desk_office/authorization_dashboard_views.py - Complete dashboard functionality
   - authorization_dashboard() - Main dashboard with statistics and pending requests
   - pending_consultations_list() - List all consultations requiring authorization
   - pending_referrals_list() - List all referrals requiring authorization
   - authorize_consultation() - Generate authorization code for consultation
   - authorize_referral() - Generate authorization code for referral
   - authorization_code_list() - List and filter all authorization codes

10. **Dashboard Templates Created** ✓
    - desk_office/templates/desk_office/authorization_dashboard.html - Main dashboard
    - desk_office/templates/desk_office/authorize_consultation.html - Consultation authorization form
    - desk_office/urls.py - Updated with new dashboard routes

### ✅ All Implementation Tasks Complete (13/13 - 100%)

11. **Dashboard Templates Completed** ✓
    - desk_office/templates/desk_office/authorize_referral.html
    - desk_office/templates/desk_office/pending_consultations.html
    - desk_office/templates/desk_office/pending_referrals.html
    - desk_office/templates/desk_office/authorization_code_list.html

12. **Testing Documentation Created** ✓
    - NHIA_AUTHORIZATION_TESTING_GUIDE.md - Comprehensive testing guide with scenarios

13. **System Verification** ✓
    - All migrations applied successfully
    - Django check passed with no errors
    - No pending migrations

### 🔄 Recommended Next Steps

1. **End-to-End Testing** - Follow NHIA_AUTHORIZATION_TESTING_GUIDE.md to test all scenarios
2. **User Training** - Create training materials based on test results
3. **Production Deployment** - Plan rollout strategy

## Business Rules

### When Authorization is Required

1. **Consultations**: NHIA patients seen/consulted in units OTHER than NHIA consultation rooms require authorization
2. **Referrals**: NHIA patients referred FROM NHIA units TO non-NHIA units require authorization
3. **Services**: When authorization is required for a consultation/referral, ALL services from that consultation require authorization:
   - Medication dispensing (Prescriptions)
   - Laboratory tests
   - Radiology orders
   - Other medical services

### Authorization Workflow

1. **Consultation/Referral Creation**:
   - System automatically detects if NHIA patient is in non-NHIA room or being referred to non-NHIA unit
   - Sets `requires_authorization = True` and `authorization_status = 'required'`
   - Displays warning to user

2. **Desk Office Authorization**:
   - Desk office staff generates authorization code for the patient
   - Code is linked to specific service types
   - Code has expiry date and status tracking

3. **Service Delivery**:
   - When creating prescriptions, lab tests, or radiology orders, system checks if authorization is required
   - If required, authorization code must be provided
   - System validates the code before allowing service delivery
   - Code is marked as 'used' after successful service delivery

## Implementation Details

### Database Changes

#### 1. Consultation Model (`consultations/models.py`)
Added fields:
- `requires_authorization` (BooleanField): Flags if authorization is needed
- `authorization_status` (CharField): Tracks authorization status (not_required, required, pending, authorized, rejected)
- `authorization_code` (ForeignKey to nhia.AuthorizationCode): Links to the authorization code

Added methods:
- `is_nhia_patient()`: Check if patient is NHIA
- `is_nhia_consulting_room()`: Check if room is NHIA
- `check_authorization_requirement()`: Auto-check if authorization needed
- `save()`: Override to auto-check authorization on save

#### 2. Referral Model (`consultations/models.py`)
Added fields:
- `requires_authorization` (BooleanField)
- `authorization_status` (CharField)
- `authorization_code` (ForeignKey to nhia.AuthorizationCode)

Added methods:
- `is_nhia_patient()`: Check if patient is NHIA
- `is_from_nhia_unit()`: Check if referral is from NHIA consultation
- `is_to_nhia_unit()`: Check if referred-to doctor is in NHIA department
- `check_authorization_requirement()`: Auto-check if authorization needed
- `save()`: Override to auto-check authorization on save

#### 3. Prescription Model (`pharmacy/models.py`)
Added fields:
- `requires_authorization` (BooleanField)
- `authorization_status` (CharField)
- `authorization_code` (ForeignKey to nhia.AuthorizationCode)
- `consultation` (ForeignKey to Consultation): Links prescription to consultation

Added methods:
- `is_nhia_patient()`: Check if patient is NHIA
- `check_authorization_requirement()`: Check if authorization needed based on consultation
- Updated `can_be_dispensed()`: Now checks for authorization before allowing dispensing

#### 4. TestRequest Model (`laboratory/models.py`)
Added fields:
- `requires_authorization` (BooleanField)
- `authorization_status` (CharField)
- `authorization_code` (ForeignKey to nhia.AuthorizationCode)
- `consultation` (ForeignKey to Consultation): Links test request to consultation

Added methods:
- `is_nhia_patient()`: Check if patient is NHIA
- `check_authorization_requirement()`: Check if authorization needed based on consultation
- `can_be_processed()`: Check if test can be processed (includes authorization validation)

#### 5. RadiologyOrder Model (`radiology/models.py`)
Added fields:
- `requires_authorization` (BooleanField)
- `authorization_status` (CharField)
- `authorization_code` (ForeignKey to nhia.AuthorizationCode)
- `consultation` (ForeignKey to Consultation): Links radiology order to consultation

Added methods:
- `is_nhia_patient()`: Check if patient is NHIA
- `check_authorization_requirement()`: Check if authorization needed based on consultation
- `can_be_processed()`: Check if order can be processed (includes authorization validation)

### Utility Functions (`nhia/authorization_utils.py`)

Created comprehensive utility module with functions:
- `is_nhia_patient(patient)`: Check if patient is NHIA
- `is_nhia_department(department)`: Check if department is NHIA
- `is_nhia_consulting_room(consulting_room)`: Check if room is NHIA
- `requires_consultation_authorization(patient, consulting_room)`: Check consultation auth requirement
- `requires_referral_authorization(patient, from_consultation, to_doctor)`: Check referral auth requirement
- `requires_prescription_authorization(patient, consultation)`: Check prescription auth requirement
- `requires_lab_test_authorization(patient, consultation)`: Check lab test auth requirement
- `requires_radiology_authorization(patient, consultation)`: Check radiology auth requirement
- `validate_authorization_code(authorization_code, service_type)`: Validate auth code
- `get_authorization_status_display(requires_auth, has_code, code_valid)`: Get display info

### Form Updates

#### 1. ConsultationForm (`consultations/forms.py`)
Added:
- `authorization_code_input` field: Text input for entering authorization code
- `clean_authorization_code_input()`: Validates the code
- Updated `save()`: Links authorization code to consultation

#### 2. ReferralForm (`consultations/forms.py`)
Added:
- `authorization_code_input` field: Text input for entering authorization code
- `clean_authorization_code_input()`: Validates the code
- Updated `save()`: Links authorization code to referral

### Migrations Applied

1. `consultations/migrations/0005_consultation_authorization_code_and_more.py`:
   - Added authorization fields to Consultation model
   - Added authorization fields to Referral model

2. `pharmacy/migrations/0019_prescription_authorization_code_and_more.py`:
   - Added authorization fields to Prescription model
   - Added consultation link to Prescription model

## Remaining Implementation Tasks

### High Priority

1. **Update Prescription Views** (`pharmacy/views.py`):
   - Modify prescription creation to check consultation authorization
   - Add authorization code input to prescription forms
   - Enforce authorization before dispensing

2. **Update Lab Test Views** (`laboratory/views.py`):
   - Add consultation link to TestRequest model
   - Modify test request creation to check consultation authorization
   - Add authorization code input to test request forms
   - Enforce authorization before processing tests

3. **Update Radiology Views** (`radiology/views.py`):
   - Add consultation link to RadiologyOrder model
   - Modify radiology order creation to check consultation authorization
   - Add authorization code input to radiology order forms
   - Enforce authorization before processing orders

4. **Create Authorization UI Components**:
   - Create reusable template partial for authorization status display
   - Create reusable template partial for authorization code input
   - Add authorization warnings/alerts to forms

5. **Update Desk Office Authorization Generation**:
   - Enhance authorization code generation to support consultations/referrals
   - Add ability to view pending authorization requests
   - Create dashboard for tracking authorization workflow

### Medium Priority

6. **Add Validation and Enforcement**:
   - Backend validation to prevent service delivery without authorization
   - Appropriate error messages and user feedback
   - Audit logging for authorization events

7. **Create Authorization Tracking Dashboard**:
   - View for desk office staff to see pending authorizations
   - View consultations/referrals requiring authorization
   - Manage authorization workflow

8. **Testing**:
   - End-to-end testing of authorization workflow
   - Test all service types (prescriptions, lab, radiology)
   - Test edge cases and error handling

## Usage Examples

### Example 1: NHIA Patient in Non-NHIA Room

```python
# Consultation is created
consultation = Consultation.objects.create(
    patient=nhia_patient,
    doctor=doctor,
    consulting_room=general_room,  # Non-NHIA room
    chief_complaint="Headache",
    symptoms="Severe headache for 2 days"
)

# System automatically sets:
# consultation.requires_authorization = True
# consultation.authorization_status = 'required'

# Desk office generates authorization code
auth_code = AuthorizationCode.objects.create(
    patient=nhia_patient,
    service_type='general',
    code='AUTH-2024-001',
    expiry_date=date.today() + timedelta(days=30)
)

# Doctor/staff enters authorization code
consultation.authorization_code = auth_code
consultation.authorization_status = 'authorized'
consultation.save()

# Now services can be delivered
```

### Example 2: Prescription from Authorized Consultation

```python
# Create prescription from authorized consultation
prescription = Prescription.objects.create(
    patient=nhia_patient,
    doctor=doctor,
    consultation=consultation,  # Links to consultation
    diagnosis="Migraine"
)

# System automatically checks:
# prescription.check_authorization_requirement()
# If consultation.requires_authorization == True:
#     prescription.requires_authorization = True
#     prescription.authorization_code = consultation.authorization_code

# Dispensing check
can_dispense, message = prescription.can_be_dispensed()
# Returns: (False, "Desk office authorization required...") if no auth code
# Returns: (True, "Prescription is ready for dispensing") if authorized
```

## Files Modified

1. `consultations/models.py` - Added authorization fields and methods to Consultation and Referral
2. `pharmacy/models.py` - Added authorization fields and methods to Prescription
3. `consultations/forms.py` - Added authorization code input to ConsultationForm and ReferralForm
4. `nhia/authorization_utils.py` - Created utility functions for authorization checking
5. `consultations/migrations/0005_*.py` - Database migration for consultations
6. `pharmacy/migrations/0019_*.py` - Database migration for pharmacy

## Next Steps

To complete the implementation, the following tasks need to be completed:

1. Update prescription views and forms to enforce authorization
2. Update lab test views and forms to enforce authorization
3. Update radiology views and forms to enforce authorization
4. Create UI components for authorization display
5. Enhance desk office authorization generation
6. Add comprehensive validation and error handling
7. Create authorization tracking dashboard
8. Perform end-to-end testing

## Notes

- The system automatically detects when authorization is required based on patient type and consulting room/department
- Authorization codes are validated for status and expiry before use
- Services cannot be delivered without valid authorization when required
- The implementation maintains backward compatibility with existing non-NHIA workflows

