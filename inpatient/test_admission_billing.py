from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from accounts.models import CustomUser
from patients.models import Patient, PatientWallet, WalletTransaction
from inpatient.models import Ward, Bed, Admission

class AdmissionBillingTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            first_name='Test',
            last_name='User',
            phone_number='1234567890'
        )
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='M',
            address='123 Main St',
            city='Anytown',
            state='CA',
            country='USA',
            patient_id='PAT001'
        )
        self.ward = Ward.objects.create(
            name='General Ward',
            ward_type='general',
            floor='1',
            capacity=10,
            charge_per_day=Decimal('100.00')
        )
        self.bed = Bed.objects.create(
            ward=self.ward,
            bed_number='101',
            is_occupied=False
        )
        # Ensure patient has a wallet
        self.patient_wallet = PatientWallet.objects.get_or_create(patient=self.patient)[0]
        self.initial_balance = self.patient_wallet.balance

    def test_admission_debits_wallet_correctly(self):
        # Simulate admission for 1 day
        admission = Admission.objects.create(
            patient=self.patient,
            admission_date=timezone.now() - timedelta(days=1),
            bed=self.bed,
            diagnosis='Fever',
            attending_doctor=self.user,
            reason_for_admission='High fever',
            created_by=self.user
        )
        admission.discharge_date = timezone.now() # Set discharge date to calculate cost
        admission.save() # Trigger save to update billed_amount and wallet

        expected_cost = Decimal(str(self.ward.charge_per_day * admission.get_duration()))
        # If wallet balance is sufficient, billed_amount should be 0, otherwise it's the remaining cost
        if self.initial_balance >= expected_cost:
            self.assertEqual(admission.billed_amount, Decimal('0.00'))
            self.patient_wallet.refresh_from_db()
            self.assertEqual(self.patient_wallet.balance, self.initial_balance - expected_cost)
        else:
            self.assertEqual(admission.billed_amount, expected_cost - self.initial_balance)
            self.patient_wallet.refresh_from_db()
            self.assertEqual(self.patient_wallet.balance, self.initial_balance - min(expected_cost, self.initial_balance))

        # Verify transaction record
        transaction = WalletTransaction.objects.filter(
            wallet=self.patient_wallet,
            transaction_type='admission_fee'
        ).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, expected_cost)
        self.assertEqual(transaction.balance_after, self.patient_wallet.balance)

    def test_admission_cost_increase_debits_more(self):
        # Initial admission with 1 day cost
        admission = Admission.objects.create(
            patient=self.patient,
            admission_date=timezone.now() - timedelta(days=1),
            bed=self.bed,
            diagnosis='Fever',
            attending_doctor=self.user,
            reason_for_admission='High fever',
            created_by=self.user
        )
        admission.discharge_date = timezone.now() # Set discharge date to calculate cost
        admission.save() # Trigger save to update billed_amount and wallet

        initial_billed_amount = Decimal(str(admission.billed_amount))
        self.patient_wallet.refresh_from_db()
        initial_wallet_balance = self.patient_wallet.balance

        # Simulate extending admission by 1 day (total 2 days)
        admission.discharge_date = timezone.now() + timedelta(days=1) # Extend by 1 day
        admission.save() # Trigger save to update billed_amount and wallet

        new_expected_cost = Decimal(str(self.ward.charge_per_day * admission.get_duration()))
        additional_cost = new_expected_cost - initial_billed_amount

        self.assertEqual(admission.billed_amount, initial_billed_amount + additional_cost)
        self.patient_wallet.refresh_from_db()
        self.assertEqual(self.patient_wallet.balance, initial_wallet_balance - additional_cost)

        # Verify transaction record for adjustment
        transaction = WalletTransaction.objects.filter(
            wallet=self.patient_wallet,
            transaction_type='admission_fee'
        ).order_by('-created_at').first() # Get the latest transaction
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, additional_cost)
        self.assertEqual(transaction.balance_after, self.patient_wallet.balance)

    def test_admission_cost_decrease_credits_back(self):
        # Initial admission with 2 days cost
        admission = Admission.objects.create(
            patient=self.patient,
            admission_date=timezone.now() - timedelta(days=2),
            bed=self.bed,
            diagnosis='Fever',
            attending_doctor=self.user,
            reason_for_admission='High fever',
            created_by=self.user
        )
        admission.discharge_date = timezone.now() # Set discharge date to calculate cost
        admission.save() # Trigger save to update billed_amount and wallet

        initial_billed_amount = Decimal(str(admission.billed_amount))
        self.patient_wallet.refresh_from_db()
        initial_wallet_balance = self.patient_wallet.balance

        # Simulate reducing admission to 1 day (total 1 day)
        admission.discharge_date = timezone.now() - timedelta(days=1) # Reduce to 1 day
        admission.save() # Trigger save to update billed_amount and wallet

        new_expected_cost = Decimal(str(self.ward.charge_per_day * admission.get_duration()))
        refund_amount = initial_billed_amount - new_expected_cost

        self.assertEqual(admission.billed_amount, initial_billed_amount - refund_amount)
        self.patient_wallet.refresh_from_db()
        self.assertEqual(self.patient_wallet.balance, initial_wallet_balance + refund_amount)
        self.patient_wallet.refresh_from_db()
        self.assertEqual(self.patient_wallet.balance, initial_wallet_balance + refund_amount)
        self.patient_wallet.refresh_from_db()
        self.assertEqual(self.patient_wallet.balance, initial_wallet_balance + refund_amount)

        # Verify transaction record for refund
        transaction = WalletTransaction.objects.filter(
            wallet=self.patient_wallet,
            transaction_type='admission_refund'
        ).order_by('-created_at').first() # Get the latest transaction
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, refund_amount)
        self.assertEqual(transaction.balance_after, self.patient_wallet.balance)

    def test_admission_no_cost_change_no_wallet_update(self):
        # Initial admission with 1 day cost
        admission = Admission.objects.create(
            patient=self.patient,
            admission_date=timezone.now() - timedelta(days=1),
            bed=self.bed,
            diagnosis='Fever',
            attending_doctor=self.user,
            reason_for_admission='High fever',
            created_by=self.user
        )
        admission.discharge_date = timezone.now() # Set discharge date to calculate cost
        admission.save() # Trigger save to update billed_amount and wallet

        initial_billed_amount = admission.billed_amount
        self.patient_wallet.refresh_from_db()
        initial_wallet_balance = self.patient_wallet.balance
        initial_transaction_count = WalletTransaction.objects.filter(wallet=self.patient_wallet).count()

        # Simulate saving admission without changing cost
        admission.diagnosis = 'Updated Fever Diagnosis'
        admission.save() # Trigger save

        self.assertEqual(admission.billed_amount, initial_billed_amount)
        self.patient_wallet.refresh_from_db()
        self.assertEqual(self.patient_wallet.balance, initial_wallet_balance)
        self.assertEqual(WalletTransaction.objects.filter(wallet=self.patient_wallet).count(), initial_transaction_count)