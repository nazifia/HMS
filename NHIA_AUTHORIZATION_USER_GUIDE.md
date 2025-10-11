# NHIA Authorization System - User Guide

## Welcome to the NHIA Authorization System

This guide will help you understand and use the NHIA Authorization System in your daily work.

---

## What is the NHIA Authorization System?

The NHIA Authorization System ensures that NHIA patients who receive services outside of NHIA units must first obtain authorization from the desk office. This helps maintain proper billing, tracking, and compliance with NHIA regulations.

### Key Concept
**NHIA patients seen in non-NHIA departments need authorization before receiving services.**

---

## Visual Guide: Understanding the UI

### 1. Authorization Status Badges

You'll see these badges throughout the system:

#### 🟡 Authorization Required
```
┌─────────────────────────────┐
│ ⚠️ Authorization Required   │
└─────────────────────────────┘
```
**What it means:** This service needs desk office authorization before it can be delivered.

**What to do:** 
- If you're a doctor: Inform the patient to visit desk office
- If you're service staff: Ask patient for authorization code
- If you're desk office: Generate an authorization code

---

#### 🟢 Authorized
```
┌─────────────────────────────────────────┐
│ ✅ Authorized                           │
│                                         │
│ Authorization Code: AUTH-20250930-A1B2 │
│ Service Type: Consultation              │
│ Expiry Date: Oct 30, 2025              │
└─────────────────────────────────────────┘
```
**What it means:** Authorization has been granted. Services can be delivered.

**What to do:** Proceed with service delivery normally.

---

#### ⚪ Not Required
```
┌─────────────────────────────┐
│ ℹ️ Authorization Not Required│
└─────────────────────────────┘
```
**What it means:** This service doesn't need authorization (regular patient or NHIA patient in NHIA room).

**What to do:** Proceed with service delivery normally.

---

### 2. Warning Banners

When authorization is required, you'll see a prominent warning banner:

```
╔═══════════════════════════════════════════════════════════╗
║ ⚠️  This consultation requires desk office authorization  ║
║                                                           ║
║ Why is this required?                                     ║
║ • This is an NHIA patient                                ║
║ • Seen in a non-NHIA consulting room (General Medicine)  ║
║ • All services require desk office authorization         ║
║                                                           ║
║ Action Required:                                          ║
║ Contact the desk office to generate an authorization code║
╚═══════════════════════════════════════════════════════════╝
```

**What to do:** Follow the instructions in the banner.

---

### 3. Authorization Code Input Field

When creating services (prescriptions, lab tests, radiology), you may see:

```
┌─────────────────────────────────────────────────────────┐
│ Authorization Code (if required)                        │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Enter authorization code (e.g., AUTH-20250930-ABC123)│ │
│ └─────────────────────────────────────────────────────┘ │
│ ℹ️ Enter the authorization code if this prescription    │
│   requires NHIA authorization                           │
└─────────────────────────────────────────────────────────┘
```

**What to do:** 
- If patient has authorization code: Enter it here
- If patient doesn't have code: Leave blank and inform patient to visit desk office

---

## User Guides by Role

## For Desk Office Staff

### Your Dashboard

When you login, go to: **Desk Office → Authorization Dashboard**

You'll see:

#### Statistics Cards
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Total Pending│ │Consultations │ │  Referrals   │ │   Services   │
│      5       │ │      2       │ │      1       │ │      2       │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

**What it shows:** Number of items waiting for authorization

---

#### Pending Consultations Table
```
┌────────────────────────────────────────────────────────────────┐
│ Patient        │ Doctor      │ Room    │ Date       │ Actions │
├────────────────────────────────────────────────────────────────┤
│ John Doe       │ Dr. Smith   │ GEN-201 │ Sep 30     │[Authorize]│
│ Jane Smith     │ Dr. Jones   │ CARD-301│ Sep 30     │[Authorize]│
└────────────────────────────────────────────────────────────────┘
```

**What to do:** Click "Authorize" button to generate authorization code

---

### Generating Authorization Codes

**Step 1:** Click "Authorize" button

**Step 2:** Review the details
- Patient information
- Doctor name
- Consulting room
- Why authorization is required

**Step 3:** Fill in the form
```
┌─────────────────────────────────────────┐
│ Amount Covered: [500.00        ] ₦   │
│                                         │
│ Validity Period: [30 Days      ▼]      │
│                                         │
│ Notes:                                  │
│ ┌─────────────────────────────────────┐ │
│ │ Test authorization for consultation │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [Cancel] [Generate Authorization Code] │
└─────────────────────────────────────────┘
```

**Step 4:** Click "Generate Authorization Code"

**Step 5:** Copy the code and provide it to the patient
```
╔═══════════════════════════════════════════════════╗
║ ✅ Success!                                       ║
║                                                   ║
║ Authorization code generated successfully:        ║
║                                                   ║
║     AUTH-20250930-A1B2C3                         ║
║                                                   ║
║ Please provide this code to the patient.          ║
╚═══════════════════════════════════════════════════╝
```

---

### Tips for Desk Office Staff

✅ **DO:**
- Process requests promptly (within 1 hour)
- Set appropriate validity periods (30 days is standard)
- Add clear notes for future reference
- Verify patient is NHIA before generating code
- Provide code to patient clearly (write it down or send via SMS)

❌ **DON'T:**
- Generate codes for non-NHIA patients
- Set very short expiry periods without reason
- Share codes between different patients
- Forget to inform the patient about the code

---

## For Doctors

### What You'll See

When you create a consultation for an NHIA patient in a non-NHIA room, you'll see:

1. **Warning Banner** (yellow) at the top of the consultation detail page
2. **Authorization Required Badge** (yellow) in the consultation information

### What You Should Do

**Step 1:** Complete the consultation normally

**Step 2:** Inform the patient
- "You'll need to visit the desk office for authorization before getting your medications/tests"
- "The desk office is on the ground floor"
- "They'll give you a code - keep it safe"

**Step 3:** For urgent cases
- Call desk office directly: Extension XXXX
- Provide patient details
- Request immediate authorization
- Desk office will provide code to you or service unit

**Step 4:** Document in notes
- "Patient informed about authorization requirement"
- "Directed to desk office"
- For urgent: "Desk office contacted - code: AUTH-XXXXXXXX"

---

### Tips for Doctors

✅ **DO:**
- Check patient type before consultation
- Inform patients upfront about authorization
- Be patient and explain the process
- Call desk office for urgent cases
- Document everything

❌ **DON'T:**
- Promise services without authorization
- Skip informing patients
- Get frustrated - it's a regulatory requirement
- Try to bypass the system

---

## For Pharmacy Staff

### What You'll See

When viewing a prescription that requires authorization:

1. **Warning Banner** at the top
2. **Authorization Required Badge** in prescription details
3. **Dispense button** may show error when clicked

### What You Should Do

**Step 1:** Check authorization status
- Look for the status badge
- If yellow "Authorization Required": Ask patient for code

**Step 2:** Ask patient for code
- "Do you have your authorization code from the desk office?"
- If yes: Proceed to Step 3
- If no: Direct to desk office

**Step 3:** Verify code (if needed)
- Code format: AUTH-YYYYMMDD-XXXXXX
- System validates automatically

**Step 4:** Dispense medication
- If authorized: Proceed normally
- If not authorized: Cannot dispense

---

### Common Situations

**Situation 1: Patient has no code**
```
You: "I see this prescription requires authorization. 
      Do you have your authorization code from the desk office?"
Patient: "No, I don't have any code."
You: "You'll need to visit the desk office first to get an 
      authorization code. It's on the ground floor. Come back 
      with the code and we'll dispense your medications."
```

**Situation 2: Invalid code**
```
System: "❌ Invalid authorization code"
You: "This code doesn't seem to be valid. Please go back to 
      the desk office to verify the code."
```

**Situation 3: Code already used**
```
System: "❌ Authorization code has already been used"
You: "This code has already been used. If you need more 
      medications, you'll need a new authorization from 
      the desk office."
```

---

### Tips for Pharmacy Staff

✅ **DO:**
- Always check authorization status first
- Be polite when refusing to dispense
- Direct patients to desk office clearly
- Document authorization code in notes

❌ **DON'T:**
- Dispense without valid authorization
- Accept handwritten or verbal codes
- Try to bypass the system
- Get frustrated with patients

---

## For Laboratory Staff

### Process

Same as pharmacy staff, but for lab tests:

1. Check test request authorization status
2. If required: Ask patient for authorization code
3. Verify code
4. Process test if authorized

### Tips

- For urgent tests: Contact desk office directly
- Always verify code before sample collection
- Document code in test request notes

---

## For Radiology Staff

### Process

Same as pharmacy and lab staff, but for radiology orders:

1. Check order authorization status
2. If required: Ask patient for authorization code
3. Verify code
4. Schedule/perform imaging if authorized

### Tips

- For urgent imaging: Contact desk office directly
- Verify code before scheduling
- Document code in order notes

---

## Quick Reference

### Authorization Code Format
```
AUTH-YYYYMMDD-XXXXXX

Example: AUTH-20250930-A1B2C3
```

### When is Authorization Required?

✅ **YES - Authorization Required:**
- NHIA patient in non-NHIA consulting room
- NHIA patient referred from NHIA to non-NHIA unit

❌ **NO - Authorization NOT Required:**
- Regular (non-NHIA) patient - anywhere
- NHIA patient in NHIA consulting room
- NHIA patient referred within NHIA units

### Desk Office Contact

- **Location:** Ground Floor
- **Phone:** Extension XXXX
- **Hours:** 8:00 AM - 5:00 PM (Monday - Friday)

---

## Frequently Asked Questions

**Q: What if it's an emergency?**
A: For emergencies, provide the service first, then contact desk office immediately for retroactive authorization. Document as emergency.

**Q: Can I use the same code for multiple services?**
A: Yes! If the code is linked to a consultation, it covers all services (prescriptions, lab tests, radiology) from that consultation.

**Q: What if the patient lost their code?**
A: Direct them back to desk office. Desk office can look up the code using patient information.

**Q: How long are codes valid?**
A: Usually 30 days, but check the specific code's expiry date.

**Q: What if the code is expired?**
A: Patient needs to return to desk office for a new code. Old codes cannot be reactivated.

---

## Need Help?

If you have questions or encounter issues:

1. **Check this guide** - Most common questions are answered here
2. **Contact IT Support** - Extension XXXX or it-support@hospital.com
3. **Contact Desk Office** - For authorization-specific questions

---

**User Guide Version:** 1.0
**Last Updated:** 2025-09-30
**For:** All Hospital Staff

