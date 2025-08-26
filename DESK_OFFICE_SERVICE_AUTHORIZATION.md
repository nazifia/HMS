# Desk Office Service Authorization System

## Overview
This document describes the enhanced desk office functionality for generating and managing service authorization codes for NHIA patients. The system allows desk office staff to search for NHIA patients, generate authorization codes for specific services, and enables service delivery units to accept these codes for payment.

## Features

### 1. NHIA Patient Search
- Search NHIA patients by name or patient ID
- Display search results in a table format
- Select a patient to generate an authorization code

### 2. Service Authorization Code Generation
- Generate unique UUID-based authorization codes
- Specify service type (Laboratory, Radiology, Theatre, etc.)
- Add detailed service description
- Specify department where service will be delivered
- Track code status (pending, used, expired)

### 3. Service Delivery Unit Verification
- Verify authorization codes
- View patient and service details
- Accept codes for payment
- Mark codes as "used" when services are delivered

## Implementation Details

### Models
The `AuthorizationCode` model has been enhanced with:
- `service_type`: Categorizes the type of service
- `service_description`: Detailed description of the requested service
- `is_valid()`: Method to check if a code is still valid
- `mark_as_used()`: Method to mark a code as used

### Forms
- `PatientSearchForm`: For searching NHIA patients
- `AuthorizationCodeForm`: For generating authorization codes with service details

### Views
- `generate_authorization_code`: Handles patient search and code generation
- `verify_authorization_code`: Handles code verification
- `search_nhia_patients_ajax`: AJAX endpoint for patient search (future enhancement)

### Templates
- `generate_authorization_code.html`: Main interface for generating codes
- `verify_authorization_code.html`: Interface for verifying codes
- `authorization_form_fields.html`: Partial template for form fields

## Service Types Supported
1. Laboratory
2. Radiology
3. Theatre/Surgery
4. Inpatient
5. Dental
6. Ophthalmic
7. ENT
8. Oncology
9. Gynae Emergency
10. Labor & Delivery
11. SCBU
12. ICU
13. General Consultation
14. Other Services

## Workflow

### Generating Authorization Codes
1. Navigate to `/desk-office/generate-code/`
2. Search for NHIA patient by name or ID
3. Select the patient from search results
4. Fill in service details:
   - Service type
   - Service description
   - Department
5. Generate the authorization code
6. Provide the code to the patient

### Verifying Authorization Codes
1. Navigate to `/desk-office/verify-code/`
2. Enter the authorization code
3. View patient and service details
4. If valid, accept the code for payment
5. Mark the code as "used"

## Security Considerations
- Only NHIA patients can have authorization codes generated
- Codes can only be used once
- Codes have a "pending" status until used
- Service delivery units must verify codes before accepting them

## Future Enhancements
- AJAX-based patient search with autocomplete
- Integration with specific service modules
- Reporting on authorization code usage
- Expiry date management for codes