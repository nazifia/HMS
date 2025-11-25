# Browser Testing Guide - Cart Dispensary Selection

## 🎯 What You're Testing

The cart should now properly detect the selected dispensary and update stock availability automatically.

## 🚀 Quick Start

### Step 1: Open the Cart Page

1. Navigate to: **http://127.0.0.1:8000/pharmacy/cart/2/**
2. You should see Cart #2 for patient Mary Sule

### Step 2: Open Developer Console

**Press F12** to open browser DevTools
- Make sure you're on the **Console** tab
- This will show you debug information

### Step 3: Check Initial State

Before selecting a dispensary, verify:

**What to See:**
```
┌─────────────────────────────────────────┐
│ Select Dispensary                       │
│ ┌─────────────────────────────────────┐ │
│ │ -- Select Dispensary --           ▼ │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘

Cart Items:
┌────────────────────────────────────────────────────┐
│ Amoxicillin-Clavulanate  │ [Out of Stock] ❌       │
│ Adrenaline              │ [Out of Stock] ❌       │
│ Ceftriaxone             │ [Out of Stock] ❌       │
└────────────────────────────────────────────────────┘

[Generate Invoice] ❌ DISABLED
```

**Console Should Show:**
- No errors
- Clean loading of the page

### Step 4: Select Dispensary

1. Click on the **"-- Select Dispensary --"** dropdown
2. Select **"THEATRE PHARMACY - [location]"**

**What Should Happen Immediately:**

1. **Loading Indicator Appears:**
   ```
   ⏳ Updating dispensary and checking stock availability...
   ```

2. **Console Shows Debug Logs:**
   ```
   updateDispensary called, select.value: 2
   Valid dispensary selected, submitting form
   Form data being sent:
     csrfmiddlewaretoken: [long token string]
     dispensary_id: 2
   Response status: 200
   Dispensary updated successfully, reloading page...
   ```

3. **Page Reloads** (automatically after ~1 second)

### Step 5: Verify After Reload

After the page reloads, check:

**✅ Dispensary Selection:**
```
┌─────────────────────────────────────────┐
│ Select Dispensary                       │
│ ┌─────────────────────────────────────┐ │
│ │ THEATRE PHARMACY - [location]     ▼ │ │  ← Should stay selected
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**✅ Success Message (Green Alert):**
```
✓ Dispensary updated to THEATRE PHARMACY
```

**✅ Stock Updates (Green Badges):**
```
Cart Items:
┌──────────────────────────────────────────────────────────┐
│ Amoxicillin-Clavulanate  │ [✓ 25 available] 🟢          │
│ Adrenaline              │ [✓ 36 available] 🟢          │
│ Ceftriaxone             │ [✓ 30 available] 🟢          │
└──────────────────────────────────────────────────────────┘

[Generate Invoice] ✅ ENABLED (blue button)
```

**✅ Cart Summary Shows Totals:**
```
Cart Summary
├─ Subtotal: ₦3,200.00
├─ Patient Pays (10%): ₦320.00
└─ NHIA Covers (90%): ₦2,880.00
```

### Step 6: Test Invoice Generation

1. Scroll to the **Cart Summary** section at the bottom
2. Click **"Generate Invoice"** button
3. Should redirect to invoice or update cart status to "Invoiced"

## 🎨 Visual Indicators

### Stock Status Colors

| Color | Icon | Meaning | Example |
|-------|------|---------|---------|
| 🟢 Green | ✓ | Sufficient stock | "25 available (need 1)" |
| 🟡 Yellow | ⚠️ | Partial stock | "Only 5 available (need 10)" |
| 🔴 Red | ✗ | Out of stock | "Out of stock" |

### Button States

| Button | State | When |
|--------|-------|------|
| [Generate Invoice] | 🔵 Blue (Enabled) | After dispensary selected & stock available |
| [Generate Invoice] | ⚪ Gray (Disabled) | No dispensary or insufficient stock |

## 📸 What to Screenshot (If Reporting Issues)

If something doesn't work, take screenshots of:

1. **Full Page View** - showing cart items and their stock status
2. **Browser Console** - showing any errors (red text)
3. **Network Tab** (F12 → Network) - showing the POST request to `/pharmacy/cart/2/update-dispensary/`
4. **Dispensary Dropdown** - showing what's selected

## ❌ Common Issues & Solutions

### Issue 1: Dropdown doesn't trigger update
**Symptoms:**
- Click dropdown, select dispensary
- Nothing happens
- No loading indicator

**Solution:**
1. Check Console for JavaScript errors
2. Verify the page loaded correctly (no red errors)
3. Try hard refresh: **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac)

### Issue 2: Page reloads but stock doesn't update
**Symptoms:**
- Dropdown shows selected dispensary
- But stock still shows 0 or "Out of stock"

**Solution:**
1. Check Console for backend errors
2. Verify dispensary has an ActiveStore:
   ```python
   python manage.py shell -c "from pharmacy.models import Dispensary; print(hasattr(Dispensary.objects.get(id=2), 'active_store'))"
   ```
3. Check if medications exist in ActiveStoreInventory

### Issue 3: CSRF error in console
**Symptoms:**
- Console shows: "CSRF verification failed"
- 403 Forbidden error

**Solution:**
1. This should be fixed now with our changes
2. If still happens, clear browser cookies and try again
3. Check if `{% csrf_token %}` is in the form (view page source)

### Issue 4: Stock shows 0 even after selecting dispensary
**Symptoms:**
- Dispensary selected successfully
- Page reloads
- Stock still shows 0

**Check:**
1. Does the dispensary have stock?
   ```python
   python manage.py shell -c "
   from pharmacy.models import ActiveStoreInventory;
   inv = ActiveStoreInventory.objects.filter(active_store__dispensary_id=2);
   print(f'Total medications in stock: {inv.count()}')
   "
   ```

## ✅ Success Criteria

The fix is working if:

- [x] Dispensary dropdown triggers automatic form submission
- [x] Loading indicator appears during update
- [x] Console shows debug logs (no errors)
- [x] Page reloads automatically after ~1 second
- [x] Dispensary stays selected after reload
- [x] Stock badges change from red to green (if stock available)
- [x] Stock numbers update (0 → actual stock)
- [x] Success message appears at top
- [x] "Generate Invoice" button becomes enabled
- [x] No JavaScript errors in console
- [x] No CSRF errors

## 🎓 Understanding the Console Logs

When you select a dispensary, you should see these logs in order:

```
1. updateDispensary called, select.value: 2
   ↓ (JavaScript function triggered by dropdown change)

2. Valid dispensary selected, submitting form
   ↓ (Validation passed, preparing to submit)

3. Form data being sent:
     csrfmiddlewaretoken: abc123...
     dispensary_id: 2
   ↓ (Data being sent to server)

4. Response status: 200
   ↓ (Server accepted the request)

5. Dispensary updated successfully, reloading page...
   ↓ (Server updated cart, now reloading)

6. [PAGE RELOADS]
   ↓

7. (New page load - no more logs from updateDispensary)
```

**If you see different logs or errors, that helps diagnose issues!**

## 📝 Test Checklist

Copy this and check off as you test:

```
□ Cart page loads without errors
□ Dispensary dropdown is visible
□ Initial stock shows 0 or "Out of stock"
□ Console is open (F12)
□ Select dispensary from dropdown
□ Loading indicator appears
□ Console shows debug logs
□ No red errors in console
□ Page reloads automatically
□ Dispensary stays selected after reload
□ Stock badges turn green
□ Stock numbers update correctly
□ Success message appears
□ "Generate Invoice" button is enabled
□ Clicking "Generate Invoice" works
```

## 🎉 Expected Result

After selecting the dispensary, the cart should look like this:

```
╔══════════════════════════════════════════════════════════╗
║ ✓ Dispensary updated to THEATRE PHARMACY                ║
╚══════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────┐
│ Select Dispensary: [THEATRE PHARMACY - Theatre]       ▼ │
└──────────────────────────────────────────────────────────┘

Cart Items (3 items)
┌────────────────────────────────────────────────────────────────┐
│ Medication              │ Qty │ Stock            │ Subtotal   │
├────────────────────────────────────────────────────────────────┤
│ Amoxicillin-Clavulanate │  1  │ ✓ 25 available  │ ₦1,000.00  │
│ Adrenaline              │  1  │ ✓ 36 available  │ ₦1,200.00  │
│ Ceftriaxone             │  1  │ ✓ 30 available  │ ₦1,000.00  │
└────────────────────────────────────────────────────────────────┘

Cart Summary
┌────────────────────────────┐
│ Subtotal:      ₦3,200.00   │
│ Patient Pays:    ₦320.00   │  ← 10% (NHIA patient)
│ NHIA Covers:   ₦2,880.00   │  ← 90%
│                            │
│ [Generate Invoice] 🔵      │  ← Click to continue
└────────────────────────────┘
```

## 🆘 Need Help?

If tests fail:
1. Screenshot the issue
2. Copy console logs
3. Check `CART_FIX_SUMMARY.md` for troubleshooting
4. Review Django server logs for backend errors

---

**Ready to test? Open http://127.0.0.1:8000/pharmacy/cart/2/ and follow the steps above!**
