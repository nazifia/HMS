# Theatre/Surgery Pack Order Logic - Issues Fixed

## Summary
Fixed critical issues in the theatre/surgery packs order logic that were causing errors when ordering medical packs for surgeries and labor records.

## Issues Found and Fixed

### 1. **Missing labor_record Field in PackOrder Model**
**Issue**: The `labor_record` field was removed from the PackOrder model in migration 0012 but was never re-added, while the code still referenced it.

**Impact**: 
- AttributeError when ordering packs for labor records
- Form save method failed when trying to set `pack_order.labor_record`
- Templates displayed errors when trying to access `pack_order.labor_record`

**Fix**:
- Added `labor_record` field back to PackOrder model in `pharmacy/models.py` (line 1039)
- Created migration `0020_add_labor_record_to_packorder.py` to add the field to the database

**Files Modified**:
- `pharmacy/models.py`
- `pharmacy/migrations/0020_add_labor_record_to_packorder.py` (new file)

---

### 2. **Incorrect Patient Field Initialization in Theatre View**
**Issue**: In `theatre/views.py` line 987, the patient field was initialized with `surgery.patient.id` (integer) instead of `surgery.patient` (Patient object).

**Impact**:
- Form validation errors
- Patient field not properly pre-populated

**Fix**:
- Removed patient from initial_data dictionary
- Added `preselected_patient=surgery.patient` parameter to PackOrderForm initialization
- Added explicit patient assignment in POST handler: `pack_order.patient = surgery.patient`

**Files Modified**:
- `theatre/views.py` (lines 950-959, 993-1002)

---

### 3. **Incorrect Surgery Type Filtering Logic**
**Issue**: Surgery type filtering used `surgery_type__icontains=surgery.surgery_type.name.lower()` which is a string search on a CharField with choices, leading to incorrect or no matches.

**Impact**:
- Surgery-specific packs not properly filtered
- Generic surgery packs shown instead of procedure-specific packs

**Fix**:
- Added surgery type mapping dictionary to convert surgery type names to choice values
- Changed filter to use exact match: `surgery_type=surgery_type`
- Matches the same logic used in PackOrderForm

**Files Modified**:
- `theatre/views.py` (lines 927-948)

---

### 4. **Missing Patient Pre-selection in PackOrderForm for Surgery Context**
**Issue**: When ordering packs from surgery context, the patient field was not properly pre-selected and disabled.

**Impact**:
- Users could accidentally select wrong patient
- Inconsistent UX compared to other forms

**Fix**:
- Refactored patient pre-selection logic in PackOrderForm.__init__
- Automatically set preselected_patient from surgery.patient or labor_record.patient
- Applied patient field styling and disabled state
- Added hidden field for form submission

**Files Modified**:
- `pharmacy/forms.py` (lines 1161-1245)

---

### 5. **Inconsistent Form Initialization in Labor View**
**Issue**: Labor pack order view had similar issues to theatre view - incorrect patient initialization and missing form parameters.

**Impact**:
- Same issues as theatre view but for labor records

**Fix**:
- Updated POST handler to include `labor_record=record, preselected_patient=record.patient`
- Updated GET handler to remove patient from initial_data and add proper form parameters

**Files Modified**:
- `labor/views.py` (lines 229-238, 272-278)

---

## Testing Recommendations

### 1. Test Surgery Pack Orders
```python
# Test ordering a pack for a surgery
1. Navigate to a surgery detail page
2. Click "Order Medical Pack"
3. Verify patient field is pre-selected and disabled
4. Verify only surgery-specific packs are shown
5. Select a pack and submit
6. Verify pack order is created successfully
7. Verify prescription is created automatically
8. Verify pack cost is added to surgery invoice
```

### 2. Test Labor Pack Orders
```python
# Test ordering a pack for a labor record
1. Navigate to a labor record detail page
2. Click "Order Medical Pack"
3. Verify patient field is pre-selected and disabled
4. Verify only labor-specific packs are shown
5. Select a pack and submit
6. Verify pack order is created successfully
7. Verify prescription is created automatically
8. Verify pack cost is added to patient billing
```

### 3. Test Surgery Type Filtering
```python
# Test that surgery-specific packs are properly filtered
1. Create packs for different surgery types (Appendectomy, Cesarean Section, etc.)
2. Create a surgery of type "Appendectomy"
3. Order a pack for the surgery
4. Verify only Appendectomy packs are shown in the dropdown
```

### 4. Test Database Migration
```bash
# Run the migration to add labor_record field
python manage.py migrate pharmacy 0020_add_labor_record_to_packorder

# Verify the field was added
python manage.py dbshell
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'pharmacy_packorder' AND column_name = 'labor_record';
```

---

## Database Migration Required

**IMPORTANT**: After deploying these changes, you must run the migration:

```bash
python manage.py migrate pharmacy
```

This will add the `labor_record` field back to the `pharmacy_packorder` table.

---

## Benefits of These Fixes

1. **Eliminates AttributeError**: No more crashes when ordering packs for labor records
2. **Improved UX**: Patient field is properly pre-selected and disabled, preventing user errors
3. **Better Pack Filtering**: Surgery-specific packs are correctly filtered by procedure type
4. **Consistent Behavior**: Theatre and labor pack ordering now work the same way
5. **Maintains Existing Functionality**: All existing features continue to work as expected

---

## Related Files

### Modified Files
- `pharmacy/models.py` - Added labor_record field to PackOrder model
- `pharmacy/forms.py` - Improved patient pre-selection logic
- `theatre/views.py` - Fixed patient initialization and surgery type filtering
- `labor/views.py` - Fixed patient initialization and form parameters

### New Files
- `pharmacy/migrations/0020_add_labor_record_to_packorder.py` - Migration to add labor_record field

### Unchanged Files (but referenced)
- `pharmacy/templates/pharmacy/pack_orders/pack_order_detail.html` - Already has labor_record display logic
- `pharmacy/templates/pharmacy/pack_orders/pack_order_list.html` - Already has labor_record display logic
- `theatre/templates/theatre/order_medical_pack.html` - Works correctly with fixes
- `labor/templates/labor/order_medical_pack.html` - Works correctly with fixes

---

## Notes

- The fixes maintain backward compatibility with existing pack orders
- NHIA discount logic for surgery packs remains unchanged
- Automatic prescription creation and billing integration remain unchanged
- All error handling and user messaging remain unchanged

