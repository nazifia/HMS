# Pharmacy Revenue Comprehensive Enhancement Design

## Overview

This design document outlines the enhancement of the existing Pharmacy Revenue Comprehensive page (previously at `http://127.0.0.1:8000/pharmacy/revenue/comprehensive/`, now available at `http://127.0.0.1:8000/pharmacy/revenue/statistics/`) to include revenue generated from all hospital departments and implement month-based search functionality.

## Current State Analysis

### Existing Implementation
- **URL**: `/pharmacy/revenue/statistics/` (previously `/pharmacy/revenue/comprehensive/`)
- **View**: `comprehensive_revenue_analysis` in `pharmacy/views.py`
- **Template**: `pharmacy/templates/pharmacy/comprehensive_revenue_analysis.html`
- **Current Scope**: Limited to pharmacy dispensing logs only
- **Date Filter**: Basic start/end date range selection

### Current Revenue Sources (Identified)
The current implementation only tracks:
- Pharmacy revenue from dispensed medications via `DispensingLog` records

### Missing Revenue Sources
Based on codebase analysis, the following revenue sources are not included:
1. **Laboratory Revenue** - Test requests and completed tests
2. **Consultation Revenue** - Doctor consultations and appointments  
3. **Theatre Revenue** - Surgical procedures and operations
4. **Admission Revenue** - Inpatient admission fees and services
5. **General Billing Revenue** - Other medical services and procedures

## Architecture Enhancement

### Data Model Integration

#### Revenue Source Models
```
Revenue Sources Mapping:
├── Pharmacy Revenue
│   ├── pharmacy_billing.Payment (Pharmacy invoices)
│   └── pharmacy.DispensingLog (Dispensed medications)
├── Laboratory Revenue  
│   └── billing.Invoice (source_app='laboratory')
├── Consultation Revenue
│   └── billing.Invoice (source_app='appointment')
├── Theatre Revenue
│   └── billing.Invoice (source_app='theatre')  
├── Admission Revenue
│   └── billing.Invoice (source_app='inpatient')
└── General Revenue
    └── billing.Invoice (source_app='billing')
```

#### Payment Models Hierarchy
```
Payment Processing:
├── billing.Payment (General hospital payments)
├── pharmacy_billing.Payment (Pharmacy-specific payments)
└── patients.WalletTransaction (Wallet-based payments)
```

### Database Query Strategy

#### Revenue Aggregation Logic
```
Revenue Calculation per Department:
1. Pharmacy Revenue = Σ(pharmacy_billing.Payment.amount) + Σ(DispensingLog.total_price_for_this_log)
2. Laboratory Revenue = Σ(billing.Payment.amount WHERE invoice.source_app='laboratory')
3. Consultation Revenue = Σ(billing.Payment.amount WHERE invoice.source_app='appointment')  
4. Theatre Revenue = Σ(billing.Payment.amount WHERE invoice.source_app='theatre')
5. Admission Revenue = Σ(billing.Payment.amount WHERE invoice.source_app='inpatient')
6. General Revenue = Σ(billing.Payment.amount WHERE invoice.source_app='billing')
```

#### Month-Based Filtering
```
Date Filtering Options:
├── Current Month (Default)
├── Previous Month
├── Last 3 Months
├── Last 6 Months
├── Last 12 Months
├── Year-to-Date
├── Custom Date Range
└── Specific Month/Year Selection
```

## Component Design

### Enhanced View Logic

#### Revenue Aggregation Service
```python
class RevenueAggregationService:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
    
    def get_pharmacy_revenue(self):
        # Pharmacy billing payments + dispensing logs
        
    def get_laboratory_revenue(self):
        # Laboratory invoice payments
        
    def get_consultation_revenue(self):
        # Consultation/appointment invoice payments
        
    def get_theatre_revenue(self):
        # Theatre/surgery invoice payments
        
    def get_admission_revenue(self):
        # Admission invoice payments
        
    def get_general_revenue(self):
        # General billing invoice payments
        
    def get_monthly_trends(self):
        # Month-by-month revenue breakdown
        
    def get_daily_breakdown(self):
        # Day-by-day revenue analysis
```

#### Month Selection Component
```
Month Filter Interface:
├── Dropdown for Month Selection
├── Dropdown for Year Selection  
├── Quick Select Buttons (Current, Previous, YTD)
├── Custom Date Range Picker
└── Apply/Reset Filter Actions
```

### Data Aggregation Logic

#### Revenue Collection Strategy
```
Data Sources Integration:
1. Pharmacy Revenue:
   - Query: pharmacy_billing.Payment + DispensingLog
   - Filter: payment_date/dispensed_date within range
   - Aggregate: SUM(amount) + SUM(total_price_for_this_log)

2. Other Department Revenue:
   - Query: billing.Payment JOIN billing.Invoice
   - Filter: payment_date within range AND source_app = department
   - Aggregate: SUM(payment.amount) GROUP BY source_app

3. Monthly Trends:
   - Query: All payment sources
   - Group: EXTRACT(month, payment_date), EXTRACT(year, payment_date)
   - Aggregate: SUM(amount) per month per department
```

#### Performance Optimization
```
Query Optimization:
├── Database Indexes on payment_date fields
├── Selective field loading with select_related()
├── Aggregation at database level using SUM()
├── Caching for frequently accessed data
└── Pagination for large result sets
```

### User Interface Enhancement

#### Filter Panel Design
```
Enhanced Filter Panel:
├── Month/Year Dropdowns
├── Quick Filter Buttons
│   ├── "Current Month"
│   ├── "Previous Month" 
│   ├── "Last 3 Months"
│   ├── "Last 6 Months"
│   ├── "Year to Date"
│   └── "Custom Range"
├── Department Filter Checkboxes
└── Apply/Reset Actions
```

#### Revenue Display Components
```
Revenue Dashboard Layout:
├── Total Revenue Summary Card
├── Department-wise Revenue Cards
│   ├── Pharmacy Revenue Card
│   ├── Laboratory Revenue Card
│   ├── Consultation Revenue Card
│   ├── Theatre Revenue Card
│   ├── Admission Revenue Card
│   └── General Revenue Card
├── Revenue Distribution Charts
│   ├── Monthly Trend Line Chart
│   ├── Department Distribution Pie Chart
│   └── Daily Revenue Bar Chart
└── Detailed Revenue Tables
    ├── Top Revenue Sources Table
    ├── Monthly Breakdown Table
    └── Export Options
```

## Implementation Strategy

### Phase 1: Data Integration
1. **Revenue Service Creation**
   - Create `RevenueAggregationService` class
   - Implement department-specific revenue methods
   - Add comprehensive data validation

2. **Model Integration**
   - Update view to use all payment models
   - Implement proper JOIN operations
   - Add error handling for missing data

### Phase 2: Month-Based Filtering
1. **Filter Component**
   - Create month/year selection dropdowns
   - Implement quick filter buttons
   - Add custom date range picker

2. **Backend Logic**
   - Modify date parsing logic
   - Implement month-based query filtering
   - Add validation for date ranges

### Phase 3: UI Enhancement
1. **Template Restructuring**
   - Update template with comprehensive revenue cards
   - Enhance charts with all revenue sources
   - Improve responsive design

2. **Interactive Features**
   - Add dynamic chart updates
   - Implement real-time filtering
   - Add export functionality

### Phase 4: Performance & Testing
1. **Optimization**
   - Database query optimization
   - Implement caching strategy
   - Add pagination for large datasets

2. **Validation**
   - Unit tests for revenue calculations
   - Integration tests for all revenue sources
   - Performance testing with large datasets

## Technical Specifications

### Database Queries

#### Primary Revenue Query
```sql
-- Comprehensive revenue aggregation
SELECT 
    source_app,
    DATE_TRUNC('month', payment_date) as month,
    SUM(amount) as total_revenue,
    COUNT(*) as transaction_count
FROM (
    -- Billing payments
    SELECT bp.amount, bp.payment_date, bi.source_app
    FROM billing_payment bp
    JOIN billing_invoice bi ON bp.invoice_id = bi.id
    WHERE bp.payment_date BETWEEN %s AND %s
    
    UNION ALL
    
    -- Pharmacy payments  
    SELECT pp.amount, pp.payment_date, 'pharmacy' as source_app
    FROM pharmacy_billing_payment pp
    WHERE pp.payment_date BETWEEN %s AND %s
) combined_payments
GROUP BY source_app, DATE_TRUNC('month', payment_date)
ORDER BY month DESC, source_app;
```

#### Monthly Trend Analysis
```sql
-- Monthly revenue trends by department
SELECT 
    EXTRACT(year FROM payment_date) as year,
    EXTRACT(month FROM payment_date) as month,
    source_app,
    SUM(amount) as monthly_revenue
FROM combined_revenue_view 
WHERE payment_date >= %s AND payment_date <= %s
GROUP BY year, month, source_app
ORDER BY year, month, source_app;
```

### API Endpoints

#### Revenue Data API
```
GET /pharmacy/api/revenue/comprehensive/
Parameters:
- start_date: YYYY-MM-DD
- end_date: YYYY-MM-DD  
- month: MM (optional)
- year: YYYY (optional)
- departments: comma-separated list
- format: json|csv|pdf

Response:
{
    "total_revenue": decimal,
    "department_breakdown": {
        "pharmacy": {"revenue": decimal, "transactions": int},
        "laboratory": {"revenue": decimal, "transactions": int},
        "consultation": {"revenue": decimal, "transactions": int},
        "theatre": {"revenue": decimal, "transactions": int},
        "admission": {"revenue": decimal, "transactions": int},
        "general": {"revenue": decimal, "transactions": int}
    },
    "monthly_trends": [...],
    "daily_breakdown": [...]
}
```

### Form Components

#### Enhanced Filter Form
```python
class ComprehensiveRevenueFilterForm(forms.Form):
    MONTH_CHOICES = [(i, calendar.month_name[i]) for i in range(1, 13)]
    YEAR_CHOICES = [(y, y) for y in range(2020, timezone.now().year + 2)]
    
    filter_type = forms.ChoiceField(
        choices=[
            ('current_month', 'Current Month'),
            ('previous_month', 'Previous Month'),
            ('last_3_months', 'Last 3 Months'),
            ('last_6_months', 'Last 6 Months'),
            ('year_to_date', 'Year to Date'),
            ('custom_range', 'Custom Range'),
            ('specific_month', 'Specific Month')
        ]
    )
    month = forms.ChoiceField(choices=MONTH_CHOICES, required=False)
    year = forms.ChoiceField(choices=YEAR_CHOICES, required=False)
    start_date = forms.DateField(required=False)
    end_date = forms.DateField(required=False)
    departments = forms.MultipleChoiceField(
        choices=[
            ('pharmacy', 'Pharmacy'),
            ('laboratory', 'Laboratory'),  
            ('consultation', 'Consultations'),
            ('theatre', 'Theatre'),
            ('admission', 'Admissions'),
            ('general', 'General')
        ],
        required=False
    )
```

## Testing Strategy

### Unit Testing
```
Test Coverage Areas:
├── Revenue calculation accuracy
├── Date range filtering logic
├── Department-wise aggregation
├── Month-based filtering
├── Edge case handling
└── Performance benchmarks
```

### Integration Testing  
```
Integration Test Scenarios:
├── End-to-end revenue flow validation
├── Cross-department data consistency
├── Filter combination testing
├── Large dataset performance
└── UI component integration
```

### Data Validation
```
Validation Checkpoints:
├── Revenue total accuracy vs individual payments
├── Department categorization correctness  
├── Date range boundary conditions
├── Missing data handling
└── Duplicate payment prevention
```

## Security Considerations

### Access Control
```
Security Measures:
├── Role-based access control for revenue data
├── Audit logging for revenue queries
├── Data export permissions
├── Sensitive information masking
└── Rate limiting for API endpoints
```

### Data Privacy
```
Privacy Controls:
├── Patient information anonymization
├── Revenue data access logging
├── Export audit trails
├── Compliance with healthcare regulations
└── Data retention policies
```