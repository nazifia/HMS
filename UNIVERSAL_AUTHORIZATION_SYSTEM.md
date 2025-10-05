# Universal Authorization System - Complete Implementation

## Overview

A comprehensive, centralized authorization request processing system that works across **ALL 16 medical modules** in the Hospital Management System. This system allows desk office staff to manage NHIA authorization requests from any module in one unified interface.

## Key Features

✅ **Universal Coverage** - Supports 16 different model types across all medical modules  
✅ **Centralized Dashboard** - View all pending requests in one place  
✅ **Reusable Widget** - Drop-in authorization component for any module  
✅ **Flexible Authorization** - Request or generate codes from anywhere  
✅ **AJAX Status Checking** - Real-time authorization status updates  
✅ **Bulk Operations** - Generate multiple authorization codes at once  
✅ **Authorization History** - Track all codes for a patient/service  

## Supported Models

The system supports authorization for the following 16 model types:

### Core Medical Services
1. **consultation** - Consultations (consultations.Consultation)
2. **referral** - Referrals (consultations.Referral)
3. **prescription** - Prescriptions (pharmacy.Prescription)
4. **test_request** - Laboratory Tests (laboratory.TestRequest)
5. **radiology_order** - Radiology Orders (radiology.RadiologyOrder)
6. **surgery** - Surgeries (theatre.Surgery)

### Specialty Medical Modules
7. **dental_record** - Dental Records (dental.DentalRecord)
8. **ophthalmic_record** - Ophthalmic Records (ophthalmic.OphthalmicRecord)
9. **ent_record** - ENT Records (ent.EntRecord)
10. **oncology_record** - Oncology Records (oncology.OncologyRecord)
11. **scbu_record** - SCBU Records (scbu.ScbuRecord)
12. **anc_record** - ANC Records (anc.AncRecord)
13. **labor_record** - Labor Records (labor.LaborRecord)
14. **icu_record** - ICU Records (icu.IcuRecord)
15. **family_planning_record** - Family Planning Records (family_planning.Family_planningRecord)
16. **gynae_emergency_record** - Gynae Emergency Records (gynae_emergency.Gynae_emergencyRecord)

## Components

### 1. Authorization Utilities (`core/authorization_utils.py`)

Central utility module providing:

- **`AUTHORIZATION_SUPPORTED_MODELS`** - Registry of all supported models
- **`get_model_info(model_type)`** - Get model configuration
- **`get_model_class(model_type)`** - Get Django model class
- **`get_object_for_authorization(model_type, object_id)`** - Retrieve object
- **`check_if_requires_authorization(obj)`** - Check if auth needed
- **`get_authorization_status(obj)`** - Get current auth status
- **`create_authorization_request(obj, requested_by, notes)`** - Request auth
- **`generate_authorization_for_object(obj, generated_by, amount, expiry_days, notes)`** - Generate code
- **`get_all_pending_authorizations()`** - Get all pending requests

### 2. Authorization Views (`core/authorization_views.py`)

Universal views handling authorization across all modules:

- **`request_authorization(request, model_type, object_id)`** - Request authorization
- **`generate_authorization(request, model_type, object_id)`** - Generate auth code
- **`universal_authorization_dashboard(request)`** - View all pending requests
- **`check_authorization_status_ajax(request)`** - AJAX status checker
- **`bulk_generate_authorization(request)`** - Bulk code generation
- **`authorization_history(request, model_type, object_id)`** - View history

### 3. Authorization Widget (`templates/includes/authorization_request_widget.html`)

Reusable template component that can be included in any module's detail page.

**Features:**
- Shows authorization status with color-coded alerts
- Displays authorization code details if available
- Provides "Request Authorization" button with modal form
- Supports both user request and desk office generate modes
- Automatically detects NHIA patients

**Usage:**
```django
{% include 'includes/authorization_request_widget.html' with object=record model_type='dental_record' %}
```

**Optional Parameters:**
- `show_request_button` - Show/hide request button (default: True)
- `show_generate_button` - Show/hide generate button for desk office (default: False)

### 4. Universal Dashboard (`templates/core/universal_authorization_dashboard.html`)

Centralized dashboard showing all pending authorization requests.

**Features:**
- Statistics cards (pending, generated today, active, expired)
- Accordion view grouped by module type
- Pending requests table for each module
- Recent authorization codes list
- Quick generate buttons

**Access:** `/core/authorization/dashboard/`

### 5. Generate Authorization Template (`templates/core/generate_authorization.html`)

Form for desk office staff to generate authorization codes.

**Features:**
- Object information display
- Amount covered input
- Validity period selector (7 days to 1 year)
- Notes/remarks field
- Help guidelines
- Patient authorization history link

## URL Patterns

Added to `core/urls.py`:

```python
# Universal Authorization URLs
path('authorization/request/<str:model_type>/<int:object_id>/', 
     authorization_views.request_authorization, name='request_authorization'),
path('authorization/generate/<str:model_type>/<int:object_id>/', 
     authorization_views.generate_authorization, name='generate_authorization'),
path('authorization/dashboard/', 
     authorization_views.universal_authorization_dashboard, name='universal_authorization_dashboard'),
path('authorization/check-status/', 
     authorization_views.check_authorization_status_ajax, name='check_authorization_status'),
path('authorization/bulk-generate/', 
     authorization_views.bulk_generate_authorization, name='bulk_generate_authorization'),
path('authorization/history/<str:model_type>/<int:object_id>/', 
     authorization_views.authorization_history, name='authorization_history'),
```

## Integration

### Sidebar Integration

Added to `templates/includes/sidebar.html` under Desk Office section:

```django
<a class="collapse-item" href="{% url 'core:universal_authorization_dashboard' %}">
    <i class="fas fa-globe me-1"></i> Universal Dashboard <span class="badge badge-success">New</span>
</a>
```

### Desk Office Dashboard Integration

Enhanced `desk_office/templates/desk_office/authorization_dashboard.html`:

- Added "Universal Dashboard" button in header
- Added info alert promoting the new feature
- Maintains backward compatibility with existing dashboard

## Usage Examples

### 1. Add Authorization Widget to Module Detail Page

In any module's detail template (e.g., `dental/dental_record_detail.html`):

```django
{% extends 'base.html' %}

{% block content %}
<div class="container-fluid">
    <!-- Record details here -->
    
    <!-- Authorization Widget -->
    {% include 'includes/authorization_request_widget.html' with object=record model_type='dental_record' %}
</div>
{% endblock %}
```

### 2. Request Authorization from Code

```python
from core.authorization_utils import create_authorization_request

# In a view
record = get_object_or_404(DentalRecord, id=record_id)
success = create_authorization_request(record, request.user, "Patient needs urgent dental work")
```

### 3. Generate Authorization Code

```python
from core.authorization_utils import generate_authorization_for_object

# In a view (typically desk office)
record = get_object_or_404(DentalRecord, id=record_id)
auth_code, error = generate_authorization_for_object(
    record, 
    request.user, 
    amount=500.00, 
    expiry_days=30, 
    notes="Approved for dental procedure"
)
```

### 4. Check Authorization Status via AJAX

```javascript
$.ajax({
    url: '/core/authorization/check-status/',
    data: {
        model_type: 'dental_record',
        object_id: 123
    },
    success: function(data) {
        console.log('Status:', data.status);
        console.log('Requires auth:', data.requires_authorization);
    }
});
```

## Workflow

### For Medical Staff (Doctors, Nurses, etc.)

1. View patient record in any medical module
2. See authorization widget showing status
3. If NHIA patient needs authorization, click "Request Authorization"
4. Fill in reason and estimated amount
5. Submit request
6. Desk office receives notification

### For Desk Office Staff

1. Access Universal Authorization Dashboard
2. View all pending requests across all modules
3. Click "Generate Code" for a request
4. Enter amount covered and validity period
5. Add notes if needed
6. Generate authorization code
7. Code is automatically linked to the record

### For Patients

1. Authorization code is generated
2. Medical staff can proceed with service
3. Code is validated during service delivery
4. Code is marked as "used" after service completion

## Benefits

1. **Centralized Management** - All authorization requests in one place
2. **Consistency** - Same authorization process across all modules
3. **Efficiency** - Bulk operations and quick access
4. **Transparency** - Clear status tracking and history
5. **Flexibility** - Works with any module without code changes
6. **Scalability** - Easy to add new modules to the system

## Technical Notes

### Model Requirements

For a model to work with the authorization system, it should have:

1. `patient` ForeignKey to Patient model
2. `authorization_code` field (ForeignKey to AuthorizationCode or CharField)
3. Optional: `authorization_status` CharField
4. Optional: `requires_authorization` BooleanField

### Authorization Status Values

- `not_required` - Patient is not NHIA or service doesn't need auth
- `required` - Authorization needed but not requested yet
- `pending` - Authorization request submitted, awaiting desk office
- `authorized` - Authorization code generated and valid
- `rejected` - Authorization request rejected
- `expired` - Authorization code has expired

### Service Type Mapping

Each model type maps to a service type for authorization codes:

- `general` - General services (consultations, referrals, ANC, etc.)
- `laboratory` - Lab tests
- `radiology` - Radiology orders
- `theatre` - Surgeries
- `dental` - Dental services
- `opthalmic` - Eye care
- `ent` - ENT services
- `oncology` - Cancer treatment
- `inpatient` - Inpatient services (SCBU, ICU, Labor)

## Future Enhancements

Potential improvements:

1. Email/SMS notifications for authorization requests
2. Mobile app integration
3. Authorization approval workflow with multiple levels
4. Integration with NHIA national database
5. Automated authorization for certain service types
6. Analytics dashboard for authorization trends
7. Patient portal to view authorization status

## Testing

To test the system:

1. Create an NHIA patient
2. Create a record in any medical module for that patient
3. View the record detail page
4. Verify authorization widget appears
5. Request authorization
6. Access Universal Authorization Dashboard
7. Generate authorization code
8. Verify code appears in record detail

## Troubleshooting

**Widget not showing:**
- Verify patient is NHIA type
- Check that model_type matches registry
- Ensure object has patient attribute

**Cannot generate code:**
- Verify user has desk office permissions
- Check that object exists
- Ensure patient is NHIA type

**Pending requests not showing:**
- Check authorization_status field values
- Verify model is in AUTHORIZATION_SUPPORTED_MODELS
- Check database for pending records

## Conclusion

The Universal Authorization System provides a comprehensive, scalable solution for managing NHIA authorization requests across all medical modules in the HMS. It centralizes authorization management while maintaining flexibility and ease of use.

