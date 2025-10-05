# User Guide: Prescription Invoice and Payment Receipt System

## Quick Start Guide

### For Doctors

#### Creating a Prescription
1. Navigate to **Pharmacy → Create Prescription**
2. Select patient
3. Add medications with dosage, frequency, and duration
4. Save prescription
5. **Note:** Invoice is NOT created automatically - pharmacist will generate it after checking availability

### For Pharmacists

#### Generating Invoice After Availability Check
1. Open the prescription from the prescription list
2. Click **"Generate Invoice (Pharmacist)"** button
3. Review the availability check page showing:
   - All prescribed medications
   - Stock levels in each dispensary
   - Color-coded status:
     - 🟢 **Green (Sufficient)** - Enough stock available
     - 🟡 **Yellow (Insufficient)** - Some stock but not enough
     - 🔴 **Red (Out of Stock)** - No stock available
4. Select the dispensary with best availability
5. Click **"Generate Invoice"**
6. System will:
   - Create invoice for available medications only
   - Exclude unavailable medications
   - Calculate correct amount based on NHIA status
   - Show success message with details

#### Important Notes for Pharmacists
- Only medications with sufficient stock will be included in the invoice
- Patient will only be charged for available medications
- NHIA patients automatically get 10% pricing
- You can see which medications were excluded in the success message

### For Billing Office Staff

#### Processing Payments
1. Navigate to prescription detail page
2. Click **"Billing Office Payment"** or **"Patient Wallet Payment"**
3. Enter payment details:
   - Amount (can be partial payment)
   - Payment method (Cash, Card, Transfer, etc.)
   - Transaction ID (if applicable)
   - Notes (optional)
4. Click **"Record Payment"**
5. Payment is recorded and receipt is available

#### Generating Payment Receipts
1. After payment is recorded, go to payment history
2. Find the payment in the list
3. Click **"Receipt"** button
4. Receipt opens in new tab
5. Click **"Print"** button or use Ctrl+P to print

### For All Users

#### Viewing Payment History
**Pharmacy Payments:**
- Go to Prescription Detail → Payment section
- View all payments made for the prescription
- Each payment has a "Receipt" button

**Laboratory Payments:**
- Go to Test Request Detail → Payment History
- View all payments for the test
- Click "Receipt" for any payment

**Consultation Payments:**
- Similar process through consultation detail page

**Admission Payments:**
- Similar process through admission detail page

## Receipt Information

### What's Included in a Receipt
- **Hospital Information:** Name, address, contact details
- **Receipt Number:** Unique identifier (e.g., PH-123, LAB-456)
- **Patient Information:** Name, ID, insurance status
- **Service Details:** What was paid for
- **Itemized Breakdown:** Individual items with quantities and prices
- **Payment Information:** Method, transaction ID, received by
- **Amount Summary:** Subtotal, tax, discount, total, amount paid, balance
- **Signature Sections:** For patient and authorized personnel
- **Official Stamp Area:** For hospital stamp

### Receipt Types and Numbering
- **Pharmacy:** PH-{payment_id}
- **Laboratory:** LAB-{payment_id}
- **Consultation:** CONS-{payment_id}
- **Admission:** ADM-{payment_id}

## NHIA Patient Handling

### Automatic NHIA Detection
- System automatically detects NHIA patients
- Shows NHIA badge on prescription detail page
- Calculates 10% patient payment automatically

### NHIA Invoice Generation
When pharmacist generates invoice for NHIA patient:
- System calculates total medication cost
- Patient pays only 10%
- NHIA covers 90%
- Invoice clearly shows breakdown
- Receipt indicates NHIA status

### Example
- Medication total cost: ₦10,000
- NHIA patient pays: ₦1,000 (10%)
- NHIA covers: ₦9,000 (90%)
- Invoice amount: ₦1,000

## Common Scenarios

### Scenario 1: All Medications Available
1. Doctor prescribes 3 medications
2. Pharmacist checks availability - all available in Dispensary A
3. Pharmacist selects Dispensary A and generates invoice
4. Invoice includes all 3 medications
5. Patient pays full amount
6. Receipt generated with all items

### Scenario 2: Partial Availability
1. Doctor prescribes 3 medications
2. Pharmacist checks availability:
   - Medication A: Available in Dispensary A
   - Medication B: Available in Dispensary A
   - Medication C: Out of stock everywhere
3. Pharmacist selects Dispensary A and generates invoice
4. Invoice includes only Medications A and B
5. System shows message: "2 medications included, 1 unavailable"
6. Patient pays for available medications only
7. Doctor can be notified about unavailable medication

### Scenario 3: NHIA Patient with Partial Availability
1. Doctor prescribes medications worth ₦10,000 total
2. Only ₦8,000 worth of medications available
3. Pharmacist generates invoice
4. NHIA patient pays 10% of ₦8,000 = ₦800
5. Invoice shows NHIA discount
6. Receipt indicates NHIA status

### Scenario 4: Partial Payment
1. Invoice total: ₦5,000
2. Patient pays ₦3,000 first
3. Receipt generated for ₦3,000 payment
4. Balance: ₦2,000
5. Patient pays ₦2,000 later
6. Second receipt generated for ₦2,000 payment
7. Both receipts available in payment history

## Troubleshooting

### Invoice Not Generated
**Problem:** "Generate Invoice" button not showing
**Solution:** Check if invoice already exists. If yes, use existing invoice.

### No Medications Available
**Problem:** All medications out of stock
**Solution:** 
1. Check other dispensaries
2. Request stock transfer from bulk store
3. Inform doctor to modify prescription
4. Order medications from supplier

### Receipt Not Printing
**Problem:** Receipt doesn't print properly
**Solution:**
1. Use Chrome or Edge browser
2. Check printer settings
3. Ensure "Print background graphics" is enabled
4. Try "Save as PDF" first

### Wrong Amount on Receipt
**Problem:** Receipt shows incorrect amount
**Solution:**
1. Verify payment was recorded correctly
2. Check if NHIA discount was applied correctly
3. Contact billing office to verify
4. May need to void and re-record payment

## Best Practices

### For Pharmacists
1. Always check availability before generating invoice
2. Select dispensary with best stock levels
3. Inform patients about unavailable medications
4. Coordinate with bulk store for stock transfers
5. Keep dispensary inventory updated

### For Billing Staff
1. Always generate receipt after payment
2. Verify payment amount before recording
3. Keep transaction IDs for card/transfer payments
4. Print receipt for patient records
5. File receipts properly

### For All Staff
1. Verify patient identity before processing
2. Check NHIA status before payment
3. Explain charges to patients clearly
4. Keep receipts for audit purposes
5. Report system issues immediately

## Keyboard Shortcuts

- **Ctrl+P:** Print receipt
- **Ctrl+S:** Save receipt as PDF
- **Esc:** Close receipt window

## Support

For technical issues or questions:
- Contact IT Support
- Email: support@hospital.com
- Phone: Extension 1234

For billing questions:
- Contact Billing Office
- Extension 5678

## Updates and Changes

This system replaces the old automatic invoice generation system. Key changes:
- Invoices now generated by pharmacist after availability check
- Receipts now available for all payment types
- Better inventory management
- Improved patient experience
- Reduced billing disputes

## Feedback

We welcome your feedback to improve this system. Please report:
- Bugs or errors
- Confusing workflows
- Missing features
- Improvement suggestions

Contact: development@hospital.com

