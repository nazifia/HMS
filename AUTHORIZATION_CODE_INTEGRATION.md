# Hospital Management System - Authorization Code Integration

## Overview

This document describes the integration of authorization code support across all medical modules in the Hospital Management System (HMS). This enhancement allows desk office staff to generate authorization codes that can be used by various departments to provide services to patients.

## Modules Updated

The following medical modules have been updated to support authorization codes:

1. Ophthalmic
2. ENT (Ear, Nose, and Throat)
3. Oncology
4. SCBU (Special Care Baby Unit)
5. ANC (Antenatal Care)
6. Labor
7. ICU (Intensive Care Unit)
8. Family Planning
9. Gynae Emergency

## Changes Made

### 1. Database Schema Updates

Each module's database model has been updated to include an `authorization_code` field:

```python
authorization_code = models.CharField(max_length=50, blank=True, null=True, help_text="Authorization code from desk office")
```

### 2. Form Updates

All forms have been updated to include the authorization code field:

- Added `authorization_code` to the form fields
- Added appropriate widget for the authorization code input
- Added help text to guide users

### 3. View Updates

All views have been enhanced to handle authorization codes:

- Import of `AuthorizationCode` model from `nhia.models`
- Validation of authorization codes when provided
- Marking of authorization codes as "used" when services are provided
- Error handling for invalid or expired authorization codes

### 4. Template Updates

All templates have been updated to:

- Display the authorization code input field in forms
- Show authorization code information in record details
- Provide user guidance on authorization code usage

### 5. Migration Files

Migration files have been created for each module to add the authorization_code field to the database tables.

## Implementation Details

### Authorization Code Validation

When an authorization code is provided:

1. The system checks if the code exists in the database
2. Validates that the code is still active (not expired or used)
3. Confirms that the code is valid for the specific service type
4. Marks the code as "used" when the service is provided

### Error Handling

The system provides clear error messages for:

- Invalid authorization codes
- Expired authorization codes
- Authorization codes not valid for the specific service type

### User Interface

The authorization code field is optional and clearly marked as such. Users are provided with guidance on when and how to use authorization codes.

## Service Types

The authorization code system supports the following service types:

- laboratory
- radiology
- theatre
- inpatient
- dental
- ophthalmic
- ent
- oncology
- general (for any service)

## Benefits

1. **Streamlined Workflow**: Desk office can pre-authorize services, reducing delays at service points
2. **Better Tracking**: All authorization codes are tracked and marked as used when services are provided
3. **Enhanced Security**: Authorization codes provide an additional layer of validation
4. **Improved Reporting**: Better tracking of authorized services vs. direct payments

## Usage Instructions

### For Desk Office Staff

1. Generate authorization codes through the desk office interface
2. Specify the patient, service type, and any amount limitations
3. Provide the authorization code to the patient or relevant department

### For Medical Staff

1. When creating or updating a medical record, enter the authorization code if provided
2. The system will automatically validate the code
3. If valid, the code will be marked as used and the record will be created/updated
4. If invalid, appropriate error messages will be displayed

## Future Enhancements

Potential future enhancements include:

1. Integration with billing system for automatic invoice generation
2. SMS notifications when authorization codes are generated
3. Barcode/QR code support for easier code entry
4. Bulk authorization code generation for events or campaigns

## Testing

All modules have been tested to ensure:

1. Authorization codes are properly validated
2. Valid codes are accepted and marked as used
3. Invalid codes are rejected with appropriate error messages
4. Existing functionality is preserved when no authorization code is provided

## Support

For issues or questions regarding the authorization code system, please contact the development team.