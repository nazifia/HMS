# Manual Authorization Code Input Feature

## Overview

The HMS authorization system now supports **both auto-generated and manually input authorization codes**. Desk office staff can choose to either let the system generate a unique code automatically or input their own custom authorization code.

## Feature Highlights

### ✅ Dual Code Generation Options

1. **Auto-Generate (Default)**
   - System automatically creates unique codes
   - Format: `AUTH-YYYYMMDD-XXXXXX` (e.g., AUTH-20251005-ABC123)
   - Guaranteed uniqueness
   - No user input required

2. **Manual Input (New)**
   - Desk office staff can enter custom codes
   - Flexible format (letters, numbers, hyphens)
   - Automatic uppercase conversion
   - Uniqueness validation
   - Examples: `NHIA-2025-001`, `CUSTOM-CODE-123`, `REF-2025-OCT-001`

### ✅ Universal Acceptance

Both auto-generated and manually input codes are:
- Stored in the same database table
- Linked to records identically
- Validated the same way
- Accepted at all requesting units/departments/specialties
- Tracked in authorization history

## Where Manual Codes Can Be Created

### 1. Universal Authorization Dashboard
**URL:** `/core/authorization/generate/<model_type>/<object_id>/`

**Supports:**
- All 16 model types (consultations, referrals, prescriptions, lab tests, radiology, surgery, and 10 medical specialty modules)
- Radio button selection between auto and manual
- Real-time validation
- Form data persistence on errors

### 2. Desk Office Authorization Dashboard
**URL:** `/desk-office/authorization-dashboard/`

**Supports:**
- Consultations requiring authorization
- Referrals requiring authorization
- Same dual-option interface
- Integrated with existing workflow

## User Interface

### Code Type Selection

```
Authorization Code Type

○ Auto-Generate
  System generates unique code
  
○ Manual Input
  Enter custom code
```

### Manual Code Input Field

When "Manual Input" is selected:
- Input field appears with slide-down animation
- Placeholder shows example formats
- Auto-converts to uppercase as you type
- Validates format (alphanumeric and hyphens only)
- Checks for uniqueness before submission

## Validation Rules

### Format Validation

**Allowed Characters:**
- Uppercase letters (A-Z)
- Numbers (0-9)
- Hyphens (-)

**Restrictions:**
- Minimum length: 3 characters
- No spaces allowed
- No special characters except hyphens
- Automatically converted to uppercase

**Valid Examples:**
- `NHIA-2025-001`
- `CUSTOM-CODE-123`
- `REF-OCT-2025-A1`
- `AUTH123`
- `CODE-A-B-C-1-2-3`

**Invalid Examples:**
- `ab` (too short)
- `code with spaces` (contains spaces)
- `code@123` (special character)
- `code_123` (underscore not allowed)

### Uniqueness Validation

- System checks if code already exists in database
- If duplicate found, error message displayed
- User can enter a different code
- Form data preserved for correction

## Technical Implementation

### Backend Changes

#### 1. `core/authorization_utils.py`

Updated `generate_authorization_for_object()` function:

```python
def generate_authorization_for_object(obj, generated_by, amount=0.00, 
                                     expiry_days=30, notes='', manual_code=None):
    """
    Generate authorization code for an object
    Supports both auto-generated and manually input codes
    
    Args:
        manual_code: Optional manual code (if None, auto-generates)
    
    Returns:
        (auth_code, error) tuple
    """
```

**Key Features:**
- Accepts optional `manual_code` parameter
- Validates manual code format and uniqueness
- Marks code source in notes ("Manual-generated" or "System-generated")
- Returns error message if validation fails

#### 2. `core/authorization_views.py`

Updated `generate_authorization()` view:

```python
if request.method == 'POST':
    code_type = request.POST.get('code_type', 'auto')
    manual_code = request.POST.get('manual_code', '').strip().upper()
    
    if code_type == 'manual':
        # Validate and create with manual code
        if not manual_code:
            messages.error(request, 'Please enter a manual authorization code.')
            # Return form with data preserved
        
        if AuthorizationCode.objects.filter(code=manual_code).exists():
            messages.error(request, f'Code "{manual_code}" already exists.')
            # Return form with data preserved
```

**Key Features:**
- Handles both auto and manual code types
- Validates manual codes before creation
- Preserves form data on errors
- Shows appropriate error messages

#### 3. `desk_office/authorization_dashboard_views.py`

Updated `authorize_consultation()` and `authorize_referral()` views with same logic.

### Frontend Changes

#### 1. Form Templates

**Files Updated:**
- `templates/core/generate_authorization.html`
- `desk_office/templates/desk_office/authorize_consultation.html`
- `desk_office/templates/desk_office/authorize_referral.html`

**New Elements:**
```html
<!-- Code Type Selection -->
<div class="mb-3">
    <label class="form-label">Authorization Code Type</label>
    <div class="form-check">
        <input type="radio" name="code_type" id="codeTypeAuto" value="auto" checked>
        <label for="codeTypeAuto">
            <i class="fas fa-magic text-primary"></i> Auto-Generate
        </label>
    </div>
    <div class="form-check mt-2">
        <input type="radio" name="code_type" id="codeTypeManual" value="manual">
        <label for="codeTypeManual">
            <i class="fas fa-keyboard text-success"></i> Manual Input
        </label>
    </div>
</div>

<!-- Manual Code Input (Hidden by default) -->
<div class="mb-3" id="manualCodeGroup" style="display: none;">
    <label for="manual_code">Manual Authorization Code</label>
    <input type="text" class="form-control text-uppercase" 
           id="manual_code" name="manual_code" 
           placeholder="e.g., NHIA-2025-001">
</div>
```

#### 2. JavaScript Functionality

**Features:**
- Toggle manual code input visibility
- Auto-uppercase conversion
- Form validation
- Preserve selection on form resubmission

```javascript
$(document).ready(function() {
    // Toggle manual code input
    $('input[name="code_type"]').change(function() {
        if ($(this).val() === 'manual') {
            $('#manualCodeGroup').slideDown();
            $('#manual_code').prop('required', true);
        } else {
            $('#manualCodeGroup').slideUp();
            $('#manual_code').prop('required', false);
        }
    });
    
    // Auto-uppercase manual code
    $('#manual_code').on('input', function() {
        this.value = this.value.toUpperCase();
    });
});
```

## Usage Examples

### Example 1: Auto-Generate Code

1. Navigate to authorization generation page
2. Select "Auto-Generate" (default)
3. Enter amount, validity period, and notes
4. Click "Generate Authorization Code"
5. System creates code like `AUTH-20251005-ABC123`

### Example 2: Manual Code Input

1. Navigate to authorization generation page
2. Select "Manual Input"
3. Manual code field appears
4. Enter custom code (e.g., `NHIA-2025-001`)
5. Code automatically converts to uppercase
6. Enter amount, validity period, and notes
7. Click "Generate Authorization Code"
8. System validates uniqueness and creates code

### Example 3: Duplicate Code Error

1. Select "Manual Input"
2. Enter code that already exists (e.g., `NHIA-2025-001`)
3. Click "Generate Authorization Code"
4. Error message: "Authorization code 'NHIA-2025-001' already exists. Please use a different code."
5. Form data preserved (amount, validity, notes)
6. Enter different code and resubmit

## Benefits

### For Desk Office Staff

1. **Flexibility** - Choose between auto and manual codes
2. **Custom Naming** - Use organizational naming conventions
3. **Integration** - Match external system codes
4. **Control** - Full control over code format

### For Medical Staff

1. **Transparency** - No difference in how codes work
2. **Acceptance** - Both types accepted everywhere
3. **Tracking** - All codes tracked in authorization history

### For System

1. **Consistency** - Both types stored identically
2. **Validation** - Same validation for all codes
3. **Audit Trail** - Code source tracked in notes
4. **Flexibility** - Easy to extend or modify

## Code Source Tracking

All authorization codes include source information in their notes:

**Auto-Generated:**
```
System-generated for Consultation #123 in General OPD. Patient requires urgent care.
```

**Manual Input:**
```
Manual-generated for Consultation #123 in General OPD. Patient requires urgent care.
```

This helps with:
- Audit trails
- Troubleshooting
- Reporting
- Analytics

## Best Practices

### When to Use Auto-Generate

- Standard consultations
- Quick authorization needs
- No specific code format required
- High volume processing

### When to Use Manual Input

- Integration with external systems (e.g., NHIA national database)
- Organizational naming conventions
- Sequential numbering requirements
- Special tracking needs
- Cross-referencing with paper records

### Recommended Manual Code Formats

**By Service Type:**
- Consultations: `CONS-YYYY-NNN` (e.g., `CONS-2025-001`)
- Referrals: `REF-YYYY-NNN` (e.g., `REF-2025-001`)
- Lab Tests: `LAB-YYYY-NNN` (e.g., `LAB-2025-001`)
- Radiology: `RAD-YYYY-NNN` (e.g., `RAD-2025-001`)
- Surgery: `SURG-YYYY-NNN` (e.g., `SURG-2025-001`)

**By Month:**
- `NHIA-2025-OCT-001`
- `NHIA-2025-OCT-002`

**By Department:**
- `OPD-2025-001`
- `DENTAL-2025-001`
- `OPHTHALMIC-2025-001`

## Error Handling

### Empty Manual Code

**Error:** "Please enter a manual authorization code."

**Solution:** Enter a code in the manual code field

### Duplicate Code

**Error:** "Authorization code 'XXX' already exists. Please use a different code."

**Solution:** Enter a unique code

### Invalid Format

**Error:** "Authorization code can only contain uppercase letters, numbers, and hyphens."

**Solution:** Remove invalid characters (spaces, special characters, etc.)

### Too Short

**Error:** "Authorization code must be at least 3 characters long."

**Solution:** Enter a longer code

## Database Schema

No changes to database schema required. Both code types use the same `AuthorizationCode` model:

```python
class AuthorizationCode(models.Model):
    code = models.CharField(max_length=50, unique=True)  # Stores both types
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField()
    status = models.CharField(max_length=20)
    notes = models.TextField()  # Includes code source
    generated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
```

## Testing Checklist

- [ ] Auto-generate code works
- [ ] Manual code input works
- [ ] Uppercase conversion works
- [ ] Uniqueness validation works
- [ ] Empty code validation works
- [ ] Format validation works
- [ ] Form data preservation works
- [ ] Both code types accepted at requesting units
- [ ] Code source tracked in notes
- [ ] Error messages display correctly

## Future Enhancements

1. **Code Templates** - Predefined format templates
2. **Sequential Numbering** - Auto-increment manual codes
3. **Bulk Manual Codes** - Import codes from CSV
4. **Code Prefixes** - Department-specific prefixes
5. **Code Validation Rules** - Custom validation per organization

## Conclusion

The manual authorization code feature provides desk office staff with flexibility while maintaining system integrity. Both auto-generated and manually input codes work identically throughout the system, ensuring seamless operation across all departments and specialties.

---

**Implementation Date:** 2025-10-05  
**Status:** ✅ Complete and Ready for Use  
**Version:** 1.0

