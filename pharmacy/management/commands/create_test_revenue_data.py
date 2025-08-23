from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import random

from patients.models import Patient, PatientWallet, WalletTransaction
from billing.models import Invoice, Payment as BillingPayment, Service
from pharmacy_billing.models import Payment as PharmacyPayment
from pharmacy.models import DispensingLog, Prescription, PrescriptionItem, Medication
from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'Create test revenue data for testing the comprehensive revenue analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of test data to create (default: 30)'
        )

    def handle(self, *args, **options):
        days = options['days']
        
        self.stdout.write(f'Creating test revenue data for {days} days...')
        
        # Create test data
        self.create_test_patients()
        self.create_test_services()
        self.create_test_wallet_transactions(days)
        self.create_test_billing_data(days)
        self.create_test_pharmacy_data(days)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created test revenue data for {days} days')
        )

    def create_test_patients(self):
        """Create test patients if they don't exist"""
        for i in range(5):
            patient_id = f'TEST{i+1:03d}'
            patient, created = Patient.objects.get_or_create(
                patient_id=patient_id,
                defaults={
                    'first_name': f'Test',
                    'last_name': f'Patient{i+1}',
                    'phone_number': f'080{random.randint(10000000, 99999999)}',
                    'email': f'test{i+1}@example.com',
                    'gender': random.choice(['male', 'female']),
                    'date_of_birth': timezone.now().date() - timedelta(days=random.randint(6570, 25550))  # 18-70 years old
                }
            )
            
            if created:
                self.stdout.write(f'Created test patient: {patient.get_full_name()}')
                
            # Create wallet for patient
            wallet, wallet_created = PatientWallet.objects.get_or_create(
                patient=patient,
                defaults={'balance': Decimal('1000.00')}
            )
            
            if wallet_created:
                self.stdout.write(f'Created wallet for patient: {patient.get_full_name()}')

    def create_test_services(self):
        """Create test services if they don't exist"""
        services = [
            ('Laboratory Test', 'laboratory', Decimal('500.00')),
            ('Consultation', 'appointment', Decimal('2000.00')),
            ('Surgery', 'theatre', Decimal('50000.00')),
            ('Admission', 'inpatient', Decimal('5000.00')),
            ('General Service', 'billing', Decimal('1000.00')),
        ]
        
        for name, category, price in services:
            service, created = Service.objects.get_or_create(
                name=name,
                defaults={
                    'price': price,
                    'tax_percentage': Decimal('5.0'),
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created service: {name}')

    def create_test_wallet_transactions(self, days):
        """Create test wallet transactions"""
        patients = list(Patient.objects.filter(patient_id__startswith='TEST'))
        transaction_types = [
            'payment', 'lab_test_payment', 'pharmacy_payment', 
            'consultation_fee', 'procedure_fee', 'admission_fee'
        ]
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            
            # Create 2-5 transactions per day
            num_transactions = random.randint(2, 5)
            
            for _ in range(num_transactions):
                patient = random.choice(patients)
                wallet = patient.wallet
                transaction_type = random.choice(transaction_types)
                amount = Decimal(str(random.randint(50, 5000)))
                
                # Create transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type=transaction_type,
                    amount=amount,
                    balance_after=wallet.balance - amount,
                    description=f'Test {transaction_type} transaction',
                    created_at=timezone.make_aware(
                        timezone.datetime.combine(current_date, timezone.datetime.min.time())
                    ) + timedelta(hours=random.randint(8, 18))
                )
                
        self.stdout.write(f'Created wallet transactions for {days} days')

    def create_test_billing_data(self, days):
        """Create test billing invoices and payments"""
        patients = list(Patient.objects.filter(patient_id__startswith='TEST'))
        services = list(Service.objects.all())
        source_apps = ['laboratory', 'appointment', 'theatre', 'inpatient', 'billing']
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            
            # Create 1-3 invoices per day
            num_invoices = random.randint(1, 3)
            
            for _ in range(num_invoices):
                patient = random.choice(patients)
                service = random.choice(services)
                source_app = random.choice(source_apps)
                
                # Create invoice
                invoice = Invoice.objects.create(
                    patient=patient,
                    total_amount=service.price,
                    subtotal=service.price,
                    tax_amount=Decimal('0.00'),
                    discount_amount=Decimal('0.00'),
                    status='paid',
                    source_app=source_app,
                    invoice_date=current_date,
                    due_date=current_date + timedelta(days=30),  # Add due_date field
                    created_at=timezone.make_aware(
                        timezone.datetime.combine(current_date, timezone.datetime.min.time())
                    ) + timedelta(hours=random.randint(8, 18))
                )
                
                # Create payment for the invoice
                BillingPayment.objects.create(
                    invoice=invoice,
                    amount=service.price,
                    payment_method=random.choice(['cash', 'card', 'transfer']),
                    payment_date=current_date,
                    received_by=None  # We'll leave this as None for test data
                )
                
        self.stdout.write(f'Created billing data for {days} days')

    def create_test_pharmacy_data(self, days):
        """Create test pharmacy billing payments and dispensing logs"""
        patients = list(Patient.objects.filter(patient_id__startswith='TEST'))
        
        # Create a test medication if it doesn't exist
        medication, created = Medication.objects.get_or_create(
            name='Test Medication',
            defaults={
                'generic_name': 'Test Generic',
                'strength': '500mg',
                'price': Decimal('100.00'),
                'is_active': True
            }
        )
        if created:
            self.stdout.write('Created test medication')
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            
            # Create 1-2 pharmacy transactions per day
            num_transactions = random.randint(1, 2)
            
            for _ in range(num_transactions):
                patient = random.choice(patients)
                amount = Decimal(str(random.randint(100, 1000)))
                
                # Create pharmacy payment
                PharmacyPayment.objects.create(
                    amount=amount,
                    payment_method=random.choice(['cash', 'card', 'wallet']),
                    payment_date=current_date,
                    transaction_id=f'TEST{random.randint(1000, 9999)}',
                    notes='Test pharmacy payment'
                )
                
        self.stdout.write(f'Created pharmacy data for {days} days')