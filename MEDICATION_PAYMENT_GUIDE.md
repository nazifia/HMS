# 💊 How to Make Payment for Prescribed Medications - Complete Guide

## Overview
This guide explains how to process payments for prescribed medications in the HMS system using the **dual-source payment system**. Payments can be made from either the **pharmacy** or **billing office** and are recorded/considered accordingly across the system.

## 🔄 Dual-Source Payment Workflow

### Payment Sources Available
1. **Pharmacy Interface** - Patient wallet-focused payments
2. **Billing Office Interface** - Professional payment processing with dual options

### Step 1: Prescription Creation → Invoice Generation
1. **Doctor creates prescription** for patient
2. **System automatically generates invoice** in `pharmacy_billing` app
3. **Invoice status**: Initially set to `'pending'`
4. **Prescription payment_status**: Initially set to `'unpaid'`
5. **Dispensing**: Blocked until payment is completed

### Step 2: Locate and Access Payment Options

#### Payment Source Options:

**Option A: Pharmacy Interface (Patient Wallet Focused)**
1. Navigate to **Pharmacy → Prescriptions**
2. Click **View** on the prescription
3. Click **"Patient Wallet Payment"** button
4. Process payment through pharmacy interface

**Option B: Billing Office Interface (Dual-Source)**
1. Navigate to **Pharmacy → Prescriptions**
2. Click **View** on the prescription
3. Click **"Billing Office Payment"** button
4. Choose between:
   - Direct payment (cash/card/bank transfer)
   - Patient wallet payment

**Option C: From Billing System**
1. Navigate to **Billing → Invoices**
2. Look for invoices with **Source**: "Pharmacy"
3. Filter by **Status**: "Pending" or "Partially Paid"
4. Click **"Record Payment"** button

**Option D: Direct Invoice Access**
1. Navigate to **Billing → Invoice Detail** (if you have invoice ID)
2. Click **"Record Payment"** button

## 💳 Payment Methods Available

The system supports multiple payment methods:

- **Cash** - Physical cash payment
- **Credit Card** - Credit card payment
- **Debit Card** - Debit card payment
- **UPI** - Unified Payments Interface
- **Net Banking** - Online banking transfer
- **Insurance** - Insurance coverage
- **Wallet** - Patient wallet (if available)
- **Other** - Other payment methods

## 📝 Step-by-Step Payment Process

### Step 1: Access Payment Form
1. Click **"Record Payment"** or **"Pay Invoice"** button
2. System opens payment form with:
   - **Pre-filled amount**: Remaining balance
   - **Payment date**: Current date
   - **Payment method**: Default to 'cash'

### Step 2: Fill Payment Details
```
Payment Amount: [Auto-filled with remaining balance]
Payment Method: [Select from dropdown]
Payment Date: [Current date or select date]
Transaction ID: [Optional - for card/online payments]
Notes: [Optional - any additional information]
```

### Step 3: Submit Payment
1. **Verify payment amount** (cannot exceed remaining balance)
2. **Select appropriate payment method**
3. **Add transaction ID** (if applicable)
4. **Click "Record Payment"**

### Step 4: System Processing
1. **Payment record created** in database
2. **Invoice amount_paid updated**
3. **Invoice status updated** (paid/partially_paid)
4. **Prescription payment_status updated** to 'paid'
5. **Notifications sent** to relevant staff
6. **Audit log created** for tracking

## 🎯 Payment Scenarios

### Scenario 1: Full Payment
- **Amount**: Full invoice total
- **Result**: Invoice status → 'paid'
- **Effect**: Prescription becomes dispensable immediately

### Scenario 2: Partial Payment
- **Amount**: Less than invoice total
- **Result**: Invoice status → 'partially_paid'
- **Effect**: Prescription remains non-dispensable until full payment

### Scenario 3: Wallet Payment
- **Method**: Patient wallet
- **Process**: Automatic deduction from patient wallet
- **Validation**: Checks wallet balance before processing

### Scenario 4: Insurance Payment
- **Method**: Insurance
- **Process**: Records insurance as payment method
- **Follow-up**: May require insurance verification

## 🔍 Verification & Tracking

### After Payment Submission:
1. **Success message** displayed
2. **Invoice detail page** shows updated payment status
3. **Payment history** visible in invoice details
4. **Prescription status** automatically updated
5. **Dispensing becomes available**

### Payment Verification:
- **Invoice Detail Page**: Shows all payments made
- **Payment History**: Lists all payment transactions
- **Balance Calculation**: Automatically calculates remaining balance
- **Status Updates**: Real-time status updates across system

## 🚨 Important Notes

### Payment Validation:
- ✅ **Cannot exceed remaining balance**
- ✅ **Must be positive amount**
- ✅ **Payment date cannot be future date**
- ✅ **Wallet payments allow negative balances**

### System Integration:
- ✅ **Automatic prescription status update**
- ✅ **Real-time dispensing availability**
- ✅ **Audit trail for all transactions**
- ✅ **Notification system for stakeholders**

### Security Features:
- ✅ **User authentication required**
- ✅ **Payment amount validation**
- ✅ **Transaction logging**
- ✅ **Role-based access control**

## 🔗 Navigation URLs

### Key System URLs:
- **Prescription List**: `/pharmacy/prescriptions/`
- **Invoice List**: `/billing/invoices/`
- **Record Payment**: `/billing/invoices/{invoice_id}/payment/`
- **Invoice Detail**: `/billing/invoices/{invoice_id}/`

## 📊 Payment Status Indicators

### Visual Indicators:
- 🔴 **Red Badge**: "Payment Required" - Unpaid
- 🟡 **Yellow Badge**: "Payment Pending" - Partially paid
- 🟢 **Green Badge**: "Payment Completed" - Fully paid
- 🔵 **Blue Badge**: "Payment Waived" - No payment required

## 🛠️ Troubleshooting

### Common Issues:

#### Issue: "Payment amount exceeds remaining balance"
- **Solution**: Check current balance and enter correct amount

#### Issue: "Wallet payment processing error"
- **Solution**: Check network connection and try again

#### Issue: "Invoice already paid"
- **Solution**: Check payment history, invoice may be fully paid

#### Issue: "Cannot find invoice"
- **Solution**: Verify prescription has associated invoice

## 📞 Support

For technical issues or questions:
1. **Check audit logs** for payment history
2. **Verify user permissions** for billing operations
3. **Contact system administrator** for technical support
4. **Review payment documentation** for detailed procedures

## 🖥️ Practical Step-by-Step Demo

### Method 1: Payment from Prescription Page

#### Step 1: Navigate to Prescription
```
URL: /pharmacy/prescriptions/
1. Login as billing officer
2. Go to "Pharmacy" → "Prescriptions"
3. Find the prescription needing payment
4. Look for payment status indicator:
   🔴 "Payment Required" or 🟡 "Payment Pending"
```

#### Step 2: Access Payment
```
1. Click "View" button on prescription
2. In prescription detail page, look for:
   - Payment Status section with red/yellow badge
   - "Pay Invoice #[ID]" button (if unpaid)
3. Click "Pay Invoice" or "Complete Payment" button
```

#### Step 3: Payment Form
```
URL: /billing/payment/{invoice_id}/
Form displays:
┌─────────────────────────────────────────┐
│ Record Payment for Invoice #12345       │
├─────────────────────────────────────────┤
│ Invoice Information:                    │
│ • Invoice Number: #12345                │
│ • Date: January 15, 2025               │
│ • Patient: John Doe (P001)             │
│                                         │
│ Payment Summary:                        │
│ • Total Amount: ₦5,000.00              │
│ • Amount Paid: ₦0.00                   │
│ • Balance Due: ₦5,000.00               │
│                                         │
│ Payment Details:                        │
│ Amount: [5000.00] (pre-filled)         │
│ Method: [Cash ▼] (dropdown)            │
│ Date: [2025-01-15] (today)             │
│ Transaction ID: [Optional]              │
│ Notes: [Optional]                       │
│                                         │
│ [Record Payment] [Cancel]               │
└─────────────────────────────────────────┘
```

### Method 2: Payment from Billing System

#### Step 1: Navigate to Billing
```
URL: /billing/
1. Go to "Billing" → "Invoices"
2. Filter by:
   - Status: "Pending" or "Partially Paid"
   - Source: "Pharmacy" (for medication invoices)
3. Look for invoices with balance due > 0
```

#### Step 2: Record Payment
```
1. Find the medication invoice
2. Click "Record Payment" button
3. Same payment form opens as Method 1
```

### Method 3: Direct Invoice Access

#### Step 1: Direct URL
```
URL: /billing/{invoice_id}/
1. If you have the invoice ID
2. Navigate directly to invoice detail
3. Click "Record Payment" button
```

## 💡 Payment Form Field Details

### Payment Amount Field:
```
Input: Number field with validation
- Pre-filled with remaining balance
- Cannot exceed remaining amount
- Must be greater than 0
- Supports decimal values (₦0.01 minimum)
```

### Payment Method Dropdown:
```
Options:
• Cash (default)
• Credit Card
• Debit Card
• UPI
• Net Banking
• Insurance
• Wallet
• Other
```

### Transaction ID Field:
```
Input: Text field (optional)
- Required for: Card payments, bank transfers
- Optional for: Cash, wallet payments
- Examples: "TXN123456", "CHQ001", "REF789"
```

### Notes Field:
```
Input: Textarea (optional)
- Additional payment information
- Special instructions
- Reference details
```

## 🔄 Real-Time System Updates

### After Successful Payment:

#### Immediate Updates:
1. **Payment Record Created**
   ```
   Payment ID: PAY-2025-001
   Amount: ₦5,000.00
   Method: Cash
   Status: Completed
   ```

2. **Invoice Status Updated**
   ```
   Before: Status = "Pending", Amount Paid = ₦0.00
   After:  Status = "Paid", Amount Paid = ₦5,000.00
   ```

3. **Prescription Status Updated**
   ```
   Before: payment_status = "unpaid"
   After:  payment_status = "paid"
   ```

4. **Dispensing Enabled**
   ```
   Before: Dispense button disabled/locked
   After:  Dispense button active and clickable
   ```

#### Notifications Sent:
- ✅ Success message to billing officer
- ✅ Email notification to invoice creator
- ✅ Internal notification to pharmacy staff
- ✅ Audit log entry created

## 📱 Mobile-Friendly Interface

The payment system is responsive and works on:
- 💻 Desktop computers
- 📱 Tablets
- 📱 Mobile phones
- 🖥️ Touch screen kiosks

---

## Quick Reference Card

### Payment Process Summary:
1. **Find Invoice** → Pharmacy prescriptions or Billing invoices
2. **Click "Record Payment"** → Opens payment form
3. **Fill Details** → Amount, method, date, transaction ID
4. **Submit Payment** → System processes and updates status
5. **Verify Success** → Check invoice status and prescription dispensability

### Payment Methods Quick List:
- Cash, Credit/Debit Card, UPI, Net Banking
- Insurance, Wallet, Other

### Key Validation Rules:
- Amount ≤ Remaining Balance
- Amount > 0
- Payment Date ≤ Today
- Wallet payments allow negative balances (no minimum balance requirement)
