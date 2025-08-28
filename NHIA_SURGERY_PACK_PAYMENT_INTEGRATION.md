# NHIA Patient 10% Payment Integration for Surgery Packs

## Overview

This document describes the implementation of the 10% payment system for NHIA patients for surgery packs in the Hospital Management System (HMS). The integration ensures that NHIA patients pay only 10% of the cost of medical packs used in surgeries, while the remaining 90% is covered by the NHIA scheme.

## Implementation Details

### 1. Patient Identification

NHIA patients are identified by the `patient_type` field in the [Patient](file://c:\Users\dell\Desktop\MY_PRODUCTS\HMS\patients\models.py#L7-L130) model:
- `patient_type = 'nhia'` for NHIA patients
- `patient_type = 'regular'` for regular patients

### 2. Pricing Logic

The pricing logic is implemented in the [_add_pack_to_surgery_invoice](file://c:\Users\dell\Desktop\MY_PRODUCTS\HMS\theatre\views.py#L1015-L1077) function in `theatre/views.py`:

```python
# Calculate pack cost with NHIA discount if applicable
pack_cost = pack_order.pack.get_total_cost()

# Apply 10% payment for NHIA patients (they pay 10%, NHIA covers 90%)
if surgery.patient.patient_type == 'nhia':
    pack_cost = pack_cost * Decimal('0.10')  # NHIA patients pay 10%
```

### 3. Invoice Creation

When a medical pack is ordered for a surgery, the system automatically:
1. Creates a prescription from the pack items
2. Adds the pack cost to the surgery invoice
3. Applies the 10% discount for NHIA patients

### 4. Billing Interface

The billing interface in `billing/views.py` has been enhanced to:
- Display NHIA patient status prominently
- Show original pack costs and discounted amounts for NHIA patients
- Calculate total savings for NHIA patients
- Provide clear breakdown of costs

### 5. Template Updates

The surgery billing template (`billing/templates/billing/surgery_billing.html`) now:
- Shows an NHIA badge for NHIA patients
- Displays original costs vs. patient portion
- Shows the discount amount for NHIA patients
- Provides a clear breakdown of all costs

## Key Features

### 1. Automatic Patient Type Detection
The system automatically detects NHIA patients based on their `patient_type` field and applies the appropriate pricing.

### 2. Transparent Pricing
Patients and staff can clearly see:
- Original pack costs
- Discounted amounts for NHIA patients
- Total savings for NHIA patients

### 3. Consistent Integration
The implementation works seamlessly with existing:
- Theatre scheduling system
- Pharmacy pack ordering system
- Billing and payment system
- Invoice generation system

### 4. Audit Trail
All pricing decisions are clearly documented in:
- Invoice descriptions
- Audit logs
- Payment records

## Testing

A comprehensive test script (`test_nhia_surgery_pack_payment.py`) has been created to verify:
1. NHIA patient identification
2. 10% payment calculation
3. Regular patient full payment
4. Invoice creation with correct pricing
5. Integration between all modules

## Benefits

### For NHIA Patients
- Clear indication of their NHIA status
- Transparent pricing with visible discounts
- Reduced financial burden (90% savings)

### For Hospital Staff
- Automatic pricing calculations
- Clear visual indicators for NHIA patients
- Detailed cost breakdowns
- Reduced billing errors

### For Administration
- Compliance with NHIA regulations
- Accurate financial reporting
- Audit trail for all transactions
- Integration with existing systems

## Usage Instructions

### For Theatre Staff
1. When ordering a medical pack for a surgery, the system automatically detects if the patient is an NHIA patient
2. The correct pricing (10% for NHIA, 100% for regular) is automatically applied
3. An invoice item is created with the appropriate cost

### For Billing Staff
1. When viewing surgery billing, NHIA patients are clearly marked
2. Original costs and patient portions are displayed separately
3. The total discount amount is shown for NHIA patients
4. Payments can be processed normally, with the system using the discounted amounts

### For Administrators
1. Reports will show accurate revenue figures based on actual payments received
2. NHIA-related discounts are clearly documented
3. Compliance with NHIA pricing regulations is maintained

## Technical Implementation

### Modified Files
1. `theatre/views.py` - Updated [_add_pack_to_surgery_invoice](file://c:\Users\dell\Desktop\MY_PRODUCTS\HMS\theatre\views.py#L1015-L1077) function
2. `billing/views.py` - Enhanced [surgery_billing](file://c:\Users\dell\Desktop\MY_PRODUCTS\HMS\billing\views.py#L488-L627) view
3. `billing/templates/billing/surgery_billing.html` - Updated template

### Key Functions
1. `_add_pack_to_surgery_invoice()` - Applies NHIA discount during invoice creation
2. `surgery_billing()` - Displays NHIA pricing information
3. Template rendering - Shows clear pricing breakdown

## Future Enhancements

1. Integration with NHIA authorization codes for additional verification
2. Automated reporting on NHIA patient savings
3. Enhanced audit logging for compliance purposes
4. Mobile-friendly billing interface

## Support

For technical issues or questions:
1. Check the audit logs for pricing decisions
2. Verify patient type in the patient record
3. Contact system administrator for technical support
4. Review this documentation for detailed procedures