# HMS New Features Documentation

This document describes the new features implemented in the Hospital Management System (HMS).

## Features Implemented

### 1. Automated Daily Admission Fee Deduction

**Description**: Automatically deduct daily admission charges from patient wallets at 12:00 AM for all active admissions.

**Key Components**:
- **Management Command**: `inpatient/management/commands/daily_admission_charges.py`
- **Cron Setup Script**: `scripts/setup_daily_charges_cron.py`
- **Transaction Types**: Added `daily_admission_charge` and `admission_fee` to WalletTransaction model

**How it Works**:
1. The system identifies all active admissions (status='admitted', not discharged)
2. Calculates daily charges based on ward rates
3. Creates invoices for daily charges
4. Automatically debits patient wallets
5. Creates transaction records for audit trail

**Usage**:
```bash
# Test the command (dry-run mode)
python manage.py daily_admission_charges --dry-run

# Run for specific date
python manage.py daily_admission_charges --date 2025-08-01

# Run for today (production)
python manage.py daily_admission_charges
```

**Automation Setup**:
```bash
# Set up cron job for daily execution at 12:00 AM
python scripts/setup_daily_charges_cron.py
```

**Cron Job Entry** (Linux/Mac):
```bash
0 0 * * * cd /path/to/hms && python manage.py daily_admission_charges >> /var/log/hms_daily_charges.log 2>&1
```

**Windows Task Scheduler**:
- Create a daily task that runs at 12:00 AM
- Command: `python /path/to/hms/manage.py daily_admission_charges`

### 2. Enhanced Prescription Viewing for Pharmacy Staff

**Description**: Improved prescription search and viewing functionality allowing pharmacy staff to easily view all prescriptions for a selected/searched patient.

**Key Components**:
- **Enhanced Search Form**: `pharmacy/forms.py` - PrescriptionSearchForm
- **New View**: `pharmacy/views.py` - patient_prescriptions()
- **New Template**: `pharmacy/templates/pharmacy/patient_prescriptions.html`
- **Updated URLs**: `pharmacy/urls.py`

**New Features**:
1. **Enhanced Search Fields**:
   - Patient search (name, ID, phone)
   - Patient number specific search
   - Medication name search
   - Status filtering
   - Payment status filtering
   - Doctor filtering
   - Date range filtering

2. **Patient-Specific Prescription View**:
   - View all prescriptions for a specific patient
   - Prescription history with statistics
   - Filter by status, payment status, date range
   - Quick action buttons (View, Dispense, Payment)
   - Pagination support

3. **Enhanced Prescription List**:
   - "All Prescriptions" button for each patient
   - Better layout with patient ID display
   - Improved action buttons layout

**URLs**:
- `/pharmacy/prescriptions/list/` - Enhanced prescription list
- `/pharmacy/prescriptions/patient/<patient_id>/` - Patient-specific prescriptions

**Usage for Pharmacy Staff**:
1. **Search for Patient Prescriptions**:
   - Go to Pharmacy → Prescriptions
   - Use the search form to find prescriptions by patient name, ID, or phone
   - Click "All Prescriptions" button next to any patient to see their complete history

2. **View Patient Prescription History**:
   - Access via patient-specific URL
   - View statistics (total, pending, dispensed, unpaid)
   - Filter by status, payment status, or date range
   - Take actions directly from the list

## Technical Details

### Database Changes

**New Transaction Types** in `patients.models.WalletTransaction`:
```python
('admission_fee', 'Admission Fee'),
('daily_admission_charge', 'Daily Admission Charge'),
```

**Field Changes**:
- `WalletTransaction.transaction_type` max_length increased from 20 to 30 characters
- Migration created: `patients/migrations/0005_alter_wallettransaction_transaction_type.py`

**Required Migration**:
```bash
python manage.py makemigrations patients
python manage.py migrate patients
```

### Security and Permissions

- All new views require appropriate permissions
- Daily charges command includes error handling and logging
- Dry-run mode available for testing

### Logging and Monitoring

**Daily Charges Logging**:
- Command output logged to `/var/log/hms_daily_charges.log` (Linux/Mac)
- Windows: logs to `logs/hms_daily_charges.log` in project directory
- Detailed error logging for troubleshooting

**Audit Trail**:
- All wallet transactions are logged with user, description, and timestamps
- Invoice creation for each daily charge
- Complete transaction history maintained

## Testing

**Test Script**: `test_new_features.py`
```bash
python test_new_features.py
```

**Manual Testing**:
1. **Daily Charges**:
   ```bash
   python manage.py daily_admission_charges --dry-run
   ```

2. **Prescription Views**:
   - Visit `/pharmacy/prescriptions/list/`
   - Test search functionality
   - Click "All Prescriptions" for any patient
   - Test filtering options

## Deployment Checklist

### For Daily Admission Charges:
- [ ] Run test command: `python manage.py daily_admission_charges --dry-run`
- [ ] Set up cron job: `python scripts/setup_daily_charges_cron.py`
- [ ] Verify log file permissions
- [ ] Test with actual data (small scale first)

### For Prescription Enhancements:
- [ ] Run Django check: `python manage.py check`
- [ ] Test prescription search functionality
- [ ] Verify patient prescription view works
- [ ] Check permissions for pharmacy staff

## Maintenance

### Daily Charges:
- Monitor log files for errors
- Check wallet balances periodically
- Verify invoice generation
- Review transaction records

### Prescription Views:
- Monitor search performance
- Update search indexes if needed
- Review user feedback for improvements

## Troubleshooting

### Common Issues:

1. **Daily Charges Not Running**:
   - Check cron job status: `crontab -l`
   - Verify Python path in cron job
   - Check log files for errors

2. **Prescription Search Not Working**:
   - Verify database indexes
   - Check form validation
   - Review URL patterns

3. **Permission Errors**:
   - Verify user has required permissions
   - Check Django permission system
   - Review role assignments

### Support:
- Check log files first
- Use dry-run mode for testing
- Review audit trails for transaction issues
- Contact system administrator for cron job issues

## Future Enhancements

### Potential Improvements:
1. **Email Notifications**: Send daily charge summaries to administrators
2. **Dashboard Widgets**: Add daily charges summary to dashboard
3. **Advanced Filtering**: More sophisticated prescription search options
4. **Bulk Operations**: Bulk actions for prescription management
5. **Mobile Optimization**: Improve mobile interface for pharmacy staff

### Performance Optimizations:
1. **Database Indexing**: Add indexes for frequently searched fields
2. **Caching**: Implement caching for prescription searches
3. **Background Tasks**: Use Celery for heavy operations
4. **Query Optimization**: Optimize database queries for large datasets
