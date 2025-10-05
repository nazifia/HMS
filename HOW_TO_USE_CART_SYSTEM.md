# How to Use the Prescription Cart System - Visual Guide

## 🎯 Quick Access Points

### Option 1: From Prescription List Page

**URL**: `http://127.0.0.1:8000/pharmacy/prescriptions/`

**Steps**:
1. Navigate to **Pharmacy** → **Prescriptions** (or go to the URL above)
2. You'll see a table with all prescriptions
3. In the **Actions** column (rightmost), you'll see buttons for each prescription:
   - 🔵 **View** (blue button)
   - 🟣 **Create Cart** (purple gradient button) ← **CLICK THIS!**
   - 🟢 **Dispense** (green button)
   - ⚫ **Print** (gray button)

4. Click the **"Create Cart"** button (purple with shopping cart icon)

---

### Option 2: From Prescription Detail Page

**URL**: `http://127.0.0.1:8000/pharmacy/prescriptions/<prescription_id>/`

**Steps**:
1. Click **"View"** button on any prescription from the list
2. You'll be taken to the prescription detail page
3. Scroll down to the **Payment & Dispensing** section
4. You'll see a button group with:
   - 🟣 **Create Billing Cart** (purple button with shopping cart icon) ← **CLICK THIS!**
   - 🟡 **Pay Now** (yellow button - only if invoice exists)

5. Below the buttons, you'll see helper text:
   > ℹ️ Create a cart to review items, check availability, and generate invoice

---

### Option 3: From Pharmacy Dashboard

**URL**: `http://127.0.0.1:8000/pharmacy/dashboard/`

**Steps**:
1. Go to **Pharmacy Dashboard**
2. Look for the **"Prescription Carts"** card (purple gradient)
3. Click **"View All Carts"** button
4. This shows all existing carts
5. From there, you can view/manage existing carts

---

## 📋 Complete Workflow Example

### Step-by-Step Guide

#### **Step 1: Create a Cart**

1. **Go to**: `http://127.0.0.1:8000/pharmacy/prescriptions/`
2. **Find** any prescription in the list
3. **Click** the purple **"Create Cart"** button in the Actions column
4. **Result**: Cart is created with all prescription items

**What happens**:
- System creates a new `PrescriptionCart`
- Adds all undispensed prescription items
- Redirects you to the cart view page

---

#### **Step 2: View Your Cart**

**URL**: `http://127.0.0.1:8000/pharmacy/cart/<cart_id>/`

**You'll see**:
- 📊 **Cart Header**: Cart ID, patient info, status
- 🏥 **Dispensary Section**: Dropdown to select dispensary
- 📦 **Items Table**: All medications with quantities
- 📈 **Status Timeline**: Visual progress indicator
- 💰 **Summary Panel**: Totals and action buttons

---

#### **Step 3: Select Dispensary**

1. **Find** the "Select Dispensary" section (below the header)
2. **Choose** a dispensary from the dropdown
3. **Click** "Update Dispensary" button
4. **Result**: Stock availability updates for all items

**What you'll see**:
- 🟢 **Green badge**: Sufficient stock available
- 🟡 **Yellow badge**: Partial stock available
- 🔴 **Red badge**: Out of stock

---

#### **Step 4: Adjust Quantities**

1. **Find** the quantity input fields in the items table
2. **Change** any quantity as needed
3. **Result**: Totals update automatically (AJAX)

**Features**:
- Real-time calculation
- No page reload
- Instant feedback
- Validation (can't exceed prescribed quantity)

---

#### **Step 5: Generate Invoice**

1. **Scroll** to the right panel (Summary)
2. **Click** the purple **"Generate Invoice & Proceed to Payment"** button
3. **Result**: Invoice created, redirected to payment page

**Pre-conditions** (button will be disabled if not met):
- ✅ Dispensary selected
- ✅ At least one item in cart
- ✅ All items have sufficient stock

---

#### **Step 6: Process Payment**

**URL**: `http://127.0.0.1:8000/pharmacy/prescriptions/<prescription_id>/payment/`

1. **Review** the payment summary
2. **Select** payment method
3. **Enter** payment details
4. **Click** "Process Payment"
5. **Result**: Payment recorded, cart status updated to "Paid"

---

#### **Step 7: Complete Dispensing**

1. **Return** to cart view (or click "Complete Dispensing" button)
2. **Click** the green **"Complete Dispensing"** button
3. **Result**: 
   - Medications dispensed
   - Inventory updated
   - Dispensing logs created
   - Prescription status updated
   - Cart status: "Completed"

---

## 🔍 Finding Existing Carts

### View All Carts

**URL**: `http://127.0.0.1:8000/pharmacy/carts/`

**Access**:
1. **Pharmacy Dashboard** → Click "View All Carts" card
2. **Or** navigate directly to the URL above

**Features**:
- Filter by status (Active, Invoiced, Paid, Completed, Cancelled)
- Filter by dispensary
- Search by patient name or prescription ID
- Pagination
- Action buttons for each cart

---

## 🎨 Visual Indicators

### Cart Status Colors

- 🔵 **Active** (Blue): Cart being prepared
- 🟠 **Invoiced** (Orange): Invoice created, awaiting payment
- 🟢 **Paid** (Green): Payment completed, ready to dispense
- 🟣 **Completed** (Purple): Dispensing completed
- 🔴 **Cancelled** (Red): Cart cancelled

### Stock Status Colors

- 🟢 **Available** (Green): Sufficient stock
- 🟡 **Partial** (Yellow): Some stock available
- 🔴 **Out of Stock** (Red): No stock

---

## 🚨 Troubleshooting

### "I don't see the Create Cart button"

**Check**:
1. ✅ Are you on the prescription list or detail page?
2. ✅ Have you refreshed the page after updating templates?
3. ✅ Is the prescription in a valid status (not cancelled)?

**Solution**:
- Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- Check browser console for errors (F12)
- Verify migrations are run: `python manage.py migrate`

---

### "Create Cart button gives an error"

**Possible causes**:
1. ❌ Migrations not run
2. ❌ URL not registered
3. ❌ View not imported

**Solution**:
```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Restart server
python manage.py runserver
```

---

### "Cart page shows 404 error"

**Check**:
1. ✅ Is the cart ID valid?
2. ✅ Are URLs properly configured?

**Solution**:
- Check `pharmacy/urls.py` has cart URLs
- Verify cart exists in database
- Check server logs for errors

---

## 📱 Mobile Access

The cart system is fully responsive:

- **Mobile**: Stacked layout, touch-friendly buttons
- **Tablet**: 2-column layout
- **Desktop**: Full 3-column layout with sidebar

---

## 🎯 Quick Links

### Main Pages

1. **Prescription List**: `/pharmacy/prescriptions/`
2. **Cart List**: `/pharmacy/carts/`
3. **Pharmacy Dashboard**: `/pharmacy/dashboard/`

### Cart Actions

1. **Create Cart**: `/pharmacy/cart/create/<prescription_id>/`
2. **View Cart**: `/pharmacy/cart/<cart_id>/`
3. **Cart Receipt**: `/pharmacy/cart/<cart_id>/receipt/`

---

## 💡 Tips & Best Practices

### For Pharmacists

1. ✅ **Always select dispensary first** - This updates stock availability
2. ✅ **Review stock status** - Check green/yellow/red badges
3. ✅ **Adjust quantities** - Based on actual availability
4. ✅ **Remove unavailable items** - Don't bill for out-of-stock items
5. ✅ **Generate invoice only when ready** - Can't edit after invoice created

### For NHIA Patients

1. ℹ️ **10% patient payment** - Patient pays 10% of total
2. ℹ️ **90% NHIA coverage** - NHIA covers 90% of total
3. ℹ️ **Clear breakdown** - Summary shows both amounts
4. ℹ️ **Accurate billing** - Based on actual dispensed quantities

---

## 📞 Support

If you encounter issues:

1. **Check documentation**:
   - `PRESCRIPTION_CART_SYSTEM.md` - Complete system docs
   - `CART_SYSTEM_QUICK_START.md` - Quick reference
   - `CART_TEMPLATES_IMPLEMENTATION.md` - Template details

2. **Check server logs**:
   ```bash
   # View Django logs
   python manage.py runserver
   # Check for errors in terminal
   ```

3. **Check browser console**:
   - Press F12
   - Go to Console tab
   - Look for JavaScript errors

---

## ✅ Verification Checklist

Before using the system, verify:

- [ ] Migrations run successfully
- [ ] Server running without errors
- [ ] Can access prescription list page
- [ ] "Create Cart" button visible
- [ ] Can create a cart
- [ ] Can view cart page
- [ ] Can select dispensary
- [ ] Stock status shows correctly
- [ ] Can adjust quantities
- [ ] Can generate invoice
- [ ] Can process payment
- [ ] Can complete dispensing

---

## 🎉 Success!

Once you see the **"Create Cart"** button (purple with shopping cart icon) in the Actions column of the prescription list, you're ready to use the system!

**Happy billing!** 🛒💊

