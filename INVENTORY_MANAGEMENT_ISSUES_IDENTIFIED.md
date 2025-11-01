# HMS Inventory Management System - Issues Identified

## Investigation Date: 2025-11-01

This document lists all issues identified in the HMS inventory management system across the following modules:
1. Supplier Management
2. Procurement
3. Bulk Store
4. Request & Transfer
5. Related Modules

---

## 1. SUPPLIER MANAGEMENT ISSUES

### 1.1 Logical Issues

#### Issue #SM-L001: Supplier List Template Variable Mismatch
**File**: `pharmacy/templates/pharmacy/supplier_list.html`
**Lines**: 55, 119-153, 183, 200
**Severity**: HIGH
**Description**: Template expects `suppliers` variable but view passes `page_obj`
**Current Code**:
```python
# views.py line 516
context = {
    'page_obj': page_obj,  # ← Passes page_obj
    ...
}
```
```html
<!-- supplier_list.html line 55 -->
<i class="fas fa-building"></i> Suppliers ({{ suppliers.paginator.count }} total)
<!-- line 74 -->
{% for supplier in suppliers %}
```
**Impact**: Template will fail to render supplier list, pagination will break
**Fix Required**: Change view to pass `suppliers` or update template to use `page_obj`

#### Issue #SM-L002: Missing Status Filter Implementation
**File**: `pharmacy/views.py`
**Lines**: 499-525
**Severity**: MEDIUM
**Description**: Template has status filter UI but view doesn't implement filtering logic
**Current Code**:
```python
def supplier_list(request):
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    # No handling of is_active parameter from template
```
**Template Code** (supplier_list.html line 33-37):
```html
<select name="is_active" id="is_active" class="form-select">
    <option value="">All Suppliers</option>
    <option value="true">Active Only</option>
    <option value="false">Inactive Only</option>
</select>
```
**Impact**: Status filter dropdown doesn't work, always shows only active suppliers
**Fix Required**: Add status filter logic in view

#### Issue #SM-L003: Incorrect Page Title Variable
**File**: `pharmacy/views.py`
**Lines**: 521, 541, 565
**Severity**: LOW
**Description**: Views use `page_title` but templates expect `title`
**Current Code**:
```python
context = {
    'page_title': 'Supplier List',  # ← Wrong variable name
}
```
**Template Code** (supplier_list.html line 3):
```html
{% block title %}{{ title }}{% endblock %}
```
**Impact**: Page titles won't display correctly in browser tabs
**Fix Required**: Change `page_title` to `title` or update templates

### 1.2 Template Issues

#### Issue #SM-T001: Inconsistent Variable Names
**File**: `pharmacy/templates/pharmacy/supplier_list.html`
**Lines**: Multiple
**Severity**: HIGH
**Description**: Template uses both `suppliers` and `page_obj` inconsistently
**Impact**: Pagination and list display will fail
**Fix Required**: Standardize to use `page_obj` throughout

#### Issue #SM-T002: Missing Error Handling
**File**: `pharmacy/templates/pharmacy/add_edit_supplier.html`
**Lines**: 17-22
**Severity**: MEDIUM
**Description**: No error message display for form validation errors
**Impact**: Users won't see validation errors when form submission fails
**Fix Required**: Add error message display block

---

## 2. PROCUREMENT ISSUES

### 2.1 Logical Issues

#### Issue #PR-L001: Incomplete Purchase Item Deletion
**File**: `pharmacy/views.py`
**Lines**: 1868-1872
**Severity**: CRITICAL
**Description**: `delete_purchase_item` function has no implementation (just `pass`)
**Current Code**:
```python
@login_required
def delete_purchase_item(request, item_id):
    """View for deleting a purchase item"""
    item = get_object_or_404(PurchaseItem, id=item_id)
    # Implementation for deleting purchase item
    pass  # ← No implementation!
```
**Impact**: Cannot delete purchase items, broken functionality
**Fix Required**: Implement deletion logic with total amount recalculation

#### Issue #PR-L002: Incomplete Purchase Approval Workflow
**File**: `pharmacy/views.py`
**Lines**: 1876-1896
**Severity**: CRITICAL
**Description**: Three critical functions have no implementation:
- `submit_purchase_for_approval` (line 1876-1880)
- `approve_purchase` (line 1884-1888)
- `reject_purchase` (line 1892-1896)
**Current Code**:
```python
@login_required
def submit_purchase_for_approval(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    # Implementation for submitting purchase for approval
    pass

@login_required
def approve_purchase(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    # Implementation for approving purchase
    pass

@login_required
def reject_purchase(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    # Implementation for rejecting purchase
    pass
```
**Impact**: Entire purchase approval workflow is broken
**Fix Required**: Implement complete approval workflow with status updates

#### Issue #PR-L003: Missing Purchase Item Edit Function
**File**: `pharmacy/views.py`
**Severity**: HIGH
**Description**: No `edit_purchase_item` function exists but URL pattern references it
**Impact**: Cannot edit purchase items after creation
**Fix Required**: Implement edit function for purchase items

#### Issue #PR-L004: Inefficient Total Amount Calculation
**File**: `pharmacy/views.py`
**Lines**: 1822-1824
**Severity**: MEDIUM
**Description**: Manual sum calculation instead of using model method
**Current Code**:
```python
# Update purchase total
new_total = sum(p_item.total_price for p_item in purchase.items.all())
purchase.total_amount = new_total
purchase.save()
```
**Better Approach**:
```python
purchase.update_total_amount()  # Use model method
```
**Impact**: Inconsistent calculation logic, potential bugs
**Fix Required**: Use model's `update_total_amount()` method

#### Issue #PR-L005: Missing Dispensary Assignment
**File**: `pharmacy/views.py`
**Lines**: 1719-1752
**Severity**: HIGH
**Description**: Purchase creation doesn't assign dispensary
**Current Code**:
```python
purchase = form.save(commit=False)
purchase.total_amount = Decimal('0.00')
purchase.created_by = request.user
# No dispensary assignment!
purchase.save()
```
**Impact**: Purchases not linked to dispensaries, inventory tracking issues
**Fix Required**: Add dispensary assignment logic

### 2.2 Database Issues

#### Issue #PR-D001: Missing Index on Purchase Date
**File**: `pharmacy/models.py`
**Lines**: 70-98
**Severity**: MEDIUM
**Description**: No database index on `purchase_date` field despite frequent filtering
**Impact**: Slow queries when filtering by date
**Fix Required**: Add index to `purchase_date` field

### 2.3 Template Issues

#### Issue #PR-T001: Missing Purchase Detail Template Validation
**File**: `pharmacy/templates/pharmacy/purchase_detail.html`
**Severity**: MEDIUM
**Description**: Need to verify template handles empty purchase items correctly
**Fix Required**: Review and add empty state handling

---

## 3. BULK STORE ISSUES

### 3.1 Logical Issues

#### Issue #BS-L001: Incomplete Bulk Store Dashboard
**File**: `pharmacy/views.py`
**Lines**: 1100-1111
**Severity**: MEDIUM
**Description**: Dashboard only shows bulk stores, no inventory statistics
**Current Code**:
```python
def bulk_store_dashboard(request):
    bulk_stores = BulkStore.objects.filter(is_active=True)
    context = {
        'bulk_stores': bulk_stores,
        # Missing: inventory stats, low stock alerts, expiring items
    }
    return render(request, 'pharmacy/bulk_store_dashboard.html', context)
```
**Impact**: Dashboard lacks useful information for inventory management
**Fix Required**: Add inventory statistics, low stock alerts, expiring medications

#### Issue #BS-L002: Missing Bulk Store Inventory Management Views
**File**: `pharmacy/views.py`
**Severity**: HIGH
**Description**: No views for:
- Adding bulk store inventory
- Editing bulk store inventory
- Viewing bulk store inventory details
- Stock adjustments
**Impact**: Cannot manage bulk store inventory through UI
**Fix Required**: Implement complete CRUD operations for bulk store inventory

### 3.2 Integration Issues

#### Issue #BS-I001: Automatic Bulk Store Creation
**File**: `pharmacy/models.py`
**Lines**: 195-209
**Severity**: MEDIUM
**Description**: PurchaseItem automatically creates "Main Bulk Store" if not exists
**Current Code**:
```python
def _add_to_bulk_store(self):
    bulk_store, created = BulkStore.objects.get_or_create(
        name='Main Bulk Store',
        defaults={...}
    )
```
**Impact**: Unexpected bulk store creation, potential data inconsistency
**Fix Required**: Require explicit bulk store selection or configuration

---

## 4. REQUEST & TRANSFER ISSUES

### 4.1 Logical Issues

#### Issue #RT-L001: Missing Expiry Date Validation
**File**: `pharmacy/views.py`
**Lines**: 1300-1348
**Severity**: HIGH
**Description**: `request_medication_transfer` doesn't validate expiry dates
**Current Code**:
```python
# Check if bulk store has sufficient quantity
bulk_inventory = BulkStoreInventory.objects.filter(
    medication=medication,
    bulk_store=bulk_store,
    batch_number=batch_number,
    stock_quantity__gte=quantity
).first()
# No expiry date check!
```
**Impact**: Can transfer expired medications
**Fix Required**: Add expiry date validation before creating transfers

#### Issue #RT-L002: Missing Batch Number Validation
**File**: `pharmacy/views.py`
**Lines**: 1296-1297
**Severity**: MEDIUM
**Description**: Batch number is optional but should be validated if provided
**Impact**: Inconsistent batch tracking
**Fix Required**: Add batch number validation

#### Issue #RT-L003: Inter-Dispensary Transfer Uses Legacy Model
**File**: `pharmacy/inter_dispensary_views.py`
**Lines**: 83-96, 285-288, 376-389
**Severity**: HIGH
**Description**: Uses `MedicationInventory` (legacy) instead of `ActiveStoreInventory`
**Current Code**:
```python
source_inventory = MedicationInventory.objects.get(
    medication=transfer.medication,
    dispensary=transfer.from_dispensary
)
```
**Impact**: Inconsistent with new inventory system, potential data issues
**Fix Required**: Migrate to use ActiveStoreInventory or provide compatibility layer

#### Issue #RT-L004: Missing Import in Inter-Dispensary Views
**File**: `pharmacy/inter_dispensary_views.py`
**Lines**: 280
**Severity**: CRITICAL
**Description**: `Medication` model not imported but used in line 280
**Current Code**:
```python
medication = Medication.objects.get(id=medication_id)  # ← Medication not imported!
```
**Impact**: Runtime error when checking medication inventory
**Fix Required**: Add `from .models import Medication` to imports

---

## 5. INTEGRATION ISSUES

### 5.1 Cross-Module Issues

#### Issue #INT-001: Inconsistent Inventory Models
**File**: `pharmacy/models.py`
**Lines**: 299-314, 337-360
**Severity**: HIGH
**Description**: Two inventory systems exist:
- `MedicationInventory` (legacy)
- `ActiveStoreInventory` (new)
**Impact**: Confusion, potential data inconsistency
**Fix Required**: Migrate fully to new system or provide clear migration path

#### Issue #INT-002: Missing Inventory Synchronization
**File**: Multiple
**Severity**: HIGH
**Description**: No automatic sync between BulkStore → ActiveStore → Dispensary
**Impact**: Manual tracking required, prone to errors
**Fix Required**: Implement automatic inventory synchronization

---

## SUMMARY

### Critical Issues (Must Fix): 5
- PR-L001: Incomplete purchase item deletion
- PR-L002: Incomplete purchase approval workflow
- BS-L002: Missing bulk store inventory management
- RT-L004: Missing import in inter-dispensary views

### High Priority Issues: 11
- SM-L001: Supplier list template variable mismatch
- SM-T001: Inconsistent variable names
- PR-L003: Missing purchase item edit function
- PR-L005: Missing dispensary assignment
- BS-L001: Incomplete bulk store dashboard
- RT-L001: Missing expiry date validation
- RT-L003: Inter-dispensary transfer uses legacy model
- INT-001: Inconsistent inventory models
- INT-002: Missing inventory synchronization

### Medium Priority Issues: 8
- SM-L002: Missing status filter implementation
- SM-T002: Missing error handling
- PR-L004: Inefficient total amount calculation
- PR-D001: Missing index on purchase date
- PR-T001: Missing purchase detail template validation
- RT-L002: Missing batch number validation
- BS-I001: Automatic bulk store creation

### Low Priority Issues: 1
- SM-L003: Incorrect page title variable

**Total Issues Identified: 25**

---

## NEXT STEPS

1. Fix all CRITICAL issues first
2. Address HIGH priority issues
3. Implement MEDIUM priority improvements
4. Handle LOW priority issues
5. Add comprehensive testing
6. Update documentation

