# NHIA Authorization System - Quick Start Guide

## 🎯 What Was Implemented

The NHIA Authorization System ensures that NHIA patients seen in non-NHIA units or referred from NHIA to non-NHIA units must receive desk office authorization before services (medications, lab tests, radiology) can be delivered.

## 🚀 Quick Access URLs

### For Desk Office Staff
- **Main Dashboard**: `/desk-office/authorization-dashboard/`
- **Pending Consultations**: `/desk-office/pending-consultations/`
- **Pending Referrals**: `/desk-office/pending-referrals/`
- **All Authorization Codes**: `/desk-office/authorization-codes/`

### For Doctors
- Consultations and referrals automatically show authorization status
- Warning banners appear when authorization is required

### For Service Delivery Staff (Pharmacy, Lab, Radiology)
- Services are automatically blocked if authorization is required but not provided
- Clear error messages guide staff to obtain authorization

## 📋 How It Works

### Automatic Detection
The system automatically detects when authorization is required:

1. **NHIA Patient in Non-NHIA Room**
   - When a consultation is saved, the system checks if the patient is NHIA
   - If the consulting room is not an NHIA room, authorization is required
   - `requires_authorization` is set to `True` automatically

2. **NHIA Patient Referred to Non-NHIA Unit**
   - When a referral is created from NHIA to non-NHIA unit
   - Authorization is automatically required
   - All services from the referred consultation need authorization

### Service Blocking
Services cannot be delivered without valid authorization:

- **Pharmacy**: Cannot dispense medications
- **Laboratory**: Cannot process test results
- **Radiology**: Cannot schedule or perform imaging

### Authorization Flow

```
NHIA Patient → Non-NHIA Consultation → Authorization Required
                                              ↓
                                    Desk Office Generates Code
                                              ↓
                                    Code Linked to Consultation
                                              ↓
                              Services Can Be Delivered with Code
```

## 🔧 For Desk Office Staff

### Accessing the Dashboard
1. Login to the system
2. Navigate to `/desk-office/authorization-dashboard/`
3. You'll see:
   - Statistics cards showing pending authorizations
   - Pending consultations table
   - Pending referrals table
   - Recent authorization codes

### Generating Authorization Code

#### For Consultation:
1. From dashboard, find the consultation in "Pending Consultations"
2. Click "Authorize" button
3. Fill in the form:
   - **Amount**: Amount covered by this authorization (e.g., 500.00)
   - **Validity Period**: How long the code is valid (7, 14, 30, 60, or 90 days)
   - **Notes**: Any additional information
4. Click "Generate Authorization Code"
5. Code is generated in format: `AUTH-YYYYMMDD-XXXXXX`
6. Provide this code to the patient or service unit

#### For Referral:
1. From dashboard, find the referral in "Pending Referrals"
2. Click "Authorize" button
3. Follow same process as consultation

### Managing Authorization Codes
1. Navigate to `/desk-office/authorization-codes/`
2. Use filters to search:
   - By status (active, used, expired, cancelled)
   - By service type
   - By patient name or ID
3. View complete history of all codes

## 👨‍⚕️ For Doctors

### Creating Consultation
1. Create consultation as usual
2. If NHIA patient in non-NHIA room:
   - Warning banner appears: "This consultation requires desk office authorization"
   - Authorization status badge shows "Authorization Required"
3. Inform patient to visit desk office for authorization

### Creating Referral
1. Create referral as usual
2. If referring NHIA patient to non-NHIA unit:
   - Warning banner appears
   - Authorization status badge shows "Authorization Required"
3. Inform patient to visit desk office

### Viewing Authorization Status
- Consultation detail page shows authorization status
- Green badge = Authorized
- Yellow badge = Authorization Required
- Authorization code is displayed when available

## 💊 For Pharmacy Staff

### Dispensing Medications

#### Without Authorization (Blocked):
1. Navigate to prescription
2. Click "Dispense"
3. **Error**: "Desk office authorization required for NHIA patient from non-NHIA unit."
4. Inform patient to obtain authorization from desk office

#### With Authorization (Allowed):
1. Patient provides authorization code
2. Enter code in prescription form
3. Code is validated automatically
4. Dispensing proceeds normally

## 🔬 For Laboratory Staff

### Processing Test Results

#### Without Authorization (Blocked):
1. Navigate to test request
2. Try to add results
3. **Error**: "Desk office authorization required for NHIA patient from non-NHIA unit."
4. Request authorization code

#### With Authorization (Allowed):
1. Enter authorization code in test request form
2. Code is validated
3. Test processing proceeds normally

## 📸 For Radiology Staff

### Performing Imaging

#### Without Authorization (Blocked):
1. Navigate to radiology order
2. Try to schedule or add results
3. **Error**: "Desk office authorization required for NHIA patient from non-NHIA unit."
4. Request authorization code

#### With Authorization (Allowed):
1. Enter authorization code in radiology order form
2. Code is validated
3. Imaging proceeds normally

## 🎨 Visual Indicators

### Authorization Status Badges
- 🟢 **Green "Authorized"**: Authorization code is valid and linked
- 🟡 **Yellow "Authorization Required"**: Needs desk office authorization
- 🔵 **Blue "Pending"**: Authorization request is pending

### Warning Banners
- Appear at the top of consultation/referral detail pages
- Clearly state why authorization is required
- Provide guidance on next steps

## 🔍 Troubleshooting

### "Authorization required" but patient is not NHIA
**Solution**: Check patient's `patient_type` field. Only NHIA patients require authorization.

### Service still blocked after entering code
**Possible causes**:
- Code is invalid or doesn't exist
- Code has expired
- Code has already been used
- Code is cancelled

**Solution**: Verify code with desk office staff

### Dashboard not showing pending items
**Possible causes**:
- Items are already authorized
- Items don't require authorization
- User doesn't have permission

**Solution**: Check authorization status on the item directly

### Code validation fails
**Possible causes**:
- Typo in code entry
- Code format is incorrect
- Code doesn't exist in system

**Solution**: Double-check code with desk office

## 📊 Reports and Tracking

### Desk Office Dashboard Statistics
- **Total Pending**: All items requiring authorization
- **Consultations**: Pending consultation authorizations
- **Referrals**: Pending referral authorizations
- **Prescriptions**: Pending prescription authorizations
- **Lab Tests**: Pending lab test authorizations
- **Radiology**: Pending radiology authorizations

### Authorization Code List
- Filter by status to see:
  - Active codes (not yet used)
  - Used codes (already consumed)
  - Expired codes (past expiry date)
  - Cancelled codes

## 🔐 Security Features

1. **Unique Codes**: Each authorization code is unique (UUID-based)
2. **Expiry Dates**: Codes automatically expire after set period
3. **One-Time Use**: Codes can only be used once
4. **Audit Trail**: Complete history of code generation and usage
5. **User Tracking**: Records who generated each code

## 📝 Best Practices

### For Desk Office Staff
- Generate codes promptly to avoid service delays
- Set appropriate expiry periods (30 days is standard)
- Add notes to codes for future reference
- Review pending authorizations daily

### For Doctors
- Inform patients about authorization requirements upfront
- Check authorization status before ordering services
- Coordinate with desk office for urgent cases

### For Service Delivery Staff
- Always check authorization status before processing
- Validate authorization codes carefully
- Report any issues to desk office immediately

## 🆘 Support

### Common Questions

**Q: Can one authorization code be used for multiple services?**
A: Yes, if the code is linked to a consultation, it can be used for all services (prescriptions, lab tests, radiology) from that consultation.

**Q: What happens if a code expires?**
A: The code becomes invalid and cannot be used. A new code must be generated.

**Q: Can authorization codes be cancelled?**
A: Yes, desk office staff can update the code status to 'cancelled' in the admin panel.

**Q: How long should codes be valid?**
A: Standard is 30 days, but can be adjusted based on the service type and patient needs.

## 📚 Related Documentation

- **NHIA_AUTHORIZATION_IMPLEMENTATION.md**: Complete technical implementation details
- **NHIA_AUTHORIZATION_TESTING_GUIDE.md**: Comprehensive testing scenarios
- **DESK_OFFICE_SERVICE_AUTHORIZATION.md**: Original desk office authorization documentation

## ✅ System Status

- ✅ All migrations applied
- ✅ All models updated
- ✅ All views updated
- ✅ All templates created
- ✅ Dashboard functional
- ✅ Authorization enforcement active
- 🔄 Ready for testing

## 🎯 Next Steps

1. **Test the system** using NHIA_AUTHORIZATION_TESTING_GUIDE.md
2. **Train staff** on the new workflow
3. **Monitor** the dashboard for pending authorizations
4. **Provide feedback** on any issues or improvements

---

**Last Updated**: 2025-09-30
**Version**: 1.0
**Status**: Implementation Complete - Ready for Testing

