"""Wallet money-in/money-out gets a printable roll receipt too."""
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from patients.models import Patient, PatientWallet, WalletTransaction


class WalletTransactionReceiptTest(TestCase):
    def test_receipt_renders_amount_and_balance(self):
        user = CustomUser.objects.create_user(
            phone_number="9101", username="teller", password="pw"
        )
        user.user_permissions.add(
            Permission.objects.get(codename="print_paymentreceipt")
        )
        self.client.force_login(user)
        patient = Patient.objects.create(
            first_name="Wal", last_name="Let", date_of_birth="1990-01-01",
            gender="F", address="2 St", city="Town", state="ST", patient_id="P961",
        )
        wallet = PatientWallet.objects.get(patient=patient)
        txn = WalletTransaction.objects.create(
            patient_wallet=wallet, patient=patient, transaction_type="deposit",
            amount=Decimal("2500.00"), balance_after=Decimal("2500.00"),
            description="Cash deposit at billing office", created_by=user,
        )

        body = self.client.get(
            reverse("patients:wallet_transaction_receipt", args=[txn.id])
        ).content.decode()

        self.assertIn("DEPOSIT", body)
        self.assertIn("2,500.00", body)
        self.assertIn("Cash deposit at billing office", body)
