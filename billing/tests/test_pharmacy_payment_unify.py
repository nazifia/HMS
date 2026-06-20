"""Guard for the billing unification (#5): a pharmacy invoice is an ordinary
billing.Invoice(source_app="pharmacy"), and a wallet-method payment debits the
patient wallet exactly ONCE (via billing signals) — not again by view code.
Regression guard against the double-debit class the unification removed.
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from billing.models import Invoice, Payment
from patients.models import Patient, PatientWallet, WalletTransaction


class PharmacyWalletPaymentTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="Pay", last_name="Once", date_of_birth="1990-01-01",
            gender="M", address="1 St", city="Town", state="ST", patient_id="P950",
        )
        # Wallet auto-created by signal; fund it.
        self.wallet = PatientWallet.objects.get(patient=self.patient)
        self.wallet.balance = Decimal("1000.00")
        self.wallet.save(update_fields=["balance"])

        self.invoice = Invoice.objects.create(
            patient=self.patient,
            source_app="pharmacy",
            invoice_number="PHMTEST1",
            invoice_date=timezone.now(),
            due_date=timezone.now().date(),
            subtotal=Decimal("200.00"),
            tax_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
        )

    def test_wallet_payment_debits_once_and_settles_invoice(self):
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("200.00"),
            payment_method="wallet",
            payment_date=timezone.now(),
        )

        # Debited exactly once: 1000 - 200. A second (manual) debit would give 600.
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("800.00"))

        # Exactly one wallet transaction is linked to this payment.
        self.assertEqual(
            WalletTransaction.objects.filter(patient_wallet=self.wallet).count(), 1
        )

        # Invoice settled by the signal from the sum of payments.
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("200.00"))
        self.assertEqual(self.invoice.status, "paid")
