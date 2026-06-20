"""Guards for the wallet credit/debit fixes:

- #1: shared-wallet routing must survive (the duplicate credit/debit defs that
  dropped routing are gone).
- #2: individual credit/debit update balance atomically and record balance_after.
"""
from decimal import Decimal

from django.test import TestCase

from patients.models import Patient, PatientWallet, SharedWallet, WalletTransaction


class WalletRoutingTestCase(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Doe",
            date_of_birth="1990-01-01",
            gender="F",
            address="1 St",
            city="Town",
            state="ST",
            patient_id="P900",
        )
        # Wallet auto-created by signal.
        self.wallet = PatientWallet.objects.get(patient=self.patient)

    def test_individual_credit_then_debit_nets(self):
        self.wallet.credit(Decimal("100.00"), description="topup")
        self.wallet.debit(Decimal("30.00"), description="charge")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("70.00"))

        # balance_after recorded on the latest txn matches the wallet.
        latest = WalletTransaction.objects.filter(
            patient_wallet=self.wallet
        ).latest("created_at")
        self.assertEqual(latest.balance_after, Decimal("70.00"))

    def test_credit_routes_to_shared_wallet(self):
        shared = SharedWallet.objects.create(wallet_name="Family", wallet_type="family")
        self.wallet.shared_wallet = shared
        self.wallet.save(update_fields=["shared_wallet"])

        self.wallet.credit(Decimal("50.00"), description="shared topup")

        shared.refresh_from_db()
        self.wallet.refresh_from_db()
        # Money lands on the shared wallet, NOT the individual one.
        self.assertEqual(shared.balance, Decimal("50.00"))
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertTrue(
            WalletTransaction.objects.filter(shared_wallet=shared).exists()
        )

    def test_debit_routes_to_shared_wallet(self):
        shared = SharedWallet.objects.create(
            wallet_name="Corp", wallet_type="corporate", balance=Decimal("200.00")
        )
        self.wallet.shared_wallet = shared
        self.wallet.save(update_fields=["shared_wallet"])

        self.wallet.debit(Decimal("80.00"), description="shared charge")

        shared.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(shared.balance, Decimal("120.00"))
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
