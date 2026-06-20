"""Unify billing: migrate pharmacy_billing.{Invoice,Payment,InvoiceItem} into
billing.{Invoice,Payment,InvoiceItem} (source_app="pharmacy") and repoint the
PrescriptionCart.invoice FK from pharmacy_billing.Invoice to billing.Invoice.

Historical models returned by apps.get_model do not fire billing.signals
(those are bound to the concrete billing.models classes), so copying payments
here does NOT re-debit patient wallets. invoice_number / amount_paid / status
are set explicitly because the historical model has no custom save().
"""
from django.db import migrations, models
import django.db.models.deletion


# Map of cart pk -> old pharmacy_billing invoice pk, captured before the carts
# are detached and reused after the FK is retargeted. Module-global because it
# must survive between the two RunPython steps of a single migrate run.
_CART_OLD_INVOICE = {}
# Map of old pharmacy_billing invoice pk -> new billing invoice pk.
_INVOICE_MAP = {}


def copy_and_detach(apps, schema_editor):
    PharmacyInvoice = apps.get_model("pharmacy_billing", "Invoice")
    PharmacyPayment = apps.get_model("pharmacy_billing", "Payment")
    PharmacyItem = apps.get_model("pharmacy_billing", "InvoiceItem")
    BillingInvoice = apps.get_model("billing", "Invoice")
    BillingPayment = apps.get_model("billing", "Payment")
    BillingItem = apps.get_model("billing", "InvoiceItem")
    Cart = apps.get_model("pharmacy", "PrescriptionCart")

    _INVOICE_MAP.clear()
    _CART_OLD_INVOICE.clear()

    # Copy invoices.
    for pi in PharmacyInvoice.objects.all():
        bi = BillingInvoice.objects.create(
            patient_id=pi.patient_id,
            prescription_id=pi.prescription_id,
            source_app="pharmacy",
            invoice_number=f"PHM{pi.id:06d}",
            invoice_date=pi.invoice_date,
            due_date=pi.due_date,
            created_by_id=pi.created_by_id,
            subtotal=pi.subtotal,
            tax_amount=pi.tax_amount,
            discount_amount=pi.discount_amount,
            total_amount=pi.total_amount,
            amount_paid=pi.amount_paid,
            status=pi.status,
        )
        _INVOICE_MAP[pi.id] = bi.id

    # Copy payments (no signals on historical models -> no wallet re-debit).
    for pp in PharmacyPayment.objects.all():
        BillingPayment.objects.create(
            invoice_id=_INVOICE_MAP[pp.invoice_id],
            amount=pp.amount,
            payment_date=pp.payment_date,
            payment_method=pp.payment_method,
            transaction_id=pp.transaction_id,
            notes=pp.notes,
            received_by_id=pp.received_by_id,
        )

    # Copy invoice items (computed totals set explicitly).
    for it in PharmacyItem.objects.all():
        line = it.unit_price * it.quantity
        tax = line * it.tax_percentage / 100
        BillingItem.objects.create(
            invoice_id=_INVOICE_MAP[it.invoice_id],
            service_id=it.service_id,
            description=it.description,
            quantity=it.quantity,
            unit_price=it.unit_price,
            tax_percentage=it.tax_percentage,
            tax_amount=tax,
            total_amount=line + tax,
        )

    # Remember cart links, then detach so the FK can be retargeted without a
    # constraint violation (old ids don't exist in billing).
    for cart in Cart.objects.filter(invoice__isnull=False):
        _CART_OLD_INVOICE[cart.id] = cart.invoice_id
    Cart.objects.filter(invoice__isnull=False).update(invoice=None)


def relink_carts(apps, schema_editor):
    Cart = apps.get_model("pharmacy", "PrescriptionCart")
    for cart_id, old_invoice_id in _CART_OLD_INVOICE.items():
        new_id = _INVOICE_MAP.get(old_invoice_id)
        if new_id is not None:
            Cart.objects.filter(id=cart_id).update(invoice=new_id)


def reverse(apps, schema_editor):
    # Best-effort: drop migrated billing rows and detach carts. The original
    # pharmacy_billing rows are untouched by the forward migration, so reversing
    # the FK (next op) restores the old links from the DB backup if needed.
    BillingInvoice = apps.get_model("billing", "Invoice")
    Cart = apps.get_model("pharmacy", "PrescriptionCart")
    migrated = BillingInvoice.objects.filter(
        source_app="pharmacy", invoice_number__startswith="PHM"
    )
    Cart.objects.filter(invoice__in=migrated).update(invoice=None)
    migrated.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0026_seed_medications_consumables"),
        ("billing", "0012_seed_fee_services"),
        ("pharmacy_billing", "0006_alter_invoice_prescription_related_name"),
    ]

    operations = [
        migrations.RunPython(copy_and_detach, reverse),
        migrations.AlterField(
            model_name="prescriptioncart",
            name="invoice",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="prescription_cart",
                to="billing.invoice",
            ),
        ),
        migrations.RunPython(relink_carts, migrations.RunPython.noop),
    ]
