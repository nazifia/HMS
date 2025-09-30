# NHIA Authorization System - Testing Guide

## Overview
This guide provides step-by-step instructions for testing the NHIA authorization system implementation.

## Prerequisites
- All migrations have been applied ✓
- Django development server is running
- Test NHIA patient exists in the system
- Test users with appropriate permissions (doctor, desk office staff, pharmacist, lab technician, radiologist)

## Test Scenarios

### Scenario 1: NHIA Patient in Non-NHIA Consulting Room

#### Step 1: Create/Select NHIA Patient
1. Navigate to Patients module
2. Create or select an existing NHIA patient
3. Verify patient has `patient_type = 'nhia'`
4. Note the patient ID for testing

#### Step 2: Create Consultation in Non-NHIA Room
1. Login as a doctor
2. Navigate to Consultations
3. Create a new consultation for the NHIA patient
4. **Important**: Select a consulting room that is NOT an NHIA room
5. Fill in consultation details (chief complaint, history, examination)
6. Save the consultation

**Expected Results**:
- ✅ Consultation is saved successfully
- ✅ `requires_authorization` field is automatically set to `True`
- ✅ `authorization_status` is set to `'required'`
- ✅ Warning banner appears: "This consultation requires desk office authorization"
- ✅ Authorization status badge shows "Authorization Required"

#### Step 3: Attempt to Create Prescription Without Authorization
1. From the consultation detail page, try to create a prescription
2. Add medications to the prescription
3. Save the prescription

**Expected Results**:
- ✅ Prescription is created
- ✅ `requires_authorization` is automatically set to `True`
- ✅ `authorization_status` is set to `'required'`

#### Step 4: Attempt to Dispense Without Authorization
1. Login as pharmacist
2. Navigate to the prescription
3. Try to dispense the medication

**Expected Results**:
- ❌ Dispensing is blocked
- ✅ Error message: "Desk office authorization required for NHIA patient from non-NHIA unit."
- ✅ User is redirected back to prescription detail page

#### Step 5: Generate Authorization Code (Desk Office)
1. Login as desk office staff
2. Navigate to `/desk-office/authorization-dashboard/`
3. Verify the consultation appears in "Pending Consultations" section
4. Click "Authorize" button for the consultation
5. Fill in authorization form:
   - Amount: 500.00
   - Validity Period: 30 days
   - Notes: "Test authorization for consultation"
6. Click "Generate Authorization Code"

**Expected Results**:
- ✅ Authorization code is generated (format: AUTH-YYYYMMDD-XXXXXX)
- ✅ Success message appears with the code
- ✅ Consultation's `authorization_code` field is linked to the new code
- ✅ Consultation's `authorization_status` is updated to `'authorized'`
- ✅ Code appears in "Recent Authorization Codes" table

#### Step 6: Verify Authorization on Consultation
1. Navigate back to the consultation detail page
2. Check the authorization status

**Expected Results**:
- ✅ Authorization status badge shows "Authorized" (green)
- ✅ Authorization code is displayed
- ✅ No warning banner appears

#### Step 7: Dispense Prescription With Authorization
1. Login as pharmacist
2. Navigate to the prescription
3. Try to dispense the medication

**Expected Results**:
- ✅ Dispensing is allowed
- ✅ Medication is dispensed successfully
- ✅ Prescription status is updated

---

### Scenario 2: NHIA Patient Referred from NHIA to Non-NHIA Unit

#### Step 1: Create Initial NHIA Consultation
1. Login as NHIA doctor
2. Create consultation for NHIA patient in NHIA consulting room
3. Save consultation

**Expected Results**:
- ✅ Consultation is saved
- ✅ `requires_authorization` is `False` (NHIA patient in NHIA room)
- ✅ No authorization warning appears

#### Step 2: Create Referral to Non-NHIA Doctor
1. From the NHIA consultation, create a referral
2. Select a doctor who works in a non-NHIA department
3. Fill in referral reason and priority
4. Save referral

**Expected Results**:
- ✅ Referral is saved
- ✅ `requires_authorization` is automatically set to `True`
- ✅ `authorization_status` is set to `'required'`
- ✅ Warning banner appears on referral detail page

#### Step 3: Generate Authorization for Referral
1. Login as desk office staff
2. Navigate to authorization dashboard
3. Find the referral in "Pending Referrals" section
4. Click "Authorize" button
5. Generate authorization code

**Expected Results**:
- ✅ Authorization code is generated
- ✅ Referral is linked to the code
- ✅ Referral status updated to `'authorized'`

#### Step 4: Accept Referral and Create Consultation
1. Login as the referred-to doctor
2. Accept the referral
3. Create consultation from the referral

**Expected Results**:
- ✅ Consultation inherits authorization from referral
- ✅ Services from this consultation can be delivered

---

### Scenario 3: Lab Test Authorization

#### Step 1: Order Lab Test from Non-NHIA Consultation
1. From a consultation requiring authorization, order a lab test
2. Select test type (e.g., CBC, Blood Sugar)
3. Save test request

**Expected Results**:
- ✅ Test request is created
- ✅ `requires_authorization` is `True` (inherited from consultation)
- ✅ `authorization_status` is `'required'`

#### Step 2: Attempt to Process Test Without Authorization
1. Login as lab technician
2. Navigate to the test request
3. Try to add test results

**Expected Results**:
- ❌ Result entry is blocked
- ✅ Error message: "Desk office authorization required for NHIA patient from non-NHIA unit."

#### Step 3: Enter Authorization Code
1. Obtain authorization code from desk office (from consultation authorization)
2. Edit the test request
3. Enter the authorization code in the "Authorization Code" field
4. Save

**Expected Results**:
- ✅ Authorization code is validated
- ✅ Test request status updated to `'authorized'`
- ✅ Test can now be processed

#### Step 4: Process Test With Authorization
1. Try to add test results again
2. Enter test results
3. Save

**Expected Results**:
- ✅ Results are saved successfully
- ✅ Test status updated to completed

---

### Scenario 4: Radiology Authorization

#### Step 1: Order Radiology from Non-NHIA Consultation
1. From a consultation requiring authorization, order radiology
2. Select imaging type (e.g., X-Ray, CT Scan)
3. Save radiology order

**Expected Results**:
- ✅ Radiology order is created
- ✅ `requires_authorization` is `True`
- ✅ `authorization_status` is `'required'`

#### Step 2: Attempt to Schedule Without Authorization
1. Login as radiologist
2. Navigate to the radiology order
3. Try to schedule the order

**Expected Results**:
- ❌ Scheduling is blocked
- ✅ Error message appears

#### Step 3: Add Authorization and Complete
1. Enter authorization code from consultation
2. Schedule the order
3. Perform imaging
4. Add results

**Expected Results**:
- ✅ All operations succeed with valid authorization

---

### Scenario 5: Authorization Code Management

#### Step 1: View All Authorization Codes
1. Login as desk office staff
2. Navigate to `/desk-office/authorization-codes/`

**Expected Results**:
- ✅ All authorization codes are listed
- ✅ Codes show status (active, used, expired)
- ✅ Patient information is displayed

#### Step 2: Filter Authorization Codes
1. Use filters to search by:
   - Status (active, used, expired)
   - Service type
   - Patient name/ID
2. Apply filters

**Expected Results**:
- ✅ Results are filtered correctly
- ✅ DataTables sorting and pagination work

#### Step 3: Track Code Usage
1. Find a code that was used for dispensing
2. Check the "Used At" column

**Expected Results**:
- ✅ Usage timestamp is recorded
- ✅ Status shows "Used"

---

## Dashboard Testing

### Test Authorization Dashboard
1. Navigate to `/desk-office/authorization-dashboard/`
2. Verify all statistics cards show correct counts
3. Check pending consultations table
4. Check pending referrals table
5. Check recent authorization codes table

**Expected Results**:
- ✅ All counts are accurate
- ✅ Tables display correct data
- ✅ Quick action buttons work
- ✅ "View All" links navigate correctly

---

## Edge Cases to Test

### Edge Case 1: Invalid Authorization Code
1. Try to enter an invalid/non-existent authorization code
2. Save the form

**Expected Results**:
- ❌ Form validation fails
- ✅ Error message: "Invalid authorization code"

### Edge Case 2: Expired Authorization Code
1. Create an authorization code with 1-day expiry
2. Manually update the expiry date to yesterday in the database
3. Try to use the code

**Expected Results**:
- ❌ Code is rejected
- ✅ Error message: "Authorization code is expired"

### Edge Case 3: Already Used Authorization Code
1. Use an authorization code for dispensing
2. Try to use the same code again

**Expected Results**:
- ❌ Code is rejected
- ✅ Error message: "Authorization code is used"

### Edge Case 4: Regular Patient in Non-NHIA Room
1. Create consultation for non-NHIA patient in any room
2. Check authorization requirement

**Expected Results**:
- ✅ `requires_authorization` is `False`
- ✅ No authorization needed
- ✅ Services can be delivered without authorization

---

## Checklist

### Pre-Testing
- [ ] All migrations applied
- [ ] Test data created (NHIA patients, doctors, rooms)
- [ ] User accounts with appropriate permissions
- [ ] Development server running

### Functional Testing
- [ ] Scenario 1: Non-NHIA consultation authorization
- [ ] Scenario 2: Referral authorization
- [ ] Scenario 3: Lab test authorization
- [ ] Scenario 4: Radiology authorization
- [ ] Scenario 5: Code management

### UI/UX Testing
- [ ] Authorization status badges display correctly
- [ ] Warning banners appear when needed
- [ ] Error messages are clear and helpful
- [ ] Dashboard statistics are accurate
- [ ] DataTables work (sorting, filtering, pagination)

### Edge Cases
- [ ] Invalid authorization codes rejected
- [ ] Expired codes rejected
- [ ] Used codes rejected
- [ ] Regular patients don't require authorization

### Integration Testing
- [ ] Authorization flows from consultation to services
- [ ] Referral authorization inheritance works
- [ ] Code validation across all modules
- [ ] Desk office dashboard shows all pending items

---

## Troubleshooting

### Issue: Authorization not required when it should be
**Check**:
- Patient's `patient_type` is 'nhia'
- Consulting room is not an NHIA room
- `check_authorization_requirement()` method is being called on save

### Issue: Service delivery still blocked after authorization
**Check**:
- Authorization code is correctly linked to the service
- Code status is 'active'
- Code has not expired
- `can_be_dispensed()`/`can_be_processed()` method returns True

### Issue: Dashboard not showing pending items
**Check**:
- Items have `requires_authorization=True`
- Items have `authorization_status` in ['required', 'pending']
- Database queries are correct
- User has permission to view dashboard

---

## Success Criteria

The implementation is successful if:
1. ✅ NHIA patients in non-NHIA rooms automatically require authorization
2. ✅ Services cannot be delivered without valid authorization
3. ✅ Desk office can generate and manage authorization codes
4. ✅ Authorization codes can be validated and used across all services
5. ✅ Dashboard provides complete visibility of pending authorizations
6. ✅ All edge cases are handled gracefully
7. ✅ User experience is smooth with clear feedback

---

## Next Steps After Testing

1. **Document Issues**: Record any bugs or unexpected behavior
2. **User Training**: Create training materials based on test results
3. **Performance Testing**: Test with larger datasets
4. **Security Review**: Ensure authorization cannot be bypassed
5. **Production Deployment**: Plan rollout strategy

