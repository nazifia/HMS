from django.db import models
from django.contrib.auth.models import User
from patients.models import Patient
from pharmacy.models import Prescription
from decimal import Decimal
from django.conf import settings


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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    source_app = models.CharField(max_length=50, default='pharmacy')

    def save(self, *args, **kwargs):
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        super().save(*args, **kwargs)

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
