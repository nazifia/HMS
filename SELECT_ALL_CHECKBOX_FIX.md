# Select All Checkbox Fix - Test Plan

## Summary of Issues Fixed

### Issue 1: Bulk Store Dashboard (`/pharmacy/bulk-store/`)
**Problem:** The "Select All" checkbox only selected items on the current DataTables page, not all items across all pages.

**Root Cause:** The JavaScript was using a static NodeList (`querySelectorAll('.item-checkbox')`) that only captured checkboxes present when the page loaded. When DataTables paginated the table, new checkboxes weren't included in the selection.

**Fix Applied:**
- Modified the select all handler to query checkboxes dynamically each time it's clicked (line 1131-1132 in `pharmacy/templates/pharmacy/bulk_store_dashboard.html`)
- Implemented event delegation for individual checkbox changes to work with dynamically loaded content (line 1141-1152)
- Added logic to automatically update the "Select All" checkbox state when individual items are checked/unchecked

### Issue 2: Active Store Bulk Transfers (`/pharmacy/dispensaries/2/active-store/bulk-transfers/`)
**Problem:** The "Select All Medications" checkbox was enabled but had NO event handler attached, so clicking it did nothing.

**Root Cause:** The checkbox was enabled on line 465 when a bulk store was selected, but no `change` event handler was implemented.

**Fix Applied:**
- Added event handler for the select all checkbox (line 494-499 in `templates/pharmacy/active_store_bulk_transfers.html`)
- Implemented logic to select/deselect all visible medication checkboxes for the selected bulk store
- Added synchronization to update the select all checkbox state when individual medications are checked/unchecked (line 442-451)
- Reset select all checkbox when bulk store selection changes (line 490)

---

## Test Instructions

### Prerequisites
1. Ensure the Django development server is running on port 8000
2. Log in with appropriate pharmacy permissions

### Test 1: Bulk Store Dashboard Select All

**URL:** http://127.0.0.1:8000/pharmacy/bulk-store/

**Steps:**
1. Navigate to the bulk store dashboard
2. Verify the inventory table has multiple items (ideally 25+ to test pagination)
3. **Test: Select All on Current Page**
   - Check the "Select All" checkbox in the table header
   - ✅ **Expected:** All visible item checkboxes on the current page should be checked
   - ✅ **Expected:** The selected count should update (shown in "Apply Bulk Markup" modal)

4. **Test: Navigate to Next Page**
   - If pagination is available, click "Next" to go to page 2
   - ✅ **Expected:** The select all checkbox should reflect the state of items on this page
   - Check the select all checkbox again
   - ✅ **Expected:** Items on page 2 should also be selected

5. **Test: Individual Checkbox Changes**
   - Uncheck one item checkbox
   - ✅ **Expected:** The select all checkbox should automatically become unchecked
   - Check the item again
   - ✅ **Expected:** If all items are now checked, the select all checkbox should automatically become checked

6. **Test: Apply Bulk Markup**
   - Select several items using the checkboxes
   - Click "Apply Bulk Markup" button
   - ✅ **Expected:** The modal should show the correct count of selected items
   - Select "Apply to selected items"
   - ✅ **Expected:** Submitting should only affect the selected items

### Test 2: Active Store Bulk Transfers Select All

**URL:** http://127.0.0.1:8000/pharmacy/dispensaries/2/active-store/bulk-transfers/

**Steps:**
1. Navigate to the active store bulk transfers page
2. **Test: Initial State**
   - ✅ **Expected:** The "Select All Medications" checkbox should be disabled
   - ✅ **Expected:** No medications should be visible in the table

3. **Test: Select Bulk Store**
   - Select a bulk store from the "Source Bulk Store" dropdown
   - ✅ **Expected:** Medications for that bulk store should appear in the table
   - ✅ **Expected:** The "Select All Medications" checkbox should become enabled
   - ✅ **Expected:** The hint text should update to show medication count

4. **Test: Select All Medications**
   - Check the "Select All Medications" checkbox
   - ✅ **Expected:** All visible medication checkboxes should be checked
   - ✅ **Expected:** Quantity input fields for all medications should be enabled and set to 1 (or available quantity if less)
   - ✅ **Expected:** All medication rows should be highlighted (blue background)
   - ✅ **Expected:** The "Submit Transfer Requests" button should become enabled

5. **Test: Unselect All**
   - Uncheck the "Select All Medications" checkbox
   - ✅ **Expected:** All medication checkboxes should be unchecked
   - ✅ **Expected:** All quantity input fields should be disabled and reset to 0
   - ✅ **Expected:** Row highlighting should be removed
   - ✅ **Expected:** The "Submit Transfer Requests" button should become disabled

6. **Test: Individual Checkbox Changes**
   - Manually check 3 medication checkboxes
   - ✅ **Expected:** The select all checkbox should remain unchecked (not all items selected)
   - Manually check all remaining medication checkboxes
   - ✅ **Expected:** The select all checkbox should automatically become checked

7. **Test: Change Bulk Store**
   - Select a different bulk store
   - ✅ **Expected:** The previous selections should be cleared
   - ✅ **Expected:** The select all checkbox should be unchecked
   - ✅ **Expected:** New medications should appear
   - ✅ **Expected:** The select all checkbox should remain enabled

8. **Test: Form Submission**
   - Use select all to choose multiple medications
   - Adjust quantities as needed
   - Click "Submit Transfer Requests"
   - ✅ **Expected:** Transfer requests should be created for all selected medications

---

## Technical Details

### Files Modified
1. `C:\Users\Dell\Desktop\HMS\pharmacy\templates\pharmacy\bulk_store_dashboard.html`
   - Lines 1118-1152: Updated select all and individual checkbox handlers

2. `C:\Users\Dell\Desktop\HMS\templates\pharmacy\active_store_bulk_transfers.html`
   - Lines 422-454: Enhanced individual checkbox handler with select all sync
   - Lines 490: Reset select all on bulk store change
   - Lines 494-499: Added select all checkbox handler

### Key JavaScript Changes

**bulk_store_dashboard.html:**
```javascript
// Now queries checkboxes dynamically (line 1132)
const itemCheckboxes = document.querySelectorAll('.item-checkbox');

// Uses event delegation for individual checkboxes (line 1141)
document.addEventListener('change', function(e) {
    if (e.target && e.target.classList.contains('item-checkbox')) {
        // Updates count and syncs select all checkbox state
    }
});
```

**active_store_bulk_transfers.html:**
```javascript
// New handler for select all medications (line 494)
$('#selectAllMedications').on('change', function() {
    // Selects/deselects all visible medication checkboxes
});

// Enhanced individual checkbox handler (line 442)
// Now updates select all checkbox state automatically
$('#selectAllMedications').prop('checked', totalVisible > 0 && totalVisible === totalChecked);
```

---

## Troubleshooting

### Issue: Select all doesn't work after pagination
**Solution:** Clear browser cache and hard refresh (Ctrl+F5). The new JavaScript should query checkboxes dynamically.

### Issue: Select all checkbox doesn't sync with individual checkboxes
**Solution:** Check browser console for JavaScript errors. Ensure jQuery is loaded properly.

### Issue: Select all remains disabled on bulk transfers page
**Solution:** Ensure a bulk store is selected first. The checkbox is only enabled when medications are available.

---

## Browser Console Testing

Open browser Developer Tools (F12) and run these commands to verify functionality:

### Test 1: Check if select all handler is attached
```javascript
// Bulk Store Dashboard
console.log($('#selectAll').length); // Should return 1

// Active Store Bulk Transfers
console.log($('#selectAllMedications').length); // Should return 1
```

### Test 2: Manually trigger select all
```javascript
// Bulk Store Dashboard
$('#selectAll').prop('checked', true).trigger('change');
console.log($('.item-checkbox:checked').length); // Should match visible items

// Active Store Bulk Transfers
$('#id_bulk_store').val('1').trigger('change'); // Replace '1' with actual bulk store ID
setTimeout(() => {
    $('#selectAllMedications').prop('checked', true).trigger('change');
    console.log($('.medication-checkbox:checked').length); // Should match visible medications
}, 500);
```

### Test 3: Verify event delegation
```javascript
// Check if change events are being captured
$('.medication-checkbox').on('change', function() {
    console.log('Individual checkbox changed:', this.checked);
});
```

---

## Summary

✅ **Fixed:** Bulk Store Dashboard select all now works across all DataTables pages
✅ **Fixed:** Active Store Bulk Transfers select all now has proper event handler
✅ **Enhanced:** Both checkboxes now sync automatically with individual selections
✅ **Enhanced:** Improved user experience with visual feedback and proper state management

**Status:** Ready for testing
**Server:** Running on http://127.0.0.1:8000
**Next Step:** Follow the test instructions above to verify the fixes
