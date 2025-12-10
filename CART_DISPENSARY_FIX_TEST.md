# Cart Dispensary Selection Fix - Test Guide

## Summary of Changes

### Issue
Cart #2 was not properly detecting the selected dispensary and loading stock data accordingly. The problem was related to:
1. Missing CSRF token in the AJAX fetch request headers
2. Incomplete error handling for OneToOne field access (dispensary.active_store)
3. Missing error logging for debugging

### Files Modified

1. **pharmacy/templates/pharmacy/cart/view_cart.html**
   - Fixed `updateDispensary()` JavaScript function
   - Added CSRF token to fetch request headers
   - Improved error handling and logging
   - Removed unnecessary setTimeout delay
   - Added better loading indicator management

2. **pharmacy/cart_models.py**
   - Improved `update_available_stock()` method
   - Added `hasattr()` check for OneToOne field (active_store)
   - Added comprehensive error logging
   - Better exception handling

3. **pharmacy/cart_views.py**
   - Fixed `view_cart()` function for loading available medications
   - Fixed `complete_dispensing_from_cart()` function
   - Added `hasattr()` checks for OneToOne field access
   - Added error logging

## Testing Instructions

### Test Setup
Cart #2 has been reset with:
- Dispensary: None (not selected)
- Status: Active
- 3 items: Amoxicillin-Clavulanate, Adrenaline, Ceftriaxone
- All items showing available_stock=0 (because no dispensary selected)

### Test Case 1: Select Dispensary and Verify Stock Update

**Steps:**
1. Navigate to: http://127.0.0.1:8000/pharmacy/cart/2/
2. Open browser console (F12) to see debug logs
3. Observe the "Select Dispensary" dropdown
4. Verify all cart items show stock status as "Out of stock" or "0 available"
5. Select "THEATRE PHARMACY" from the dropdown
6. Observe the loading indicator appears: "Updating dispensary and checking stock availability..."
7. Check browser console for logs:
   - "updateDispensary called, select.value: 2"
   - "Valid dispensary selected, submitting form"
   - "Form data being sent: csrfmiddlewaretoken: [token], dispensary_id: 2"
   - "Response status: [should be 200 or redirect]"
   - "Dispensary updated successfully, reloading page..."
8. Page should reload automatically
9. After reload, verify:
   - Dispensary dropdown shows "THEATRE PHARMACY" selected
   - Cart items show updated stock:
     * Amoxicillin-Clavulanate: "25 available" (green badge)
     * Adrenaline: "36 available" (green badge)
     * Ceftriaxone: "30 available" (green badge)
   - Success message: "Dispensary updated to THEATRE PHARMACY"

**Expected Results:**
- ✓ Dispensary selection triggers immediate form submission
- ✓ Loading indicator appears during update
- ✓ CSRF token is included in request (check console logs)
- ✓ Page reloads automatically after successful update
- ✓ Stock availability is updated for all items
- ✓ Dispensary remains selected after reload

**If Test Fails:**
- Check browser console for JavaScript errors
- Check Django server logs for backend errors
- Verify CSRF token is present in logs
- Check that the dispensary has an associated ActiveStore

### Test Case 2: Verify Invoice Generation

**Steps:**
1. After selecting dispensary (Test Case 1), scroll down to cart summary
2. Check "Can generate invoice?" status
3. Click "Generate Invoice" button
4. Verify invoice is created successfully

**Expected Results:**
- ✓ "Generate Invoice" button is enabled after dispensary selection
- ✓ Invoice is created with correct amounts
- ✓ Cart status changes to "Invoiced"

### Test Case 3: Verify Stock Status Display

**Steps:**
1. On cart page with dispensary selected
2. Check stock status badges for each item
3. Verify colors and messages:
   - Green badge with checkmark: Sufficient stock
   - Yellow badge with warning: Partial stock
   - Red badge with X: Out of stock

**Expected Results:**
- ✓ Stock badges show correct status
- ✓ Available quantity is displayed
- ✓ Badges are color-coded appropriately

### Test Case 4: Test Cart Without Dispensary

**Steps:**
1. Reset cart: `python manage.py shell -c "from pharmacy.cart_models import PrescriptionCart; cart = PrescriptionCart.objects.get(id=2); cart.dispensary = None; cart.save(); [item.update_available_stock() or item.save() for item in cart.items.all()]"`
2. Navigate to: http://127.0.0.1:8000/pharmacy/cart/2/
3. Verify:
   - Dispensary dropdown shows "-- Select Dispensary --" option
   - All items show 0 stock or "Out of stock"
   - "Generate Invoice" button is disabled
   - Warning message: "No dispensary selected"

**Expected Results:**
- ✓ Cart gracefully handles missing dispensary
- ✓ Stock shows 0 for all items
- ✓ User is prompted to select dispensary

### Test Case 5: Verify Error Handling

**Steps:**
1. In browser console, test error scenarios:
   - Network error: Disconnect network, try selecting dispensary
   - Invalid dispensary: Manually edit select value to invalid ID
2. Verify error handling:
   - User-friendly error messages appear
   - Select dropdown is re-enabled on error
   - Loading indicator is removed on error

**Expected Results:**
- ✓ Error messages are shown to user
- ✓ UI recovers gracefully from errors
- ✓ Errors are logged to console

## Verification Checklist

- [ ] Dispensary selection works via dropdown
- [ ] Stock availability updates after dispensary selection
- [ ] CSRF token is included in fetch requests
- [ ] Page reloads automatically after update
- [ ] Loading indicator appears during update
- [ ] Error messages appear on failure
- [ ] Console logs show debug information
- [ ] Cart can generate invoice after dispensary selection
- [ ] Stock badges show correct colors and messages
- [ ] Cart handles missing dispensary gracefully

## Technical Details

### JavaScript Changes
- Added CSRF token header: `'X-CSRFToken': csrfToken`
- Added `credentials: 'same-origin'` for cookie handling
- Improved error handling with try-catch
- Better loading indicator management
- More detailed console logging

### Backend Changes
- Changed from `getattr(dispensary, 'active_store', None)` to `hasattr(dispensary, 'active_store')` check
- Added proper exception handling around OneToOne field access
- Added logging for errors: `logger.warning()` and `logger.error()`
- More robust stock update logic

### Why These Changes Matter
1. **CSRF Token**: Django requires CSRF protection for POST requests. Without it, requests are rejected with 403 Forbidden.
2. **hasattr Check**: Django's OneToOne fields can raise `RelatedObjectDoesNotExist` exceptions. Using `hasattr()` is safer.
3. **Error Logging**: Helps diagnose issues in production without exposing errors to users.

## Rollback Instructions (If Needed)

If the changes cause issues, rollback with:
```bash
git diff HEAD pharmacy/templates/pharmacy/cart/view_cart.html > cart_fix.patch
git checkout HEAD -- pharmacy/templates/pharmacy/cart/view_cart.html
git checkout HEAD -- pharmacy/cart_models.py
git checkout HEAD -- pharmacy/cart_views.py
```

## Contact

If you encounter any issues during testing, check:
1. Browser console for JavaScript errors
2. Django server logs for backend errors
3. Network tab in browser DevTools for failed requests
4. Database to verify dispensary has active_store relationship
