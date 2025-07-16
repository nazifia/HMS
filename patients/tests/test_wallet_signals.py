from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from patients.models import Patient, PatientWallet, WalletTransaction
from billing.models import Invoice, Payment, Service, ServiceCategory

User = get_user_model()

class WalletSignalsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password', phone_number='1234567890')
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='M',
            address='123 Main St',
            city='Anytown',
            state='CA',
            patient_id='P001'
        )
        # Wallet should be created automatically by signal
        self.patient_wallet = PatientWallet.objects.get(patient=self.patient)

        self.service_category = ServiceCategory.objects.create(name='Consultation')
        self.service = Service.objects.create(
            name='General Consultation',
            category=self.service_category,
            price=Decimal('500.00')
        )

        self.invoice = Invoice.objects.create(
            patient=self.patient,
            invoice_number='INV001',
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),
            subtotal=Decimal('500.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('500.00'),
            created_by=self.user
        )

    def test_patient_wallet_creation(self):
        """Test that a PatientWallet is created automatically for a new Patient."""
        self.assertIsNotNone(self.patient_wallet)
        self.assertEqual(self.patient_wallet.balance, Decimal('0.00'))

    def test_wallet_payment_debit(self):
        """
        Test that a wallet payment debits the patient's wallet and updates the invoice.
        The debit logic is primarily in Payment.save(), but signals ensure consistency.
        """
        initial_wallet_balance = Decimal('1000.00')
        self.patient_wallet.balance = initial_wallet_balance
        self.patient_wallet.save()

        payment_amount = Decimal('200.00')
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=payment_amount,
            payment_method='wallet',
            received_by=self.user
        )

        self.patient_wallet.refresh_from_db()
        self.invoice.refresh_from_db()

        expected_balance = initial_wallet_balance - payment_amount
        self.assertEqual(self.patient_wallet.balance, expected_balance)
        self.assertEqual(self.invoice.amount_paid, payment_amount)
        self.assertEqual(self.invoice.status, 'partially_paid')

        # Verify WalletTransaction record
        transaction = WalletTransaction.objects.get(wallet=self.patient_wallet, payment=payment)
        self.assertEqual(transaction.amount, payment_amount)
        self.assertEqual(transaction.transaction_type, 'payment')
        self.assertEqual(transaction.balance_after, expected_balance)

    def test_non_wallet_payment_updates_invoice(self):
        """Test that a non-wallet payment updates the invoice amount_paid."""
        initial_invoice_amount_paid = self.invoice.amount_paid
        payment_amount = Decimal('150.00')
        Payment.objects.create(
            invoice=self.invoice,
            amount=payment_amount,
            payment_method='cash',
            received_by=self.user
        )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, initial_invoice_amount_paid + payment_amount)
        self.assertEqual(self.invoice.status, 'partially_paid')

    def test_update_wallet_payment_amount_increase(self):
        """Test increasing an existing wallet payment amount."""
        initial_wallet_balance = Decimal('1000.00')
        self.patient_wallet.balance = initial_wallet_balance
        self.patient_wallet.save()

        # Create initial payment
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('100.00'),
            payment_method='wallet',
            received_by=self.user
        )
        self.patient_wallet.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(self.patient_wallet.balance, initial_wallet_balance - Decimal('100.00'))
        self.assertEqual(self.invoice.amount_paid, Decimal('100.00'))

        # Update payment amount
        payment.amount = Decimal('300.00') # Increase by 200
        payment.save()

        self.patient_wallet.refresh_from_db()
        self.invoice.refresh_from_db()

        expected_balance = initial_wallet_balance - Decimal('300.00')
        self.assertEqual(self.patient_wallet.balance, expected_balance)
        self.assertEqual(self.invoice.amount_paid, Decimal('300.00'))

        # Verify adjustment transaction
        transaction = WalletTransaction.objects.filter(
            wallet=self.patient_wallet,
            transaction_type='adjustment',
            amount=Decimal('200.00')
        ).first()
        self.assertIsNotNone(transaction)
        self.assertIn('Increased payment', transaction.description)

    def test_update_wallet_payment_amount_decrease(self):
        """Test decreasing an existing wallet payment amount."""
        initial_wallet_balance = Decimal('1000.00')
        self.patient_wallet.balance = initial_wallet_balance
        self.patient_wallet.save()

        # Create initial payment
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('500.00'),
            payment_method='wallet',
            received_by=self.user
        )
        self.patient_wallet.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(self.patient_wallet.balance, initial_wallet_balance - Decimal('500.00'))
        self.assertEqual(self.invoice.amount_paid, Decimal('500.00'))

        # Update payment amount
        payment.amount = Decimal('200.00') # Decrease by 300
        payment.save()

        self.patient_wallet.refresh_from_db()
        self.invoice.refresh_from_db()

        expected_balance = initial_wallet_balance - Decimal('200.00')
        self.assertEqual(self.patient_wallet.balance, expected_balance)
        self.assertEqual(self.invoice.amount_paid, Decimal('200.00'))

        # Verify adjustment transaction
        transaction = WalletTransaction.objects.filter(
            wallet=self.patient_wallet,
            transaction_type='adjustment',
            amount=Decimal('300.00')
        ).first()
        self.assertIsNotNone(transaction)
        self.assertIn('Decreased payment', transaction.description)

    def test_delete_wallet_payment(self):
        """Test that deleting a wallet payment credits the wallet back and adjusts the invoice."""
        initial_wallet_balance = Decimal('1000.00')
        self.patient_wallet.balance = initial_wallet_balance
        self.patient_wallet.save()

        payment_amount = Decimal('250.00')
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=payment_amount,
            payment_method='wallet',
            received_by=self.user
        )

        self.patient_wallet.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(self.patient_wallet.balance, initial_wallet_balance - payment_amount)
        self.assertEqual(self.invoice.amount_paid, payment_amount)

        # Delete the payment
        payment.delete()

        self.patient_wallet.refresh_from_db()
        self.invoice.refresh_from_db()

        self.assertEqual(self.patient_wallet.balance, initial_wallet_balance) # Wallet credited back
        self.assertEqual(self.invoice.amount_paid, Decimal('0.00')) # Invoice amount_paid reversed
        self.assertEqual(self.invoice.status, 'pending') # Status should revert if no other payments

        # Verify reversal transaction
        transaction = WalletTransaction.objects.filter(
            wallet=self.patient_wallet,
            transaction_type='reversal',
            amount=payment_amount
        ).first()
        self.assertIsNotNone(transaction)
        self.assertIn('Reversal: Payment', transaction.description)

    def test_invoice_status_update(self):
        """Test that invoice status updates correctly based on payments."""
        # Initial status is 'draft' (from invoice creation)
        self.assertEqual(self.invoice.status, 'draft')

        # Partially paid
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('200.00'),
            payment_method='cash',
            received_by=self.user
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'partially_paid')

        # Fully paid
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('300.00'), # Total 500
            payment_method='cash',
            received_by=self.user
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')

        # Overpayment (still 'paid')
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('100.00'),
            payment_method='cash',
            received_by=self.user
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')

    def test_admission_wallet_debit(self):
        """Test that admission fees debit the patient's wallet."""
        from inpatient.models import Admission, Ward, Bed

        # Create a ward and bed
        ward = Ward.objects.create(name='General Ward', ward_type='general', floor='1st', capacity=10, charge_per_day=Decimal('100.00'))
        bed = Bed.objects.create(ward=ward, bed_number='B1')

        initial_wallet_balance = Decimal('2000.00')
        self.patient_wallet.balance = initial_wallet_balance
        self.patient_wallet.save()

        # Create an admission
        admission = Admission.objects.create(
            patient=self.patient,
            bed=bed,
            diagnosis='Fever',
            status='admitted',
            attending_doctor=self.user,
            reason_for_admission='High fever',
            created_by=self.user
        )

        self.patient_wallet.refresh_from_db()
        admission.refresh_from_db()

        # Admission cost is negative, so abs() is used for debit amount
        expected_debit_amount = abs(admission.get_total_cost())
        expected_balance = initial_wallet_balance - expected_debit_amount

        self.assertEqual(self.patient_wallet.balance, expected_balance)
        self.assertEqual(admission.billed_amount, admission.get_total_cost())

        # Verify WalletTransaction record for admission fee
        transaction = WalletTransaction.objects.get(
            wallet=self.patient_wallet,
            transaction_type='admission_fee',
            amount=expected_debit_amount
        )
        self.assertIsNotNone(transaction)
        self.assertIn('Admission fees', transaction.description)

        # Test updating admission (e.g., duration changes, leading to more cost)
        # Simulate time passing for duration calculation
        admission.admission_date = timezone.now() - timezone.timedelta(days=2)
        admission.save()

        self.patient_wallet.refresh_from_db()
        admission.refresh_from_db()

        # The save method in Admission handles the delta billing
        # The billed_amount should now reflect the new total cost
        new_expected_debit_amount = abs(admission.get_total_cost())
        self.assertEqual(admission.billed_amount, admission.get_total_cost())
        # The wallet balance should have been debited by the difference
        # This requires careful calculation as the previous debit was for 1 day, now it's for 2 days.
        # The Admission.save() method's logic for wallet debit is designed to handle this delta.
        # So, the final balance should be initial_balance - new_total_cost.
        self.assertEqual(self.patient_wallet.balance, initial_wallet_balance - new_expected_debit_amount)

