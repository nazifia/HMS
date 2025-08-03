# HMS Error Fixes Documentation

This document describes the errors that were encountered and how they were fixed.

## Errors Fixed

### 1. InvoiceItem() got unexpected keyword arguments: 'total_price'

**Error Description:**
```
InvoiceItem() got unexpected keyword arguments: 'total_price'
```

**Root Cause:**
In `pharmacy/views.py` at line 2030, there was an `InvoiceItem.objects.create()` call that used `total_price` as a parameter, but the `InvoiceItem` model in `billing/models.py` has a field called `total_amount`, not `total_price`.

**Files Affected:**
- `pharmacy/views.py` (line 2030)

**Fix Applied:**
Changed the InvoiceItem creation from:
```python
InvoiceItem.objects.create(
    invoice=invoice,
    service=medication_dispensing_service,
    description=f'{prescription_item.medication.name} - {prescription_item.dosage} ({prescription_item.quantity} units)',
    quantity=prescription_item.quantity,
    unit_price=prescription_item.medication.price,
    total_price=item_total  # ❌ Wrong field name
)
```

To:
```python
InvoiceItem.objects.create(
    invoice=invoice,
    service=medication_dispensing_service,
    description=f'{prescription_item.medication.name} - {prescription_item.dosage} ({prescription_item.quantity} units)',
    quantity=prescription_item.quantity,
    unit_price=prescription_item.medication.price,
    tax_percentage=Decimal('0.00'),
    tax_amount=Decimal('0.00'),
    discount_amount=Decimal('0.00'),
    total_amount=item_total  # ✅ Correct field name with required fields
)
```

### 2. NOT NULL constraint failed: core_internalnotification.user_id

**Error Description:**
```
NOT NULL constraint failed: core_internalnotification.user_id
```

**Root Cause:**
The `InternalNotification` model requires a `user` field (ForeignKey with `on_delete=models.CASCADE`), but in several places in the code, notifications were being created with `user=None` or with potentially null user references.

**Files Affected:**
- `accounts/views.py` (line 642)
- `billing/views.py` (lines 110, 293, 876)

**Fixes Applied:**

#### Fix 1: accounts/views.py
Changed from creating a system-wide notification with `user=None` to notifying all superusers:
```python
# Before (❌ Incorrect)
InternalNotification.objects.create(
    user=None,  # System-wide
    message=f"Bulk user action '{action}' performed by {request.user.username}."
)

# After (✅ Correct)
superusers = CustomUser.objects.filter(is_superuser=True)
for superuser in superusers:
    InternalNotification.objects.create(
        user=superuser,
        message=f"Bulk user action '{action}' performed by {request.user.username}."
    )
```

#### Fix 2: billing/views.py (Invoice creation)
Added null check for `invoice.created_by`:
```python
# Before (❌ Potential null reference)
InternalNotification.objects.create(
    user=invoice.created_by,
    message=f"Invoice {invoice.invoice_number} created for {invoice.patient.get_full_name()}"
)

# After (✅ Safe with null check)
if invoice.created_by:
    InternalNotification.objects.create(
        user=invoice.created_by,
        message=f"Invoice {invoice.invoice_number} created for {invoice.patient.get_full_name()}"
    )
```

#### Fix 3: billing/views.py (Payment recording)
Added null check for `invoice.created_by`:
```python
# Before (❌ Potential null reference)
InternalNotification.objects.create(
    user=invoice.created_by,
    message=f"Payment of ₦{payment.amount:.2f} recorded for invoice {invoice.invoice_number} via {payment_source}"
)

# After (✅ Safe with null check)
if invoice.created_by:
    InternalNotification.objects.create(
        user=invoice.created_by,
        message=f"Payment of ₦{payment.amount:.2f} recorded for invoice {invoice.invoice_number} via {payment_source}"
    )
```

#### Fix 4: billing/views.py (Admission payment)
Improved user selection logic to ensure a valid user is always used:
```python
# Before (❌ Potential null reference)
InternalNotification.objects.create(
    user=admission.patient.primary_doctor if hasattr(admission.patient, 'primary_doctor') else request.user,
    message=f"Payment of ₦{payment.amount:.2f} recorded for admission {admission.id} via {payment_source}"
)

# After (✅ Safe with proper fallback logic)
notification_user = request.user
if hasattr(admission.patient, 'primary_doctor') and admission.patient.primary_doctor:
    notification_user = admission.patient.primary_doctor
elif hasattr(admission, 'attending_doctor') and admission.attending_doctor:
    notification_user = admission.attending_doctor

InternalNotification.objects.create(
    user=notification_user,
    message=f"Payment of ₦{payment.amount:.2f} recorded for admission {admission.id} via {payment_source}"
)
```

## Verification

After applying all fixes:

1. **System Check**: ✅ `python manage.py check` - No issues found
2. **Daily Charges Command**: ✅ `python manage.py daily_admission_charges --dry-run` - Working correctly
3. **Feature Tests**: ✅ `python test_new_features.py` - All tests passed

## Prevention Measures

To prevent similar issues in the future:

### For InvoiceItem Field Issues:
1. Always refer to the model definition when creating instances
2. Use IDE auto-completion to avoid field name errors
3. Consider creating helper methods for common InvoiceItem creation patterns

### For InternalNotification User Issues:
1. Always check if user references are not None before creating notifications
2. Implement fallback logic for user selection
3. Consider creating a helper function for safe notification creation:

```python
def create_safe_notification(user, message):
    """Create notification only if user is not None"""
    if user:
        InternalNotification.objects.create(user=user, message=message)
```

### 3. 'NoneType' object has no attribute 'email'

**Error Description:**
```
'NoneType' object has no attribute 'email'
```

**Root Cause:**
Email sending code was trying to access the `.email` attribute on user objects that could be `None` or might not have an email attribute.

**Files Affected:**
- `billing/views.py` (lines 117, 304)
- `laboratory/views.py` (line 831)

**Fixes Applied:**
Added null and attribute checks before accessing email:
```python
# Before (❌ Potential null reference)
send_notification_email(
    subject="...",
    message="...",
    recipient_list=[user.email]
)

# After (✅ Safe with checks)
if user and hasattr(user, 'email') and user.email:
    send_notification_email(
        subject="...",
        message="...",
        recipient_list=[user.email]
    )
```

### 4. BaseModelForm.__init__() got unexpected keyword argument 'invoice'

**Error Description:**
```
TypeError: BaseModelForm.__init__() got an unexpected keyword argument 'invoice'
```

**Root Cause:**
The `PrescriptionPaymentForm` was being initialized with `invoice`, `prescription`, and `patient_wallet` parameters, but its `__init__` method didn't accept these parameters.

**Files Affected:**
- `pharmacy/forms.py` (PrescriptionPaymentForm class)

**Fix Applied:**
Enhanced the form's `__init__` method to accept and handle custom parameters:
```python
def __init__(self, *args, **kwargs):
    # Extract custom parameters
    self.invoice = kwargs.pop('invoice', None)
    self.prescription = kwargs.pop('prescription', None)
    self.patient_wallet = kwargs.pop('patient_wallet', None)

    super().__init__(*args, **kwargs)

    # Set payment method choices
    from billing.models import Payment
    self.fields['payment_method'].choices = Payment.PAYMENT_METHOD_CHOICES

    # Add payment source field if wallet is available
    if self.patient_wallet:
        # Add payment source field and wallet balance info
        # Set initial amount if invoice is provided
```

## Summary

All four errors were related to data integrity and form initialization issues:
1. Field name mismatch in InvoiceItem creation
2. NOT NULL constraint violations in InternalNotification
3. Null reference errors when accessing email attributes
4. Form initialization with unexpected parameters

The fixes ensure that:
1. Correct field names are used when creating InvoiceItem instances
2. InternalNotification instances are only created with valid user references
3. Email sending code safely handles null users and missing email attributes
4. Forms properly accept and handle custom initialization parameters
5. Proper fallback logic is in place for user selection

All new features continue to work correctly after these fixes.
