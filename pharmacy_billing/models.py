from django.db import models
from django.contrib.auth.models import User
from patients.models import Patient
from pharmacy.models import Prescription
from decimal import Decimal
from django.conf import settings
from django.utils import timezone


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    prescription = models.OneToOneField(Prescription, on_delete=models.CASCADE, null=True, blank=True, related_name='invoice_prescription')
    invoice_date = models.DateField()
    due_date = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    source_app = models.CharField(max_length=50, default='pharmacy')

    def save(self, *args, **kwargs):
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        super().save(*args, **kwargs)

    def get_balance(self):
        """Return the remaining balance on this invoice"""
        return self.total_amount - self.amount_paid

    def is_paid(self):
        """Check if the invoice is fully paid"""
        return self.amount_paid >= self.total_amount


class Payment(models.Model):
    """Payment model for pharmacy billing invoices"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('upi', 'UPI'),
        ('net_banking', 'Net Banking'),
        ('insurance', 'Insurance'),
        ('wallet', 'Wallet'),
        ('other', 'Other'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pharmacy_payments')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment of ₦{self.amount} for Invoice #{self.invoice.id}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    service = models.ForeignKey('billing.Service', on_delete=models.CASCADE, related_name='pharmacy_billing_invoice_items')
    description = models.TextField()
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    @property
    def total_price(self):
        return (self.unit_price * self.quantity) + ((self.unit_price * self.quantity) * self.tax_percentage / 100)
