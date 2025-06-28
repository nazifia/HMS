from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Prescription, PrescriptionItem
from django.conf import settings
from django.contrib.auth import get_user_model
from billing.models import Invoice

from decimal import Decimal
from django.db import transaction

# @receiver(post_save, sender=Prescription)
# def create_or_update_invoice_on_prescription_save(sender, instance, created, **kwargs):
#     """
#     Automatically create or update an invoice when a Prescription is created or updated.
#     """
#     # Only create invoice if there are items and total value > 0
#     items = instance.items.all()
#     total_value = Decimal('0.00')
#     for item in items:
#         if hasattr(item.medication, 'price') and item.quantity:
#             total_value += item.medication.price * Decimal(str(item.quantity))
#     if items.exists() and total_value > Decimal('0.00'):
#         try:
#             # Use a dummy request or system user if needed
#             request = None
#             _create_pharmacy_invoice(request, instance, total_value)
#         except Exception as e:
#             pass  # Optionally log error
#     # Disabled: Invoice creation now handled in pharmacy dispensing step

# @receiver(post_save, sender=PrescriptionItem)
# def create_or_update_invoice_on_item_save(sender, instance, created, **kwargs):
#     """
#     Automatically create or update an invoice when a PrescriptionItem is created or updated.
#     """
#     prescription = instance.prescription
#     items = prescription.items.all()
#     total_value = Decimal('0.00')
#     for item in items:
#         if hasattr(item.medication, 'price') and item.quantity:
#             total_value += item.medication.price * Decimal(str(item.quantity))
#     if items.exists() and total_value > Decimal('0.00'):
#         try:
#             request = None
#             _create_pharmacy_invoice(request, prescription, total_value)
#         except Exception as e:
#             pass
#     # Disabled: Invoice creation now handled in pharmacy dispensing step

# @receiver(post_delete, sender=PrescriptionItem)
# def update_invoice_on_item_delete(sender, instance, **kwargs):
#     """
#     Update or delete invoice when a PrescriptionItem is deleted.
#     """
#     prescription = instance.prescription
#     items = prescription.items.all()
#     total_value = Decimal('0.00')
#     for item in items:
#         if hasattr(item.medication, 'price') and item.quantity:
#             total_value += item.medication.price * Decimal(str(item.quantity))
#     if items.exists() and total_value > Decimal('0.00'):
#         try:
#             request = None
#             _create_pharmacy_invoice(request, prescription, total_value)
#         except Exception as e:
#             pass
#     else:
#         # If no items left, delete the invoice
#         Invoice.objects.filter(prescription=prescription).delete()
#     # Disabled: Invoice update now handled in pharmacy dispensing step
