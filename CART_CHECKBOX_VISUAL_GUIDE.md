# Pharmacy Cart Checkbox Selection - Visual Guide

## Overview

The pharmacy cart now includes checkbox selection for all transactions, allowing pharmacists to choose specific medications to invoice/dispense.

## Visual Representation

### Active Cart (Fresh Cart)

```
📋 Cart #123 - Patient: John Doe - Status: ACTIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────┐
│  Select Dispensary                                  │
│  ┌───────────────────────────────────────────────┐  │
│  │ [🏥 Main Dispensary - Ground Floor]          ▼│  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘

📊 Cart Items Table

┌──┬────────────────┬──────────┬──────────┬──────────┬────────┐
│✓ │ Medication     │Prescribed│ Quantity │ Unit     │ Stock  │
│  │                │          │          │ Price    │        │
├──┼────────────────┼──────────┼──────────┼──────────┼────────┤
│☑ │ Amoxicillin    │    10    │    10    │ ₦500.00  │ ✅15   │
│  │ 500mg Capsule  │          │          │          │        │
├──┼────────────────┼──────────┼──────────┼──────────┼────────┤
│☑ │ Metformin      │    30    │    30    │ ₦800.00  │ ⚠️ 5   │
│  │ 500mg Tab      │          │          │          │        │
├──┼────────────────┼──────────┼──────────┼──────────┼────────┤
│☑ │ Atorvastatin   │    30    │    30    │ ₦1200.00 │ 🛑 0   │
│  │ 20mg Tab       │          │          │          │        │
└──┴────────────────┴──────────┴──────────┴──────────┴────────┘

✅ = Stock Available   ⚠️ = Low Stock   🛑 = Out of Stock

☑ Checked - included in invoice
☐ Unchecked - excluded (stays in cart)

                           [✓] Auto-Select Available
                           Selects 2 items with stock
```

### Paid Cart (Ready for Dispensing)

```
📋 Cart #123 - Patient: John Doe - Status: PAID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────┐
│  💰 Payment Status: COMPLETED                        │
│  Invoice: INV-2024-001                              │
│  Total Patient Payable: ₦1,850.00                  │
└─────────────────────────────────────────────────────┘

📊 Cart Items Table

┌──┬────────────────┬──────────┬──────────┬────────────┬────────┐
│✓ │ Medication     │Prescribed│To        │ Unit       │ Stock  │
│  │                │          │Dispense  │ Price      │        │
├──┼────────────────┼──────────┼──────────┼────────────┼────────┤
│☑ │ Amoxicillin    │    10    │ [10]     │ ₦500.00    │ ✅  15 │
│  │ 500mg Capsule  │          │          │            │        │
├──┼────────────────┼──────────┼──────────┼────────────┼────────┤
│☑ │ Metformin      │    30    │ [5]      │ ₦800.00    │ ✅   5 │
│  │ 500mg Tab      │          │          │            │        │
└──┴────────────────┴──────────┴──────────┴────────────┴────────┘

✓ All selected items have stock
☐ Unselected items withheld (stays in cart)

[✓] Dispense Selected - 2 items
[✓] Auto-Select Available - Select all with stock
[ℹ] Enter quantities above (defaults to available)
```

## Checkbox States

### Selectable (Has Stock, Not Fully Dispensed)
```
☑ [ ]  Green checkmark + box
- Enabled checkbox
- User can toggle
- Quantity input ENABLED
- Green highlight on select
```

### Disabled (No Stock / Fully Dispensed)
```
🚫   Red ban icon (no checkbox)
- Cannot be selected
- Appears grayed out
- Quantity input DISABLED
- Stays out of current transaction
```

## Action Buttons

### Active Cart (Before Invoice)
```
┌─────────────────────────────────────┐
│ 💡 Ready to Generate Invoice         │
│    Select items and click when ready │
└─────────────────────────────────────┘

[✓] Generate Invoice (Selected Only)
    Creates invoice for CHECKED items only
    Unchecked items remain in cart

[✓] Auto-Select Available
    Checks all items with stock > 0

ℹ️ Select items with checkboxes, leave unchecked to exclude
```

### Paid Cart (Dispensing)
```
[✓] Dispense Selected
    Only dispenses CHECKED items
    Unchecked items remain in cart

[✓] Auto-Select Available
    Checks all items with stock > 0
```

## Visual Feedback Colors

| State | Background | Border | Text Color | Example |
|-------|------------|--------|------------|---------|
| **Selected** | `#f8fff9` (light green) | `#28a745` (green) | Dark green | ☑ Selected row |
| **Disabled** | `#e9ecef` (gray) | `#dee2e6` (gray) | Gray + strikethrough | 🚫 No stock |
| **Default** | `#f8f9fa` (white-gray) | `#dee2e6` (default) | Dark gray | ☐ Unselected |

## User Flow Examples

### Example 1: Partial Cart Generation
```
1. Cart with 5 items: 3 have stock, 2 out of stock
   → Checkboxes: 3 enabled, 2 disabled (ban icon)

2. Click "Auto-Select Available"
   → 3 items checked automatically
   → 2 items remain unchecked (disabled)

3. Click "Generate Invoice (Selected Only)"
   → Confirmation: "Generate invoice for 3 medications?"
   → Processing...

4. Result:
   ✅ 3 items moved to invoiced cart
   ❌ 2 items remain in active cart (for later)
```

### Example 2: Manual Selection
```
1. Cart with 4 items, all have stock
   → All show enabled checkboxes

2. Uncheck item 2 and 4 manually
   → 2 items remain checked

3. Click "Generate Invoice (Selected Only)"
   → Processes only 2 items

4. Result:
   ✅ 2 items invoiced
   ❌ 2 items stay in cart
```

### Example 3: Dispensing Workflow
```
1. Paid cart with 4 items
   → Checkboxes visible

2. Auto-select all 4 (all have stock)
   → All checkboxes checked
   → Quantity inputs show available amounts

3. Adjust quantities:
   - Amoxicillin: 10 → 5 (only give 5)
   - Metformin: 10 → 10 (full amount)
   - Other 2 items: leave at 0 (don't dispense)

4. Click "Dispense Selected"
   → Confirms: "Dispense 2 medications?"
   → Processes only items with quantity > 0

5. Result:
   ✅ 2 items dispensed
   ❌ 2 items remain in cart (unchecked/zero quantity)
```

## Quick Reference

### Keyboard Shortcuts (Not implemented, but logical)
- `Tab`: Move between checkboxes
- `Space`: Toggle checkbox
- `Enter`: Submit current action

### Accessibility
- Checkboxes are focusable via keyboard
- Clear labeling for screen readers
- Color contrast meets WCAG standards
- Focus states visible (green glow)

### Mobile View
- Checkboxes remain visible (scroll horizontally if needed)
- Tap target size: minimum 44x44px
- Responsive layout adjusts to screen size

## Troubleshooting

### "Please select at least one medication checkbox"
**Cause**: User clicked "Generate Invoice" or "Dispense Selected" without checking any boxes
**Solution**: Check at least one checkbox or click "Auto-Select Available"

### Checkbox disabled with red ban icon
**Cause**: Item has no stock or is fully dispensed
**Solution**: These items will be processed when stock arrives or they're added to a new cart

### "If you want to invoice all items, please use Auto-Select Available"
**Cause**: User clicked "Generate Invoice" with no selections
**Solution**: Click "Auto-Select Available" button first

## Benefits in Practice

### Time Savings
- **Before**: Had to dispense all items or create separate carts
- **After**: Select specific items in one cart

### Better Inventory Management
- Can see stock levels before invoicing
- Exclude out-of-stock items from current transaction
- Plan partial dispensing

### Fewer Errors
- Cannot accidentally process items without stock
- Visual feedback prevents mistakes
- Explicit selection required

### Improved Patient Experience
- Can invoice partial items when some are out of stock
- Patients don't wait for all items to be available
- Clear what's included in current invoice
