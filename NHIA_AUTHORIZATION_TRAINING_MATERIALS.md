# NHIA Authorization System - Training Materials

## Table of Contents
1. [Overview](#overview)
2. [Training for Desk Office Staff](#training-for-desk-office-staff)
3. [Training for Doctors](#training-for-doctors)
4. [Training for Pharmacy Staff](#training-for-pharmacy-staff)
5. [Training for Laboratory Staff](#training-for-laboratory-staff)
6. [Training for Radiology Staff](#training-for-radiology-staff)
7. [Common Questions & Answers](#common-questions--answers)

---

## Overview

### What is the NHIA Authorization System?

The NHIA Authorization System ensures that NHIA patients who receive services outside of NHIA units must first obtain authorization from the desk office. This helps:
- Track NHIA patient services across departments
- Ensure proper billing and reimbursement
- Maintain compliance with NHIA regulations
- Prevent unauthorized service delivery

### When is Authorization Required?

Authorization is required in TWO situations:
1. **NHIA patient seen in a non-NHIA consulting room**
2. **NHIA patient referred from NHIA unit to a non-NHIA unit**

### When is Authorization NOT Required?

- Regular (non-NHIA) patients - never require authorization
- NHIA patients seen in NHIA consulting rooms - no authorization needed
- NHIA patients referred within NHIA units - no authorization needed

---

## Training for Desk Office Staff

### Your Role
You are responsible for:
- Monitoring pending authorization requests
- Generating authorization codes for eligible consultations and referrals
- Managing and tracking all authorization codes
- Providing codes to patients or service units

### Daily Workflow

#### 1. Start Your Day
1. Login to the system
2. Navigate to: **Desk Office → Authorization Dashboard**
3. Review the statistics:
   - Total Pending Authorizations
   - Pending Consultations
   - Pending Referrals
   - Pending Services (Prescriptions, Lab Tests, Radiology)

#### 2. Process Pending Authorizations

**For Consultations:**
1. Review "Pending Consultations" section
2. Click "Authorize" button for a consultation
3. Review consultation details:
   - Patient information
   - Doctor name
   - Consulting room
   - Chief complaint
   - Why authorization is required
4. Fill in authorization form:
   - **Amount Covered**: Enter the amount this code will cover (e.g., 500.00)
   - **Validity Period**: Select how long the code is valid (usually 30 days)
   - **Notes**: Add any relevant notes
5. Click "Generate Authorization Code"
6. **Important**: Copy the generated code and provide it to:
   - The patient (preferred), OR
   - The service delivery unit (pharmacy, lab, radiology)

**For Referrals:**
1. Review "Pending Referrals" section
2. Click "Authorize" button for a referral
3. Review referral details:
   - Patient information
   - Referring doctor
   - Referred-to doctor
   - Reason for referral
   - Priority level
4. Follow same process as consultations

#### 3. Manage Authorization Codes
1. Navigate to: **Desk Office → Authorization Codes**
2. Use filters to search:
   - By status (active, used, expired)
   - By service type
   - By patient name or ID
3. Monitor code usage:
   - Active codes - not yet used
   - Used codes - already consumed
   - Expired codes - past expiry date

### Best Practices

✅ **DO:**
- Process authorization requests promptly (within 1 hour)
- Set appropriate expiry periods (30 days is standard)
- Add clear notes to codes for future reference
- Verify patient is actually NHIA before generating code
- Keep a log of codes provided to patients

❌ **DON'T:**
- Generate codes for non-NHIA patients
- Set very short expiry periods (less than 7 days) without good reason
- Reuse or share authorization codes
- Generate codes without reviewing the consultation/referral details

### Common Scenarios

**Scenario 1: Patient Requests Authorization**
- Patient: "I was seen by Dr. Osei in General Medicine and need authorization for my medications"
- You: 
  1. Check the dashboard for the consultation
  2. Verify it's pending authorization
  3. Generate the code
  4. Provide code to patient
  5. Explain: "Give this code to the pharmacy when collecting your medications"

**Scenario 2: Urgent Case**
- Doctor calls: "I have an urgent NHIA patient needing immediate lab tests"
- You:
  1. Ask for patient name and consultation details
  2. Find the consultation in dashboard
  3. Generate code immediately
  4. Provide code to doctor or lab directly
  5. Set shorter validity period if needed (7-14 days)

**Scenario 3: Code Already Expired**
- Patient: "My authorization code has expired"
- You:
  1. Check the old code in the system
  2. Verify it's expired
  3. Generate a NEW code
  4. Provide new code to patient
  5. Note: Old code cannot be reactivated

---

## Training for Doctors

### Your Role
You need to:
- Identify when NHIA patients require authorization
- Inform patients about authorization requirements
- Coordinate with desk office for urgent cases

### What You'll See

#### When Creating Consultations
If you see an NHIA patient in a non-NHIA consulting room:
- **Warning Banner** appears: "This consultation requires desk office authorization"
- **Yellow Badge**: "Authorization Required"
- **Explanation**: Why authorization is needed

#### When Creating Referrals
If you refer an NHIA patient from NHIA to a non-NHIA unit:
- Same warning banner and badge appear
- Referral is flagged for authorization

### What You Should Do

#### Step 1: Inform the Patient
When you see the authorization warning:
1. Explain to the patient: "Since you're an NHIA patient being seen in this department, you'll need to visit the desk office for authorization before getting your medications/tests"
2. Direct them to: "Please go to the desk office on the ground floor"
3. Reassure them: "It's a quick process, they'll give you a code"

#### Step 2: For Urgent Cases
If the patient needs immediate service:
1. Call the desk office directly
2. Provide patient details and consultation ID
3. Request immediate authorization
4. Desk office will generate code and provide it to you or the service unit

#### Step 3: Document in Notes
Add to consultation notes:
- "Patient informed about authorization requirement"
- "Directed to desk office for authorization code"
- For urgent cases: "Desk office contacted - authorization code: AUTH-XXXXXXXX"

### Best Practices

✅ **DO:**
- Check patient type before starting consultation
- Inform patients upfront about authorization requirements
- Be patient and explain the process clearly
- Call desk office for urgent cases
- Document authorization status in notes

❌ **DON'T:**
- Promise patients that services can be delivered without authorization
- Skip informing patients about the requirement
- Get frustrated - this is a regulatory requirement
- Try to bypass the authorization system

---

## Training for Pharmacy Staff

### Your Role
You must:
- Check authorization status before dispensing
- Validate authorization codes
- Refuse to dispense without valid authorization

### What You'll See

#### When Viewing Prescriptions
For NHIA patients from non-NHIA consultations:
- **Warning Message**: "Authorization required before dispensing"
- **Yellow Badge**: "Authorization Required"
- **Dispense Button**: May be disabled or show error when clicked

### Dispensing Workflow

#### Step 1: Check Authorization Status
Before dispensing ANY prescription:
1. Check the authorization status badge
2. If it shows "Authorization Required":
   - Ask patient for authorization code
   - If patient doesn't have code, direct them to desk office

#### Step 2: Enter Authorization Code (if needed)
1. If prescription requires authorization:
2. Ask patient: "Do you have your authorization code from the desk office?"
3. Patient provides code (format: AUTH-YYYYMMDD-XXXXXX)
4. Enter code in the prescription form
5. System validates the code automatically

#### Step 3: Dispense Medication
1. If authorization is valid OR not required:
2. Proceed with normal dispensing process
3. Dispense medications
4. Update prescription status

### Handling Common Situations

**Situation 1: Patient Has No Code**
- Patient: "I don't have any code"
- You: "You need to visit the desk office first to get an authorization code. It's on the ground floor. Come back with the code and we'll dispense your medications."

**Situation 2: Invalid Code**
- System shows: "Invalid authorization code"
- You: "This code doesn't seem to be valid. Please go back to the desk office to verify the code."

**Situation 3: Code Already Used**
- System shows: "Authorization code is used"
- You: "This code has already been used. If you need more medications, you'll need a new authorization from the desk office."

**Situation 4: Code Expired**
- System shows: "Authorization code is expired"
- You: "This code has expired. Please visit the desk office to get a new authorization code."

### Best Practices

✅ **DO:**
- Always check authorization status first
- Validate codes carefully
- Be polite when refusing to dispense
- Direct patients to desk office clearly
- Document authorization code in dispensing notes

❌ **DON'T:**
- Dispense without valid authorization
- Accept handwritten or verbal codes
- Try to bypass the system
- Get frustrated with patients - they may not understand the process

---

## Training for Laboratory Staff

### Your Role
Same as pharmacy staff, but for lab tests:
- Check authorization before processing tests
- Validate authorization codes
- Refuse to process without valid authorization

### Workflow

#### Before Processing Test
1. Check test request authorization status
2. If "Authorization Required":
   - Request authorization code from patient or doctor
   - Enter code in test request form
   - Validate code
3. If authorized or not required:
   - Proceed with sample collection
   - Process test
   - Enter results

### Common Scenarios

**Scenario 1: Patient Arrives for Test Without Code**
- You: "I see this test requires authorization. Do you have your authorization code from the desk office?"
- If no: "Please visit the desk office first to get your authorization code, then come back for the test."

**Scenario 2: Doctor Orders Urgent Test**
- Doctor: "This is urgent, patient needs test immediately"
- You: "I understand. The patient needs authorization first. Can you contact the desk office for immediate authorization? Or I can call them now."

---

## Training for Radiology Staff

### Your Role
Same as lab staff, but for radiology orders:
- Check authorization before scheduling/performing imaging
- Validate authorization codes
- Refuse to proceed without valid authorization

### Workflow

#### Before Scheduling/Performing Imaging
1. Check radiology order authorization status
2. If "Authorization Required":
   - Request authorization code
   - Enter and validate code
3. If authorized or not required:
   - Schedule imaging
   - Perform imaging
   - Enter results

---

## Common Questions & Answers

### For All Staff

**Q: Why do we need this authorization system?**
A: It ensures NHIA patients receiving services outside NHIA units are properly tracked and billed according to NHIA regulations.

**Q: What if it's an emergency?**
A: For emergencies, provide the service first, then contact desk office immediately for retroactive authorization. Document as emergency in notes.

**Q: Can I use the same authorization code for multiple services?**
A: Yes! If the code is linked to a consultation, it can be used for all services (prescriptions, lab tests, radiology) from that consultation.

**Q: What if the patient lost their authorization code?**
A: Direct them back to the desk office. Desk office can look up the code using the patient's information.

**Q: How long are authorization codes valid?**
A: Usually 30 days, but check the specific code's expiry date in the system.

### For Desk Office Staff

**Q: How do I know how much to set as "Amount Covered"?**
A: This should be based on the expected cost of services. For general consultations, 500-1000 ₦ is typical. For specialist referrals or complex cases, it may be higher.

**Q: Can I cancel an authorization code?**
A: Yes, you can update the code status to 'cancelled' in the admin panel if needed.

**Q: What if I generate a code by mistake?**
A: Cancel it immediately in the system and generate a new one if needed.

### For Doctors

**Q: Do I need to wait for authorization before completing the consultation?**
A: No, complete the consultation normally. The authorization is needed before services (medications, tests) can be delivered.

**Q: What if the patient refuses to go to desk office?**
A: Explain that it's a requirement for NHIA patients. Without authorization, they cannot receive medications or tests. It's not optional.

---

## Training Completion Checklist

### Desk Office Staff
- [ ] Can access authorization dashboard
- [ ] Can generate authorization codes for consultations
- [ ] Can generate authorization codes for referrals
- [ ] Can filter and search authorization codes
- [ ] Understands when authorization is required
- [ ] Knows how to handle urgent cases

### Doctors
- [ ] Can identify when authorization is required
- [ ] Knows how to inform patients
- [ ] Knows how to handle urgent cases
- [ ] Understands the authorization workflow

### Pharmacy Staff
- [ ] Can check authorization status
- [ ] Can enter and validate authorization codes
- [ ] Knows when to refuse dispensing
- [ ] Can direct patients to desk office

### Laboratory Staff
- [ ] Can check authorization status
- [ ] Can enter and validate authorization codes
- [ ] Knows when to refuse test processing
- [ ] Can direct patients to desk office

### Radiology Staff
- [ ] Can check authorization status
- [ ] Can enter and validate authorization codes
- [ ] Knows when to refuse imaging
- [ ] Can direct patients to desk office

---

**Training Version:** 1.0
**Last Updated:** 2025-09-30
**Contact for Questions:** IT Department / System Administrator

