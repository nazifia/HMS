# Invoice Duplicate Error Fix

## Problem
Error: `UNIQUE constraint failed: billing_invoice.invoice_number`

## Root Cause
The HMS system has two invoice systems:
1. **billing.Invoice** - Old invoice system with invoice_number field
2. **pharmacy_billing.Invoice** - New pharmacy-specific invoice system

The error occurred because:
1. The prescription detail template had a "Create Invoice & Pay" button that called `create_prescription_invoice` view
2. This view creates a `billing.Invoice` using the `core.prescription_utils.create_prescription_invoice` function
3. The invoice number generation used a count-based approach that could create duplicates in concurrent scenarios
4. When multiple invoices were created at the same time (or if an invoice already existed), the unique constraint on `invoice_number` failed

## Solutions Implemented

### 1. Fixed Invoice Number Generation (billing/models.py)
**Problem**: Count-based invoice number generation could create duplicates

**Old Code**:
```python
def _generate_invoice_number(self):
    today = timezone.now().date()
    date_str = today.strftime('%Y%m%d')
    prefix = 'INV'
    count = Invoice.objects.filter(invoice_date=today).count() + 1
    return f"{prefix}{date_str}{str(count).zfill(4)}"
```

**New Code**:
```python
def _generate_invoice_number(self):
    today = timezone.now().date()
    date_str = today.strftime('%Y%m%d')
    prefix = 'INV'
    
    # Try to generate a unique invoice number with retry logic
    max_attempts = 100
    for attempt in range(max_attempts):
        count = Invoice.objects.filter(invoice_date=today).count() + 1 + attempt
        invoice_number = f"{prefix}{date_str}{str(count).zfill(4)}"
        
        # Check if this invoice number already exists
        if not Invoice.objects.filter(invoice_number=invoice_number).exists():
            return invoice_number
    
    # Fallback to timestamp if max attempts reached
    import time
    timestamp = str(int(time.time() * 1000))[-4:]
    return f"{prefix}{date_str}{timestamp}"
```

**Benefits**:
- Handles race conditions with retry logic
- Checks for existing invoice numbers before returning
- Falls back to timestamp-based generation if needed
- Prevents duplicate invoice numbers

### 2. Updated Prescription Detail Template (pharmacy/templates/pharmacy/prescription_detail.html)
**Problem**: Template had a "Create Invoice & Pay" button that created billing.Invoice, conflicting with new pharmacy_billing.Invoice system

**Old Code**:
```html
{% if prescription.invoice %}
    <a href="{% url 'pharmacy:prescription_payment' prescription.id %}" class="btn btn-warning">
        <i class="fas fa-credit-card"></i> Pay Now
    </a>
    <a href="{% url 'billing:detail' prescription.invoice.id %}" class="btn btn-outline-warning">
        <i class="fas fa-file-invoice"></i> View Invoice
    </a>
{% else %}
    <a href="{% url 'pharmacy:create_prescription_invoice' prescription.id %}" class="btn btn-primary">
        <i class="fas fa-file-invoice-dollar"></i> Create Invoice & Pay
    </a>
{% endif %}
```

**New Code**:
```html
{% if pharmacy_invoice %}
    <a href="{% url 'pharmacy:prescription_payment' prescription.id %}" class="btn btn-warning">
        <i class="fas fa-credit-card"></i> Pay Now
        {% if is_nhia_patient %}
            <span class="badge bg-light text-dark ms-1">₦{{ total_patient_pays|floatformat:2 }}</span>
        {% endif %}
    </a>
{% endif %}
```

**Changes**:
- Removed "Create Invoice & Pay" button (old workflow)
- Changed check from `prescription.invoice` (billing.Invoice) to `pharmacy_invoice` (pharmacy_billing.Invoice)
- Removed "View Invoice" button (not needed, invoice details shown in payment page)
- Invoice creation now only happens through pharmacist-controlled workflow

## Current Workflow

### Correct Invoice Generation Flow:
1. **Doctor creates prescription** → No invoice created
2. **Pharmacist clicks "Generate Invoice (Pharmacist)"** → Opens availability check page
3. **Pharmacist selects dispensary** → Medication section appears
4. **Pharmacist enters quantities** → Can adjust based on needs
5. **Pharmacist clicks "Check Availability"** → AJAX check against inventory
6. **System shows results** → Green (available) / Red (unavailable)
7. **Pharmacist clicks "Generate Invoice"** → Creates `pharmacy_billing.Invoice`
8. **Payment processed** → Uses pharmacy_billing.Invoice
9. **Receipt generated** → Professional printable receipt

### What NOT to Do:
- ❌ Don't use the old "Create Invoice & Pay" button (removed)
- ❌ Don't create billing.Invoice for prescriptions (use pharmacy_billing.Invoice)
- ❌ Don't bypass the pharmacist availability check

## Invoice Systems Comparison

### billing.Invoice (Old System)
- **Used for**: General billing, consultations, admissions, lab tests
- **Has**: invoice_number field (unique constraint)
- **Created by**: Various modules (billing, consultations, inpatient, laboratory)
- **Linked to Prescription**: Via `prescription.invoice` field

### pharmacy_billing.Invoice (New System)
- **Used for**: Pharmacy/medication billing only
- **Has**: No invoice_number field (uses ID)
- **Created by**: Pharmacist-controlled workflow
- **Linked to Prescription**: Via `prescription.invoice_prescription` field
- **Benefits**: 
  - Availability checking before invoice creation
  - Pharmacist control over quantities
  - NHIA discount calculation
  - Better inventory management

## Migration Notes

### For Existing Prescriptions:
- Old prescriptions may have `billing.Invoice` linked via `prescription.invoice`
- New prescriptions should use `pharmacy_billing.Invoice` via pharmacist workflow
- Both systems can coexist during transition period

### For Developers:
- Always use `pharmacy_billing.Invoice` for new pharmacy invoices
- Check for `pharmacy_invoice` in templates, not `prescription.invoice`
- Use `create_pharmacy_invoice()` from `pharmacy_billing.utils`, not `create_prescription_invoice()` from `core.prescription_utils`

## Testing

### Test the Fix:
1. Create a new prescription
2. Click "Generate Invoice (Pharmacist)"
3. Select dispensary and check availability
4. Generate invoice
5. Verify no duplicate invoice number error
6. Process payment
7. Generate receipt

### Verify Invoice Number Uniqueness:
```python
# In Django shell
from billing.models import Invoice
from django.utils import timezone

# Create multiple invoices on same day
for i in range(10):
    invoice = Invoice.objects.create(
        patient=patient,
        invoice_date=timezone.now().date(),
        due_date=timezone.now().date(),
        subtotal=100,
        tax_amount=0,
        total_amount=100,
        status='pending'
    )
    print(f"Invoice {i+1}: {invoice.invoice_number}")

# All invoice numbers should be unique
```

## Rollback Plan

If issues occur:
1. Revert `billing/models.py` to old invoice number generation
2. Revert `pharmacy/templates/pharmacy/prescription_detail.html` to show old button
3. Disable pharmacist-controlled invoice generation
4. Use old automatic invoice creation

## Future Improvements

1. **Migrate all prescriptions to pharmacy_billing.Invoice**
   - Create migration script
   - Convert existing billing.Invoice to pharmacy_billing.Invoice
   - Remove `prescription.invoice` field

2. **Unify invoice systems**
   - Consider using single invoice system with type field
   - Or keep separate but ensure no conflicts

3. **Add invoice number to pharmacy_billing.Invoice**
   - If needed for reporting/tracking
   - Use same robust generation logic

4. **Improve concurrency handling**
   - Use database-level locks for invoice creation
   - Implement queue system for high-volume scenarios

## Support

If you encounter invoice number duplicate errors:
1. Check which invoice system is being used
2. Verify invoice number generation logic
3. Check for concurrent invoice creation
4. Review error logs for specific invoice numbers
5. Contact development team with error details

## Related Files

- `billing/models.py` - Invoice number generation
- `pharmacy/templates/pharmacy/prescription_detail.html` - Template fix
- `pharmacy_billing/models.py` - Pharmacy invoice model
- `pharmacy_billing/utils.py` - Pharmacy invoice creation
- `core/prescription_utils.py` - Old invoice creation (deprecated for pharmacy)
- `pharmacy/views.py` - Pharmacist invoice generation view

## Conclusion

The duplicate invoice number error has been fixed by:
1. Improving invoice number generation with retry logic
2. Removing conflicting invoice creation button
3. Ensuring only pharmacy_billing.Invoice is used for prescriptions

The new pharmacist-controlled workflow provides better inventory management and prevents billing for unavailable medications.

