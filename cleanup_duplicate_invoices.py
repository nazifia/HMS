"""
Script to clean up duplicate pharmacy_billing.Invoice records.
Keeps the most recent invoice (highest ID) for each prescription and deletes duplicates.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy_billing.models import Invoice as PharmacyInvoice
from django.db import connection

# Find prescriptions with duplicate invoices
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT prescription_id, COUNT(*)
        FROM pharmacy_billing_invoice
        WHERE prescription_id IS NOT NULL
        GROUP BY prescription_id
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()

print(f"Found {len(duplicates)} prescriptions with duplicate invoices")

total_deleted = 0
for prescription_id, count in duplicates:
    print(f"\nPrescription ID {prescription_id} has {count} invoices")

    # Get all invoices for this prescription, ordered by ID (newer = higher ID)
    invoices = PharmacyInvoice.objects.filter(prescription_id=prescription_id).order_by('-id')
    invoices_list = list(invoices)

    # Keep the first (newest), delete the rest
    keep = invoices_list[0]
    to_delete = invoices_list[1:]

    print(f"  Keeping invoice ID: {keep.id} (date: {keep.invoice_date})")
    for inv in to_delete:
        print(f"  Deleting invoice ID: {inv.id} (date: {inv.invoice_date})")
        inv.delete()
        total_deleted += 1

    print(f"  Deleted {len(to_delete)} duplicate invoices")

print(f"\nTotal duplicates deleted: {total_deleted}")
print("Cleanup complete!")
