# NHIA Authorization System - Step-by-Step Walkthrough

## Overview
This document provides a complete step-by-step walkthrough of testing the NHIA authorization system using the test data that was just created.

## Prerequisites ✓
- ✅ Test data has been created (run `python manage.py setup_nhia_test_data`)
- ✅ Django development server is running (`python manage.py runserver`)
- ✅ You have the test user credentials (all passwords: `test123`)

## Test Data Summary

### Test Users (Password: test123)
| Username | Role | Department | Full Name |
|----------|------|------------|-----------|
| test_nhia_doctor | Doctor | NHIA | Dr. John Mensah |
| test_general_doctor | Doctor | General Medicine | Dr. Sarah Osei |
| test_cardiology_doctor | Doctor | Cardiology | Dr. Michael Asante |
| test_desk_office | Admin | Administration | Grace Boateng |

### Test Patients
**NHIA Patients:**
1. Test NHIA Patient One (NHIA: NHIA-TEST-0001)
2. Test NHIA Patient Two (NHIA: NHIA-TEST-0002)
3. Test NHIA Patient Three (NHIA: NHIA-TEST-0003)

**Regular Patients:**
1. Test Regular Patient One
2. Test Regular Patient Two

### Consulting Rooms
| Room Number | Department | Floor |
|-------------|------------|-------|
| NHIA-101 | NHIA | 1st Floor |
| GEN-201 | General Medicine | 2nd Floor |
| CARD-301 | Cardiology | 3rd Floor |

---

## Walkthrough 1: NHIA Patient in Non-NHIA Room (Complete Flow)

### Step 1: Login as General Medicine Doctor
1. Navigate to: `http://localhost:8000/accounts/login/`
2. Enter credentials:
   - Username: `test_general_doctor`
   - Password: `test123`
3. Click "Login"

**Expected Result:** ✅ Successfully logged in as Dr. Sarah Osei

### Step 2: Create Consultation for NHIA Patient in Non-NHIA Room
1. Navigate to: `http://localhost:8000/consultations/create/`
2. Fill in the consultation form:
   - **Patient**: Select "Test NHIA Patient One"
   - **Consulting Room**: Select "GEN-201 - General Medicine"
   - **Chief Complaint**: "Chest pain and shortness of breath"
   - **Symptoms**: "Patient reports chest pain for 2 days, difficulty breathing"
   - **Diagnosis**: "Suspected cardiac issue - requires specialist review"
   - **Consultation Notes**: "Refer to cardiology for further evaluation"
3. Click "Save" or "Submit"

**Expected Results:**
- ✅ Consultation is created successfully
- ✅ You are redirected to the consultation detail page
- ✅ **WARNING BANNER** appears at the top: "This consultation requires desk office authorization"
- ✅ **Authorization Status Badge** shows "Authorization Required" (yellow/warning color)
- ✅ Message explains: "This NHIA patient was seen in a non-NHIA consulting room"

**Screenshot Checkpoint:** Take a screenshot showing the warning banner and authorization status

### Step 3: Attempt to Create Prescription (Will Require Authorization)
1. From the consultation detail page, click "Add Prescription" or navigate to prescriptions
2. Create a prescription:
   - **Medication**: Select any medication (e.g., "Paracetamol 500mg")
   - **Dosage**: "1 tablet"
   - **Frequency**: "Three times daily"
   - **Duration**: "7 days"
3. Save the prescription

**Expected Results:**
- ✅ Prescription is created
- ✅ Prescription also shows "Authorization Required" status
- ✅ Warning appears that authorization is needed before dispensing

### Step 4: Attempt to Dispense Without Authorization (Pharmacist)
1. Logout from doctor account
2. Login as pharmacist (or use test_desk_office for now)
3. Navigate to the prescription
4. Try to click "Dispense" button

**Expected Results:**
- ❌ **Dispensing is BLOCKED**
- ✅ Error message appears: "Desk office authorization required for NHIA patient from non-NHIA unit."
- ✅ User is redirected back to prescription detail page
- ✅ No medications are dispensed

**Screenshot Checkpoint:** Take a screenshot showing the error message

### Step 5: Generate Authorization Code (Desk Office)
1. Logout and login as desk office staff:
   - Username: `test_desk_office`
   - Password: `test123`
2. Navigate to: `http://localhost:8000/desk-office/authorization-dashboard/`
3. **Verify Dashboard:**
   - Check that "Total Pending" shows at least 1
   - Check that "Consultations" count shows 1
   - Find the consultation in "Pending Consultations" table

**Expected Results:**
- ✅ Dashboard loads successfully
- ✅ Statistics cards show correct counts
- ✅ Consultation appears in "Pending Consultations" section
- ✅ Shows: Patient name, Doctor name, Room, Date

**Screenshot Checkpoint:** Take a screenshot of the dashboard

4. Click "Authorize" button for the consultation
5. Fill in the authorization form:
   - **Amount Covered**: `500.00`
   - **Validity Period**: `30 Days`
   - **Notes**: `Test authorization for general medicine consultation`
6. Click "Generate Authorization Code"

**Expected Results:**
- ✅ Success message appears with the authorization code (format: AUTH-YYYYMMDD-XXXXXX)
- ✅ You are redirected back to the dashboard
- ✅ The consultation no longer appears in "Pending Consultations"
- ✅ The code appears in "Recent Authorization Codes" table

**Important:** Copy the authorization code - you'll need it for the next steps!

### Step 6: Verify Authorization on Consultation
1. Navigate back to the consultation detail page
2. Check the authorization status

**Expected Results:**
- ✅ Warning banner is GONE
- ✅ Authorization status badge shows "Authorized" (green color)
- ✅ Authorization code is displayed
- ✅ Shows: Code, Amount, Expiry Date

**Screenshot Checkpoint:** Take a screenshot showing the authorized status

### Step 7: Dispense Prescription With Authorization
1. Navigate to the prescription
2. Try to dispense again

**Expected Results:**
- ✅ **Dispensing is NOW ALLOWED**
- ✅ Medication can be dispensed successfully
- ✅ Prescription status updates to "Dispensed"
- ✅ No error messages

**Screenshot Checkpoint:** Take a screenshot showing successful dispensing

### Step 8: Verify Authorization Code is Marked as Used
1. Go back to desk office dashboard
2. Navigate to: `http://localhost:8000/desk-office/authorization-codes/`
3. Find the authorization code you generated

**Expected Results:**
- ✅ Code status shows "Used" (gray/secondary badge)
- ✅ "Used At" column shows timestamp
- ✅ Code cannot be reused

---

## Walkthrough 2: NHIA Patient Referred from NHIA to Non-NHIA Unit

### Step 1: Login as NHIA Doctor
1. Logout and login as:
   - Username: `test_nhia_doctor`
   - Password: `test123`

### Step 2: Create Consultation in NHIA Room
1. Navigate to: `http://localhost:8000/consultations/create/`
2. Fill in the form:
   - **Patient**: Select "Test NHIA Patient Two"
   - **Consulting Room**: Select "NHIA-101 - NHIA"
   - **Chief Complaint**: "Persistent chest pain"
   - **Symptoms**: "Chest pain, irregular heartbeat"
   - **Diagnosis**: "Requires cardiology specialist evaluation"
3. Save the consultation

**Expected Results:**
- ✅ Consultation is created
- ✅ **NO authorization warning** (NHIA patient in NHIA room)
- ✅ Authorization status shows "Not Required"

### Step 3: Create Referral to Cardiology (Non-NHIA Department)
1. From the consultation, create a referral:
   - **Referred To**: Select "Dr. Michael Asante" (Cardiology)
   - **Reason**: "Suspected cardiac arrhythmia - requires specialist evaluation"
   - **Priority**: "Urgent"
2. Save the referral

**Expected Results:**
- ✅ Referral is created
- ✅ **WARNING BANNER** appears: "This referral requires desk office authorization"
- ✅ Authorization status shows "Authorization Required"
- ✅ Explanation: "NHIA patient referred from NHIA to non-NHIA unit"

**Screenshot Checkpoint:** Take a screenshot of the referral with authorization warning

### Step 4: Generate Authorization for Referral (Desk Office)
1. Login as desk office staff (`test_desk_office`)
2. Go to dashboard: `http://localhost:8000/desk-office/authorization-dashboard/`
3. Check "Pending Referrals" section
4. Click "Authorize" for the referral
5. Generate authorization code:
   - Amount: `1000.00`
   - Validity: `30 Days`
   - Notes: `Cardiology referral authorization`

**Expected Results:**
- ✅ Authorization code generated
- ✅ Referral is authorized
- ✅ Code appears in recent codes

### Step 5: Accept Referral and Create Consultation (Cardiologist)
1. Login as cardiology doctor (`test_cardiology_doctor`)
2. View the referral
3. Accept the referral
4. Create consultation from the referral

**Expected Results:**
- ✅ Consultation inherits authorization from referral
- ✅ Services from this consultation can be delivered
- ✅ No additional authorization needed

---

## Walkthrough 3: Lab Test Authorization

### Step 1: Order Lab Test from Non-NHIA Consultation
1. Use the consultation created in Walkthrough 1 (already authorized)
2. Order a lab test:
   - **Test Type**: "Complete Blood Count (CBC)"
   - **Priority**: "Routine"
   - **Notes**: "Pre-cardiology evaluation"

**Expected Results:**
- ✅ Test request is created
- ✅ Inherits authorization from consultation
- ✅ Shows "Authorized" status

### Step 2: Process Test With Authorization
1. Login as lab technician (use `test_desk_office` for now)
2. Navigate to the test request
3. Add test results
4. Mark as completed

**Expected Results:**
- ✅ Test can be processed
- ✅ Results can be entered
- ✅ No authorization errors

---

## Walkthrough 4: Testing Edge Cases

### Edge Case 1: Invalid Authorization Code
1. Create a new consultation requiring authorization
2. Try to enter an invalid code: "INVALID-CODE-123"
3. Save

**Expected Results:**
- ❌ Form validation fails
- ✅ Error message: "Invalid authorization code"

### Edge Case 2: Regular Patient in Non-NHIA Room
1. Login as general doctor
2. Create consultation for "Test Regular Patient One" in "GEN-201"

**Expected Results:**
- ✅ Consultation is created
- ✅ **NO authorization required** (not an NHIA patient)
- ✅ Services can be delivered immediately

### Edge Case 3: NHIA Patient in NHIA Room
1. Login as NHIA doctor
2. Create consultation for "Test NHIA Patient Three" in "NHIA-101"

**Expected Results:**
- ✅ Consultation is created
- ✅ **NO authorization required** (NHIA patient in NHIA room)
- ✅ Services can be delivered immediately

---

## Verification Checklist

After completing all walkthroughs, verify:

- [ ] NHIA patients in non-NHIA rooms require authorization
- [ ] NHIA patients referred to non-NHIA units require authorization
- [ ] Services cannot be delivered without valid authorization
- [ ] Desk office can generate authorization codes
- [ ] Authorization codes can be validated and used
- [ ] Dashboard shows all pending authorizations
- [ ] Authorization codes are marked as used after consumption
- [ ] Regular patients don't require authorization
- [ ] NHIA patients in NHIA rooms don't require authorization
- [ ] Invalid codes are rejected
- [ ] Used codes cannot be reused

---

## Troubleshooting

### Issue: Can't see the consultation in pending list
**Solution:** Refresh the dashboard page, ensure the consultation requires authorization

### Issue: Dispensing still blocked after authorization
**Solution:** Verify the authorization code is correctly linked to the consultation

### Issue: Dashboard not loading
**Solution:** Check that you're logged in as desk office staff, verify URL is correct

---

## Next Steps

After completing this walkthrough:
1. Document any issues found
2. Test with real patient data (if available)
3. Train staff using this walkthrough
4. Provide feedback for improvements

---

**Last Updated:** 2025-09-30
**Version:** 1.0
**Status:** Ready for Testing

