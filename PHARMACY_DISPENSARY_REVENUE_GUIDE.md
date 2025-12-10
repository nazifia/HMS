# Pharmacy Dispensary Revenue Statistics - Implementation Guide

## Overview
A new dedicated page has been created for viewing pharmacy revenue broken down by individual dispensaries.

## How to Access
**URL**: `http://127.0.0.1:8000/pharmacy/revenue/dispensary/`

**Requirements**: User must be logged in

## Features Implemented

### 1. View Function (`pharmacy/views.py:1254`)
- Function name: `pharmacy_dispensary_revenue()`
- Queries DispensingLog model grouped by dispensary
- Calculates revenue, transactions, prescriptions per dispensary
- Provides date range filtering
- Handles legacy data (logs without dispensary assignment)

### 2. URL Pattern (`pharmacy/urls.py:46`)
```python
path('revenue/dispensary/', views.pharmacy_dispensary_revenue, name='pharmacy_dispensary_revenue')
```

### 3. Template (`pharmacy/templates/pharmacy/pharmacy_dispensary_revenue.html`)
Complete responsive template with:
- Date range filters (start_date, end_date)
- Search functionality for dispensaries
- Total pharmacy revenue card
- Performance metrics (4 cards showing key stats)
- Individual dispensary cards with progress bars
- Detailed breakdown table
- 3 interactive charts (pie, bar, line)

## Page Sections

### Header
- Page title: "Pharmacy Dispensary Revenue"
- Link to "All Departments" revenue view
- Search and date filter form

### Total Revenue Overview
- Large card showing total pharmacy revenue
- Transaction count, medications dispensed, active dispensaries

### Performance Metrics (4 Cards)
1. **Average Transaction Value** - Revenue per transaction
2. **Daily Average** - Average revenue per day
3. **Total Transactions** - Count of all dispensing transactions
4. **Medications Dispensed** - Total quantity of medications

### Dispensary Cards
- One card per active dispensary
- Shows: Revenue, Transactions, Prescriptions, Units Dispensed
- Progress bar showing percentage of total revenue
- Color-coded and hover effects

### Data Table
Columns:
- # (Row number)
- Dispensary name
- Revenue (₦)
- Transactions count
- Prescriptions count
- Units Dispensed
- % of Total
- Average Transaction Value

### Charts (3 visualizations)
1. **Dispensary Revenue Distribution** - Pie/Doughnut chart
2. **Dispensary Revenue Comparison** - Bar chart
3. **Monthly Revenue Trends** - Line chart (last 6 months per dispensary)

## Current Database Status
Based on testing:
- Active Dispensaries: 2 (GOPD PHARMACY, THEATRE PHARMACY)
- Total Dispensing Logs: 14
- Revenue (last 30 days): ₦29,500.00
- Revenue by Dispensary:
  - THEATRE PHARMACY: ₦29,500.00 (14 transactions)
  - GOPD PHARMACY: ₦0.00 (0 transactions)

## Template Dependencies
- **Custom Filters Used** (from `core.templatetags.custom_filters`):
  - `currency` - Format numbers as currency (₦)
  - `div` - Division operation
  - `default` - Default value if none
  - `pluralize` - Pluralization of words

- **Built-in Tags**:
  - `{% widthratio %}` - Calculate percentages for progress bars

- **External Libraries**:
  - Chart.js 3.9.1 - For interactive charts
  - Bootstrap 5 - For responsive layout
  - FontAwesome - For icons

## How to Use

### 1. Access the Page
```
http://127.0.0.1:8000/pharmacy/revenue/dispensary/
```

### 2. Filter by Date Range
- Select start date and end date
- Click "Apply" button
- Click "Clear" to reset to current month

### 3. Search Dispensaries
- Type dispensary name in search box
- Click "Search" button

### 4. View Charts
- Scroll down to see pie chart, bar chart, and monthly trends
- Hover over chart elements for detailed tooltips

## Testing Results

### ✓ View Function
- Imports successfully
- No syntax errors
- Queries database correctly

### ✓ URL Pattern
- Configured correctly at `/pharmacy/revenue/dispensary/`
- URL reversal works: `{% url 'pharmacy:pharmacy_dispensary_revenue' %}`

### ✓ Template
- Loads without errors
- All custom filters available
- Renders successfully with test data

### ✓ Data Flow
- DispensingLog queried correctly
- Revenue calculations accurate
- Dispensary grouping works
- Date filtering functional

### ✓ Existing Functionality
- Original revenue statistics page preserved
- No conflicts with existing URLs
- Django system check passes

## Sample Data Display

For the current database (as of testing):
- **Total Pharmacy Revenue**: ₦29,500.00
- **Dispensaries Shown**: 2
  - THEATRE PHARMACY: ₦29,500.00 (100% of total)
  - GOPD PHARMACY: ₦0.00 (0% of total)
- **Total Transactions**: 14
- **Date Range**: Nov 1, 2025 - Nov 30, 2025
- **Active Dispensaries**: 2

## Troubleshooting

### If Revenue Shows ₦0.00
1. Check date range - logs might be outside selected range
2. Verify DispensingLog entries have `dispensary` field populated
3. Check that dispensary is marked as `is_active=True`

### If Charts Don't Render
1. Check browser console for JavaScript errors
2. Verify Chart.js CDN is loading
3. Ensure JSON data is properly escaped in template

### If Dispensaries Don't Appear
1. Verify Dispensary objects exist and are active
2. Check DispensingLog entries link to dispensaries
3. Verify search filter isn't excluding results

## Files Modified/Created

### Modified Files
1. `pharmacy/views.py` - Added `pharmacy_dispensary_revenue()` function (216 lines)
2. `pharmacy/urls.py` - Added URL pattern at line 46

### Created Files
1. `pharmacy/templates/pharmacy/pharmacy_dispensary_revenue.html` - Complete template (597 lines)

## Integration with Existing System

### Navigation
To add a link in the sidebar, edit `templates/includes/sidebar.html` and add:
```html
<a class="collapse-item" href="{% url 'pharmacy:pharmacy_dispensary_revenue' %}">
    <i class="fas fa-store-alt"></i> Dispensary Revenue
</a>
```

### Permissions
Currently uses `@login_required` decorator. To add role-based access:
```python
# In the view function
if not (request.user.is_superuser or (request.user.profile and request.user.profile.role in ['admin', 'pharmacist'])):
    messages.error(request, 'You do not have permission to access this page.')
    return redirect('pharmacy:dashboard')
```

## Future Enhancements

Potential improvements:
1. Export to PDF/Excel functionality
2. Comparison between different time periods
3. Medication category breakdown per dispensary
4. Pharmacist performance metrics
5. Integration with billing module for payment tracking
6. Real-time revenue updates
7. Forecasting and trend analysis

## Support

For issues or questions:
1. Check Django logs: Look at server output for errors
2. Verify database connectivity
3. Ensure all migrations are applied: `python manage.py migrate`
4. Check static files are collected: `python manage.py collectstatic`

---

**Implementation Date**: November 26, 2025
**Status**: ✅ Complete and Tested
**Version**: 1.0
