"""
Prescription Cart Models for HMS Pharmacy Module

This module provides a shopping cart-like system for prescription dispensing.
Pharmacists can add prescription items to a cart, adjust quantities, check availability,
generate invoices, and complete dispensing after payment.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError


class PrescriptionCart(models.Model):
    """
    Shopping cart for prescription items.
    Allows pharmacist to prepare billing before creating invoice and dispensing.
    """
    
    STATUS_CHOICES = (
        ('active', 'Active'),           # Cart is being prepared
        ('invoiced', 'Invoiced'),       # Invoice created, awaiting payment
        ('paid', 'Paid'),               # Payment completed, ready to dispense
        ('completed', 'Completed'),     # Dispensing completed
        ('cancelled', 'Cancelled'),     # Cart cancelled
    )
    
    prescription = models.ForeignKey(
        'pharmacy.Prescription',
        on_delete=models.CASCADE,
        related_name='carts'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prescription_carts_created'
    )
    
    dispensary = models.ForeignKey(
        'pharmacy.Dispensary',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Dispensary from which items will be dispensed"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    invoice = models.ForeignKey(
        'pharmacy_billing.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescription_cart'
    )
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Prescription Cart'
        verbose_name_plural = 'Prescription Carts'
    
    def __str__(self):
        return f"Cart #{self.id} - {self.prescription.patient.get_full_name()} - {self.get_status_display()}"
    
    def get_total_items(self):
        """Get total number of items in cart"""
        return self.items.count()
    
    def get_subtotal(self):
        """Calculate subtotal of all items in cart"""
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.get_subtotal()
        return total
    
    def get_patient_payable(self):
        """Calculate patient payable amount (with NHIA discount if applicable)"""
        subtotal = self.get_subtotal()
        
        if self.prescription.patient.is_nhia_patient():
            # Patient pays 10%, NHIA covers 90%
            return subtotal * Decimal('0.10')
        else:
            # Patient pays 100%
            return subtotal
    
    def get_nhia_coverage(self):
        """Calculate NHIA coverage amount"""
        subtotal = self.get_subtotal()
        
        if self.prescription.patient.is_nhia_patient():
            # NHIA covers 90%
            return subtotal * Decimal('0.90')
        else:
            return Decimal('0.00')
    
    def can_generate_invoice(self):
        """Check if invoice can be generated from this cart"""
        if self.status != 'active':
            return False, f'Cart status is {self.get_status_display()}, must be Active'
        
        if not self.items.exists():
            return False, 'Cart is empty'
        
        if not self.dispensary:
            return False, 'No dispensary selected'
        
        # Check if all items have sufficient stock
        for item in self.items.all():
            if not item.has_sufficient_stock():
                return False, f'Insufficient stock for {item.prescription_item.medication.name}'
        
        return True, 'Cart is ready for invoice generation'
    
    def can_complete_dispensing(self):
        """Check if dispensing can be completed"""
        if self.status != 'paid':
            return False, f'Cart status is {self.get_status_display()}, must be Paid'
        
        if not self.invoice:
            return False, 'No invoice associated with this cart'
        
        if self.invoice.status != 'paid':
            return False, 'Invoice is not paid'
        
        return True, 'Cart is ready for dispensing'
    
    def clear_cart(self):
        """Remove all items from cart"""
        self.items.all().delete()
    
    def cancel_cart(self):
        """Cancel the cart"""
        self.status = 'cancelled'
        self.save()


class PrescriptionCartItem(models.Model):
    """
    Individual item in prescription cart.
    Represents a medication with quantity to be dispensed.
    """
    
    cart = models.ForeignKey(
        PrescriptionCart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    prescription_item = models.ForeignKey(
        'pharmacy.PrescriptionItem',
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    
    quantity = models.IntegerField(
        help_text="Quantity to dispense/bill"
    )
    
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Unit price at time of adding to cart"
    )
    
    available_stock = models.IntegerField(
        default=0,
        help_text="Available stock at time of adding to cart (cached)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'prescription_item']
    
    def __str__(self):
        return f"{self.prescription_item.medication.name} x {self.quantity}"
    
    def clean(self):
        """Validate cart item"""
        # Check if quantity is positive
        if self.quantity <= 0:
            raise ValidationError('Quantity must be greater than zero')
        
        # Check if quantity doesn't exceed prescribed quantity
        remaining = self.prescription_item.remaining_quantity_to_dispense
        if self.quantity > remaining:
            raise ValidationError(
                f'Quantity ({self.quantity}) exceeds remaining quantity to dispense ({remaining})'
            )
    
    def save(self, *args, **kwargs):
        # Set unit price from medication if not set
        if not self.unit_price:
            self.unit_price = self.prescription_item.medication.price or Decimal('0.00')
        
        # Update available stock
        self.update_available_stock()
        
        super().save(*args, **kwargs)
    
    def get_subtotal(self):
        """Calculate subtotal for this item"""
        return Decimal(str(self.quantity)) * self.unit_price
    
    def get_patient_pays(self):
        """Calculate patient payable amount for this item"""
        subtotal = self.get_subtotal()
        
        if self.cart.prescription.patient.is_nhia_patient():
            return subtotal * Decimal('0.10')
        else:
            return subtotal
    
    def get_nhia_covers(self):
        """Calculate NHIA coverage for this item"""
        subtotal = self.get_subtotal()
        
        if self.cart.prescription.patient.is_nhia_patient():
            return subtotal * Decimal('0.90')
        else:
            return Decimal('0.00')
    
    def update_available_stock(self):
        """Update available stock from inventory"""
        if not self.cart.dispensary:
            self.available_stock = 0
            return
        
        from pharmacy.models import ActiveStoreInventory, MedicationInventory
        
        medication = self.prescription_item.medication
        dispensary = self.cart.dispensary
        
        # Check ActiveStoreInventory first
        total_stock = 0
        try:
            active_store = getattr(dispensary, 'active_store', None)
            if active_store:
                inventory_items = ActiveStoreInventory.objects.filter(
                    medication=medication,
                    active_store=active_store,
                    stock_quantity__gt=0
                )
                total_stock = sum(item.stock_quantity for item in inventory_items)
        except Exception:
            pass
        
        # Check legacy inventory if no stock found
        if total_stock == 0:
            try:
                legacy_inv = MedicationInventory.objects.filter(
                    medication=medication,
                    dispensary=dispensary,
                    stock_quantity__gt=0
                ).first()
                
                if legacy_inv:
                    total_stock = legacy_inv.stock_quantity
            except Exception:
                pass
        
        self.available_stock = total_stock
    
    def has_sufficient_stock(self):
        """Check if there's sufficient stock for this item"""
        self.update_available_stock()
        return self.available_stock >= self.quantity
    
    def get_stock_status(self):
        """Get stock status for display"""
        self.update_available_stock()
        
        if self.available_stock >= self.quantity:
            return {
                'status': 'available',
                'message': f'{self.available_stock} available',
                'css_class': 'success',
                'icon': 'check-circle'
            }
        elif self.available_stock > 0:
            return {
                'status': 'partial',
                'message': f'Only {self.available_stock} available',
                'css_class': 'warning',
                'icon': 'exclamation-triangle'
            }
        else:
            return {
                'status': 'out_of_stock',
                'message': 'Out of stock',
                'css_class': 'danger',
                'icon': 'times-circle'
            }

