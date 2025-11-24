# Currency Formatting Guide

This guide explains how to use the humanized currency formatting throughout the HMS codebase.

## Overview

All monetary values are now formatted with:
- **Currency symbol**: ₦ (Nigerian Naira)
- **Thousand separators**: Commas (e.g., 1,234,567.89)
- **Decimal places**: Always 2 decimal places
- **Format**: `₦ 1,234.56` (currency symbol, space, formatted number)

## In Django Templates

### Load the Custom Filters

Add this to the top of your template file (after `{% load static %}`):

```django
{% load custom_filters %}
```

### Using the `currency` Filter

Replace old patterns:

```django
{# OLD - Don't use these anymore #}
₦{{ amount|floatformat:2 }}
₦{{ price|floatformat:0 }}
${{ cost }}
{{ total|floatformat:2 }}

{# NEW - Use this everywhere #}
{{ amount|currency }}
{{ price|currency }}
{{ cost|currency }}
{{ total|currency }}
```

### Examples

```django
{# Simple usage #}
<p>Total: {{ invoice.total_amount|currency }}</p>
{# Output: Total: ₦ 1,234.56 #}

{# With complex expressions #}
<p>Subtotal: {{ item.quantity|multiply:item.price|currency }}</p>
{# Output: Subtotal: ₦ 5,000.00 #}

{# With default values #}
<p>Balance: {{ wallet.balance|default:0|currency }}</p>
{# Output: Balance: ₦ 0.00 (if balance is None) #}

{# Negative values #}
<p>Debt: {{ outstanding|currency }}</p>
{# Output: Debt: -₦ 500.00 #}
```

### Other Useful Filters

```django
{# Format without currency symbol (for inputs) #}
{{ amount|currency_no_symbol }}
{# Output: 1,234.56 #}

{# Math filters #}
{{ total|subtract:paid }}  {# Subtraction #}
{{ price|multiply:quantity }}  {# Multiplication #}
{{ total|div:count }}  {# Division #}
{{ part|percentage:whole }}  {# Percentage (25.5%) #}
```

## In Python Code

### Importing

```python
from core.utils import format_currency, parse_currency, calculate_percentage
```

### Using `format_currency()`

```python
from core.utils import format_currency

# Basic usage
amount = 1234.56
formatted = format_currency(amount)
# Result: "₦ 1,234.56"

# Large numbers
revenue = 1234567.89
formatted = format_currency(revenue)
# Result: "₦ 1,234,567.89"

# Negative values
debt = -500.00
formatted = format_currency(debt)
# Result: "-₦ 500.00"

# Without symbol (for calculations or display)
formatted = format_currency(amount, symbol=False)
# Result: "1,234.56"

# Handle None/empty values
formatted = format_currency(None)
# Result: "₦ 0.00"
```

### Using `parse_currency()`

Convert formatted currency strings back to numeric values:

```python
from core.utils import parse_currency

# Parse formatted string
value = parse_currency("₦ 1,234.56")
# Result: 1234.56

# Parse negative
value = parse_currency("-₦ 500.00")
# Result: -500.0

# Already numeric
value = parse_currency(1234.56)
# Result: 1234.56

# Handle invalid input
value = parse_currency(None)
# Result: 0.0
```

### Using `calculate_percentage()`

```python
from core.utils import calculate_percentage

# Basic usage
pct = calculate_percentage(25, 100)
# Result: "25.0%"

# With more decimal places
pct = calculate_percentage(1234, 5000, decimal_places=2)
# Result: "24.68%"
```

## In Views (Example Usage)

### Before (Old Way)

```python
def invoice_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    # Old formatting
    total = f"₦{invoice.total_amount:.2f}"
    paid = f"₦{invoice.amount_paid:.2f}"

    messages.success(request, f"Paid {paid} out of {total}")
```

### After (New Way)

```python
from core.utils import format_currency

def invoice_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    # New formatting with thousand separators
    total = format_currency(invoice.total_amount)
    paid = format_currency(invoice.amount_paid)

    messages.success(request, f"Paid {paid} out of {total}")
    # Message: "Paid ₦ 5,000.00 out of ₦ 10,000.00"
```

## In Models (String Representation)

### Example: Adding __str__ with Currency

```python
from core.utils import format_currency

class Invoice(models.Model):
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Invoice #{self.id} - {format_currency(self.total_amount)}"

    def formatted_total(self):
        """Get formatted total for display in templates or admin."""
        return format_currency(self.total_amount)
```

## In Management Commands

### Example: Reporting with Currency

```python
from django.core.management.base import BaseCommand
from core.utils import format_currency

class Command(BaseCommand):
    help = 'Generate financial report'

    def handle(self, *args, **options):
        total_revenue = calculate_total_revenue()

        # Format output
        self.stdout.write(
            self.style.SUCCESS(
                f"Total Revenue: {format_currency(total_revenue)}"
            )
        )
```

## In API Responses (DRF)

### Example: Serializer with Formatted Currency

```python
from rest_framework import serializers
from core.utils import format_currency

class InvoiceSerializer(serializers.ModelSerializer):
    total_formatted = serializers.SerializerMethodField()

    def get_total_formatted(self, obj):
        return format_currency(obj.total_amount)

    class Meta:
        model = Invoice
        fields = ['id', 'total_amount', 'total_formatted']
```

## Common Patterns

### 1. NHIA Cost Splitting (10% / 90%)

```python
from core.utils import format_currency

patient_pays = total_cost * 0.10
nhia_covers = total_cost * 0.90

message = (
    f"Patient pays: {format_currency(patient_pays)}, "
    f"NHIA covers: {format_currency(nhia_covers)}"
)
```

### 2. Invoice Balance Calculation

```python
balance = invoice.total_amount - invoice.amount_paid
balance_msg = f"Balance: {format_currency(balance)}"
```

### 3. Wallet Transactions

```python
from core.utils import format_currency

# Deposit
deposit_msg = f"Deposited {format_currency(amount)} to wallet"

# Withdrawal
withdrawal_msg = f"Withdrew {format_currency(amount)} from wallet"

# Balance
balance_msg = f"Current balance: {format_currency(wallet.balance)}"
```

## Migration Strategy for Existing Python Code

If you have existing Python code with old currency formatting:

### Find and Replace Pattern

**Old patterns to look for:**
```python
f"₦{amount:.2f}"
f"₦{amount:,.2f}"
f"N{amount:.2f}"
f"${amount:.2f}"
"₦%.2f" % amount
```

**Replace with:**
```python
format_currency(amount)
```

### Automated Search

Use grep to find all occurrences:

```bash
# Find f-strings with ₦ symbol
grep -r "f['\"].*₦" --include="*.py"

# Find format strings
grep -r "%.2f" --include="*.py" | grep -i "amount\|price\|cost\|total"
```

## Testing

Test your currency formatting:

```python
from core.utils import format_currency, parse_currency

# Run in Django shell
python manage.py shell

# Test various scenarios
>>> format_currency(1234.56)
'₦ 1,234.56'

>>> format_currency(1000000)
'₦ 1,000,000.00'

>>> parse_currency("₦ 5,000.00")
5000.0
```

## Best Practices

1. **Always use the currency filter in templates** - Don't manually format
2. **Use format_currency() in Python code** - Consistent formatting
3. **Store raw numbers in database** - Never store formatted strings
4. **Use Decimal type for money** - Avoid float rounding errors
5. **Handle None values** - Both functions handle None gracefully

## Complete Example: Payment Flow

```python
# views.py
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from core.utils import format_currency

def process_payment(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    if request.method == 'POST':
        amount = request.POST.get('amount')

        # Process payment...
        invoice.amount_paid += Decimal(amount)
        invoice.save()

        # Formatted success message
        messages.success(
            request,
            f"Payment of {format_currency(amount)} processed. "
            f"Balance: {format_currency(invoice.get_balance())}"
        )

    context = {
        'invoice': invoice,
    }
    return render(request, 'billing/payment.html', context)
```

```django
{# payment.html #}
{% load custom_filters %}

<h3>Invoice Total: {{ invoice.total_amount|currency }}</h3>
<p>Amount Paid: {{ invoice.amount_paid|currency }}</p>
<p>Balance: {{ invoice.get_balance|currency }}</p>
```

## Questions?

If you need help with currency formatting in a specific context, check:
1. This guide
2. `core/utils.py` - Python functions
3. `core/templatetags/custom_filters.py` - Template filters
4. Existing usage examples in the codebase

---

**Generated**: 2025
**Last Updated**: After currency humanization project
