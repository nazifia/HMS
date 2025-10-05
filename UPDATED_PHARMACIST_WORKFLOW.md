# Updated Pharmacist Invoice Generation Workflow

## Overview
The pharmacist invoice generation system has been enhanced to provide an interactive, real-time availability checking workflow. Pharmacists can now input custom quantities, check availability dynamically, and make adjustments before generating invoices.

## Key Features

### 1. Interactive Quantity Input
- Pharmacists can modify the quantity to dispense for each medication
- Quantities are pre-filled with prescribed amounts
- System validates that quantities don't exceed prescribed amounts
- Real-time calculation of item totals as quantities change

### 2. Real-Time Availability Checking
- AJAX-based availability checking without page reload
- Instant feedback on stock levels
- Color-coded visual indicators:
  - **Green**: Medication available in sufficient quantity
  - **Red**: Medication not available or insufficient stock
- Shows exact stock levels vs. required quantities

### 3. Dynamic Invoice Calculation
- Automatic calculation of subtotals
- NHIA discount calculation (90% discount, patient pays 10%)
- Summary showing:
  - Number of available medications
  - Number of unavailable medications
  - Total amount patient will pay
  - List of unavailable medications with reasons

### 4. Flexible Workflow
- Pharmacist can adjust quantities based on availability
- Can reduce quantities to match available stock
- Can exclude medications by setting quantity to 0
- Full control before invoice generation

## Step-by-Step Workflow

### Step 1: Access Prescription
1. Pharmacist logs in
2. Navigates to prescription detail page
3. Clicks "Generate Invoice (Pharmacist)" button

### Step 2: Select Dispensary
1. Pharmacist sees dropdown list of active dispensaries
2. Selects the dispensary where medications will be dispensed
3. Medication input section appears

### Step 3: Review and Adjust Quantities
1. System displays all prescribed medications with:
   - Medication name
   - Prescribed quantity (pre-filled in input field)
   - Dosage and frequency information
   - Unit price
   - Item total (calculated automatically)

2. Pharmacist can:
   - Keep prescribed quantities (default)
   - Reduce quantities if needed
   - Set quantity to 0 to exclude medication
   - Cannot exceed prescribed quantity (validation)

3. As pharmacist changes quantities:
   - Item totals update automatically
   - Summary section is hidden (requires re-checking)

### Step 4: Check Availability
1. Pharmacist clicks "Check Availability for All Medications" button
2. System performs AJAX request to server
3. Server checks inventory in selected dispensary for each medication
4. System displays results:
   - **Available medications** (green background):
     - Shows "Available" badge
     - Displays stock quantity
     - Included in invoice calculation
   - **Unavailable medications** (red background):
     - Shows "Not Available" badge
     - Displays stock quantity vs. required
     - Excluded from invoice calculation

### Step 5: Review Summary
1. System displays comprehensive summary:
   - **Available Medications Count**: Number of medications that can be dispensed
   - **Unavailable Medications Count**: Number of medications that cannot be dispensed
   - **Subtotal**: Total cost of available medications
   - **NHIA Discount** (if applicable): 90% discount amount
   - **Patient Amount**: Final amount patient will pay

2. If medications are unavailable:
   - Warning alert appears
   - Lists each unavailable medication with details
   - Shows required quantity vs. available quantity

### Step 6: Make Adjustments (Optional)
1. If some medications are unavailable, pharmacist can:
   - Go back and reduce quantities to match available stock
   - Click "Check Availability" again
   - Repeat until satisfied

### Step 7: Generate Invoice
1. Pharmacist reviews final summary
2. Clicks "Generate Invoice" button
3. System shows confirmation dialog with:
   - Number of medications to be included
   - Number of medications to be excluded
   - Final amount
4. Pharmacist confirms
5. System generates invoice for available medications only
6. Success message shows:
   - Number of medications included
   - Number of medications excluded
   - Dispensary name

## Technical Implementation

### Frontend (Template)
**File**: `pharmacy/templates/pharmacy/pharmacist_generate_invoice.html`

**Key Components**:
1. **Dispensary Selector**:
   - Dropdown to select dispensary
   - Shows/hides medication section based on selection

2. **Medication Input Rows**:
   - Each medication has its own row with:
     - Medication information display
     - Quantity input field
     - Availability status display
     - Item total display
   - Data attributes for JavaScript processing

3. **Check Availability Button**:
   - Triggers AJAX request
   - Shows loading state during check
   - Enables after response

4. **Summary Section**:
   - Hidden until availability check completes
   - Shows counts and totals
   - Displays warnings for unavailable items

5. **JavaScript Logic**:
   - Event listeners for dispensary selection
   - Quantity input validation
   - AJAX availability checking
   - Dynamic UI updates
   - Form submission handling

### Backend (Views)

#### 1. AJAX Endpoint: `check_medication_availability`
**File**: `pharmacy/views.py`
**URL**: `/pharmacy/api/check-medication-availability/`
**Method**: POST
**Purpose**: Check medication availability in real-time

**Input**:
```json
{
  "dispensary_id": 1,
  "medications": [
    {
      "item_id": 123,
      "medication_id": 456,
      "quantity": 10
    }
  ]
}
```

**Output**:
```json
{
  "success": true,
  "medications": [
    {
      "item_id": 123,
      "medication_id": 456,
      "medication_name": "Paracetamol 500mg",
      "quantity": 10,
      "stock_available": 50,
      "available": true,
      "unit_price": 100.00,
      "total_price": 1000.00
    }
  ]
}
```

**Logic**:
1. Receives dispensary ID and medication list
2. For each medication:
   - Checks ActiveStoreInventory for the dispensary's active store
   - Checks legacy MedicationInventory as fallback
   - Calculates total available quantity
   - Compares with requested quantity
   - Calculates pricing
3. Returns availability status for each medication

#### 2. Invoice Generation: `pharmacist_generate_invoice`
**File**: `pharmacy/views.py`
**URL**: `/pharmacy/prescriptions/<id>/generate-invoice/`
**Methods**: GET, POST

**GET Request**:
- Displays the interactive form
- Loads prescription data
- Loads all active dispensaries
- Prepares medication list with prescribed quantities

**POST Request**:
- Receives form data including:
  - Dispensary ID
  - Custom quantities for each medication
  - Availability check results (JSON)
- Validates availability data exists
- Processes only available medications
- Calculates invoice amount with NHIA discount if applicable
- Creates pharmacy invoice
- Logs audit action
- Redirects to prescription detail with success message

### Database Queries

**Inventory Checking**:
```python
# Check ActiveStoreInventory
inventory_items = ActiveStoreInventory.objects.filter(
    medication=medication,
    active_store=active_store,
    stock_quantity__gt=0
)
available_quantity = sum(inv.stock_quantity for inv in inventory_items)

# Check legacy inventory
legacy_inv = MedicationInventory.objects.filter(
    medication=medication,
    dispensary=dispensary,
    stock_quantity__gt=0
).first()
```

## User Interface Elements

### Visual Indicators
1. **Medication Row Colors**:
   - Default: Light blue background
   - Available: Light green background
   - Unavailable: Light red background

2. **Status Badges**:
   - Available: Green badge with checkmark icon
   - Not Available: Red badge with X icon
   - Checking: Gray badge with spinner icon

3. **Summary Box**:
   - Gradient background (green for success)
   - Large, bold text for totals
   - Clear separation of available/unavailable counts

### Form Validation
1. **Quantity Input**:
   - Minimum: 0
   - Maximum: Prescribed quantity
   - Type: Number (decimal allowed)
   - Auto-validation on input

2. **Dispensary Selection**:
   - Required field
   - Must select before proceeding

3. **Availability Check**:
   - Must check availability before generating invoice
   - Form submission blocked without availability data

## Error Handling

### Client-Side Errors
1. **No Dispensary Selected**:
   - Alert: "Please select a dispensary first"
   - Focus on dispensary dropdown

2. **Quantity Exceeds Prescribed**:
   - Alert with prescribed amount
   - Reset to prescribed quantity

3. **No Availability Check**:
   - Alert: "Please check availability first"
   - Prevent form submission

4. **All Medications Unavailable**:
   - Alert: "No medications are available. Cannot generate invoice."
   - Prevent form submission

### Server-Side Errors
1. **Missing Dispensary ID**:
   - Error message
   - Redirect back to form

2. **Missing Availability Data**:
   - Error message: "Please check availability before generating invoice"
   - Redirect back to form

3. **No Available Medications**:
   - Error message
   - Redirect back to form

4. **Invoice Already Exists**:
   - Warning message
   - Redirect to prescription detail

## Benefits

### For Pharmacists
1. **Full Control**: Can adjust quantities based on actual availability
2. **Real-Time Feedback**: Instant availability checking
3. **Informed Decisions**: See exact stock levels before committing
4. **Flexibility**: Can modify quantities without page reload
5. **Transparency**: Clear summary of what will be invoiced

### For Patients
1. **Accurate Billing**: Only charged for available medications
2. **No Surprises**: Pharmacist knows availability before creating invoice
3. **Faster Service**: Pharmacist can adjust on the fly
4. **Better Communication**: Pharmacist can inform about unavailable items immediately

### For Hospital
1. **Inventory Accuracy**: Real-time inventory checking
2. **Reduced Disputes**: Patients only billed for what's available
3. **Better Workflow**: Pharmacists can handle partial availability
4. **Audit Trail**: All actions logged with details
5. **NHIA Compliance**: Automatic discount calculation

## Example Scenarios

### Scenario 1: All Medications Available
1. Doctor prescribes 3 medications
2. Pharmacist selects Dispensary A
3. Keeps all prescribed quantities
4. Checks availability - all show green
5. Reviews summary - all 3 medications, total ₦5,000
6. Generates invoice - patient pays ₦5,000

### Scenario 2: Partial Availability
1. Doctor prescribes 3 medications (A, B, C)
2. Pharmacist selects Dispensary A
3. Checks availability:
   - Medication A: Available (50 units in stock, need 10)
   - Medication B: Available (30 units in stock, need 20)
   - Medication C: Not Available (0 units in stock, need 15)
4. Summary shows 2 available, 1 unavailable
5. Generates invoice - patient pays for A and B only
6. Pharmacist informs patient about C

### Scenario 3: Quantity Adjustment
1. Doctor prescribes Medication A: 100 units
2. Pharmacist selects Dispensary A
3. Checks availability - only 60 units in stock
4. Pharmacist reduces quantity to 60
5. Checks availability again - now shows available
6. Generates invoice for 60 units
7. Pharmacist notes to reorder or transfer stock

### Scenario 4: NHIA Patient
1. Doctor prescribes medications totaling ₦10,000
2. Patient is NHIA member
3. Pharmacist checks availability - all available
4. Summary shows:
   - Subtotal: ₦10,000
   - NHIA Discount (90%): ₦9,000
   - Patient Pays (10%): ₦1,000
5. Invoice generated for ₦1,000

## Future Enhancements
1. Save draft quantities for later
2. Suggest alternative medications if unavailable
3. Auto-request stock transfer from bulk store
4. Batch processing for multiple prescriptions
5. Mobile-optimized interface
6. Barcode scanning for medication verification
7. Integration with supplier ordering system

## Support and Training
- User guide available at `USER_GUIDE_PRESCRIPTION_INVOICE_RECEIPT.md`
- Testing guide available at `TESTING_GUIDE.md`
- Technical documentation at `PRESCRIPTION_INVOICE_AND_RECEIPT_IMPLEMENTATION.md`

