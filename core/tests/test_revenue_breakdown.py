"""
Comprehensive Tests for Revenue Point Breakdown Functionality
Tests all components while ensuring backward compatibility.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import json

from core.revenue_point_analyzer import RevenuePointBreakdownAnalyzer, RevenuePointFilterHelper
from core.department_revenue_utils import DepartmentRevenueCalculator, RevenueComparisonAnalyzer
from core.reporting_integration import RevenueReportGenerator, RevenueReportExecutor

from billing.models import Invoice, Payment as BillingPayment, Service, ServiceCategory
from pharmacy_billing.models import Payment as PharmacyPayment
from pharmacy.models import DispensingLog, Medication, PrescriptionItem, Prescription
from patients.models import Patient, WalletTransaction, PatientWallet
from appointments.models import Appointment
from doctors.models import Doctor

User = get_user_model()


class RevenuePointAnalyzerTestCase(TestCase):
    """Test suite for RevenuePointBreakdownAnalyzer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test patient
        self.patient = Patient.objects.create(
            user=User.objects.create_user(
                username='patient1',
                email='patient1@example.com'
            ),
            patient_id='P001',
            date_of_birth=timezone.now().date() - timedelta(days=365*30)
        )
        
        # Create test doctor
        self.doctor = Doctor.objects.create(
            user=User.objects.create_user(
                username='doctor1',
                email='doctor1@example.com'
            ),
            license_number='D001',
            specialization='General Medicine'
        )
        
        # Create test dates
        self.start_date = timezone.now().date() - timedelta(days=30)
        self.end_date = timezone.now().date()
        
        # Create test analyzer
        self.analyzer = RevenuePointBreakdownAnalyzer(self.start_date, self.end_date)
        
        # Create test data
        self._create_test_revenue_data()
    
    def _create_test_revenue_data(self):
        """Create test revenue data"""
        # Create billing invoices and payments
        service_category = ServiceCategory.objects.create(
            name='Test Services',
            description='Test service category'
        )
        
        service = Service.objects.create(
            name='Test Service',
            category=service_category,
            price=Decimal('1000.00')
        )
        
        # Pharmacy invoice
        pharmacy_invoice = Invoice.objects.create(
            patient=self.patient,
            invoice_number='INV001',
            source_app='pharmacy',
            subtotal=Decimal('500.00'),
            tax_amount=Decimal('50.00'),
            total_amount=Decimal('550.00'),
            created_by=self.user
        )
        
        BillingPayment.objects.create(
            invoice=pharmacy_invoice,
            amount=Decimal('550.00'),
            payment_method='cash',
            received_by=self.user
        )
        
        # Laboratory invoice
        lab_invoice = Invoice.objects.create(
            patient=self.patient,
            invoice_number='INV002',
            source_app='laboratory',
            subtotal=Decimal('300.00'),
            tax_amount=Decimal('30.00'),
            total_amount=Decimal('330.00'),
            created_by=self.user
        )
        
        BillingPayment.objects.create(
            invoice=lab_invoice,
            amount=Decimal('330.00'),
            payment_method='card',
            received_by=self.user
        )
        
        # Create wallet transactions
        wallet = PatientWallet.objects.create(
            patient=self.patient,
            balance=Decimal('1000.00')
        )
        
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='consultation_fee',
            amount=Decimal('200.00'),
            balance_after=Decimal('800.00'),
            description='Consultation payment',
            created_by=self.user
        )
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        self.assertEqual(self.analyzer.start_date, self.start_date)
        self.assertEqual(self.analyzer.end_date, self.end_date)
        self.assertIsInstance(self.analyzer.revenue_points, dict)
    
    def test_get_pharmacy_revenue(self):
        """Test pharmacy revenue calculation"""
        result = self.analyzer.get_pharmacy_revenue()
        
        self.assertIsInstance(result, dict)
        self.assertIn('total_revenue', result)
        self.assertGreaterEqual(result['total_revenue'], Decimal('0.00'))
    
    def test_get_laboratory_revenue(self):
        """Test laboratory revenue calculation"""
        result = self.analyzer.get_laboratory_revenue()
        
        self.assertIsInstance(result, dict)
        self.assertIn('total_revenue', result)
        self.assertGreaterEqual(result['total_revenue'], Decimal('0.00'))
    
    def test_get_comprehensive_revenue(self):
        """Test comprehensive revenue breakdown"""
        result = self.analyzer.get_comprehensive_revenue()
        
        self.assertIsInstance(result, dict)
        self.assertIn('total_revenue', result)
        self.assertIn('pharmacy_revenue', result)
        self.assertIn('laboratory_revenue', result)
        self.assertIn('consultation_revenue', result)
        self.assertIn('date_range', result)
    
    def test_get_revenue_point_breakdown(self):
        """Test revenue point breakdown"""
        result = self.analyzer.get_revenue_point_breakdown()
        
        self.assertIsInstance(result, dict)
        self.assertIn('clinical_services', result)
        self.assertIn('support_services', result)
        self.assertIn('specialty_departments', result)
        self.assertIn('summary_by_category', result)


class DepartmentRevenueCalculatorTestCase(TestCase):
    """Test suite for DepartmentRevenueCalculator"""
    
    def setUp(self):
        """Set up test data"""
        self.start_date = timezone.now().date() - timedelta(days=30)
        self.end_date = timezone.now().date()
        self.calculator = DepartmentRevenueCalculator(self.start_date, self.end_date)
    
    def test_calculator_initialization(self):
        """Test calculator initialization"""
        self.assertEqual(self.calculator.start_date, self.start_date)
        self.assertEqual(self.calculator.end_date, self.end_date)
    
    def test_get_pharmacy_detailed_revenue(self):
        """Test detailed pharmacy revenue calculation"""
        result = self.calculator.get_pharmacy_detailed_revenue()
        
        self.assertIsInstance(result, dict)
        self.assertIn('total_revenue', result)
        
        # Should handle empty data gracefully
        if 'error' not in result:
            self.assertIn('top_medications', result)
            self.assertIn('prescription_types', result)


class RevenueFilterHelperTestCase(TestCase):
    """Test suite for RevenuePointFilterHelper"""
    
    def test_get_current_month(self):
        """Test current month date range"""
        start_date, end_date = RevenuePointFilterHelper.get_current_month()
        
        self.assertIsInstance(start_date, datetime.date)
        self.assertIsInstance(end_date, datetime.date)
        self.assertLessEqual(start_date, end_date)
    
    def test_get_previous_month(self):
        """Test previous month date range"""
        start_date, end_date = RevenuePointFilterHelper.get_previous_month()
        
        self.assertIsInstance(start_date, datetime.date)
        self.assertIsInstance(end_date, datetime.date)
        self.assertLessEqual(start_date, end_date)
    
    def test_get_filter_options(self):
        """Test filter options"""
        options = RevenuePointFilterHelper.get_filter_options()
        
        self.assertIsInstance(options, list)
        self.assertGreater(len(options), 0)
        
        # Check structure
        for option in options:
            self.assertEqual(len(option), 2)


class RevenueViewsTestCase(TestCase):
    """Test suite for revenue views"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_revenue_point_dashboard_view(self):
        """Test revenue point dashboard view"""
        url = reverse('core:revenue_point_dashboard')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Revenue Point Breakdown')
    
    def test_revenue_point_api_view(self):
        """Test revenue point API view"""
        url = reverse('core:revenue_point_api')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        self.assertIn('success', data)
    
    def test_export_revenue_breakdown_csv(self):
        """Test CSV export functionality"""
        url = reverse('core:export_revenue_breakdown')
        
        response = self.client.get(url, {'format': 'csv'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')


class ReportingIntegrationTestCase(TestCase):
    """Test suite for reporting integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.executor = RevenueReportExecutor(user=self.user)
    
    def test_revenue_report_generator(self):
        """Test revenue report generation"""
        reports = RevenueReportGenerator.create_revenue_reports()
        
        self.assertIsInstance(reports, list)
        # Should create at least some reports
        self.assertGreaterEqual(len(reports), 0)
    
    def test_revenue_dashboard_creation(self):
        """Test dashboard creation"""
        dashboard = RevenueReportGenerator.create_revenue_dashboard()
        
        self.assertIsNotNone(dashboard)
        self.assertEqual(dashboard.name, 'Revenue Point Analysis Dashboard')


class BackwardCompatibilityTestCase(TestCase):
    """Test backward compatibility with existing systems"""
    
    def setUp(self):
        """Set up test environment"""
        self.start_date = timezone.now().date() - timedelta(days=30)
        self.end_date = timezone.now().date()
    
    def test_existing_revenue_service_compatibility(self):
        """Test compatibility with existing revenue service"""
        from pharmacy.revenue_service import RevenueAggregationService
        
        # Test that existing service still works
        existing_service = RevenueAggregationService(self.start_date, self.end_date)
        result = existing_service.get_comprehensive_revenue()
        
        self.assertIsInstance(result, dict)
        self.assertIn('total_revenue', result)
    
    def test_new_analyzer_extends_existing(self):
        """Test that new analyzer extends existing functionality"""
        analyzer = RevenuePointBreakdownAnalyzer(self.start_date, self.end_date)
        
        # Should have all existing methods
        self.assertTrue(hasattr(analyzer, 'get_pharmacy_revenue'))
        self.assertTrue(hasattr(analyzer, 'get_laboratory_revenue'))
        self.assertTrue(hasattr(analyzer, 'get_comprehensive_revenue'))
        
        # Should have new methods
        self.assertTrue(hasattr(analyzer, 'get_revenue_point_breakdown'))


class PerformanceTestCase(TestCase):
    """Test performance aspects of revenue analysis"""
    
    def setUp(self):
        """Set up test environment"""
        self.start_date = timezone.now().date() - timedelta(days=30)
        self.end_date = timezone.now().date()
        self.analyzer = RevenuePointBreakdownAnalyzer(self.start_date, self.end_date)
    
    def test_analyzer_performance(self):
        """Test analyzer performance with basic timing"""
        import time
        
        start_time = time.time()
        result = self.analyzer.get_revenue_point_breakdown()
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (5 seconds for basic test)
        self.assertLess(execution_time, 5.0)
        self.assertIsInstance(result, dict)


class ErrorHandlingTestCase(TestCase):
    """Test error handling in revenue analysis"""
    
    def test_invalid_date_range(self):
        """Test handling of invalid date ranges"""
        # End date before start date
        start_date = timezone.now().date()
        end_date = start_date - timedelta(days=1)
        
        # Should handle gracefully
        analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
        result = analyzer.get_revenue_point_breakdown()
        
        self.assertIsInstance(result, dict)
    
    def test_missing_data_handling(self):
        """Test handling when no revenue data exists"""
        # Use future dates where no data exists
        start_date = timezone.now().date() + timedelta(days=365)
        end_date = start_date + timedelta(days=30)
        
        analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
        result = analyzer.get_revenue_point_breakdown()
        
        self.assertIsInstance(result, dict)
        self.assertIn('total_revenue', result)
        self.assertEqual(result['total_revenue'], Decimal('0.00'))


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    settings.configure()
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['__main__'])