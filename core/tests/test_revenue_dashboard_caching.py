"""Guards the revenue-dashboard query reductions.

Trend caching and calculator reuse are pure caching, so the only thing worth
testing is that the cached/reused path returns the same numbers as the uncached
path. The specialty-department breakdown swapped per-department queries for
grouped ones, so it is checked against the per-department queries it replaced.
"""

from decimal import Decimal

from django.apps import apps
from django.core.cache import cache
from django.db.models import Count, Sum
from django.test import TestCase
from django.utils import timezone

from billing.models import Payment as BillingPayment
from core.department_revenue_utils import (
    DepartmentRevenueCalculator,
    RevenueComparisonAnalyzer,
)
from core.revenue_point_analyzer import (
    SPECIALTY_DEPARTMENTS,
    RevenuePointBreakdownAnalyzer,
)
from core.revenue_views import _get_date_range, _get_previous_period
from patients.models import WalletTransaction


class RevenueDashboardCachingTests(TestCase):
    def setUp(self):
        self.start_date, self.end_date = _get_date_range('current_month')
        cache.clear()

    def test_cached_trends_match_uncached(self):
        analyzer = RevenuePointBreakdownAnalyzer(self.start_date, self.end_date)
        uncached = analyzer._get_revenue_point_trends()

        # Second call hits the per-month cache populated by the first.
        cached = RevenuePointBreakdownAnalyzer(
            self.start_date, self.end_date
        )._get_revenue_point_trends()

        self.assertEqual(list(uncached.keys()), list(cached.keys()))
        self.assertEqual(uncached, cached)

    def test_memoized_calculator_repeats_identical_results(self):
        calculator = DepartmentRevenueCalculator(self.start_date, self.end_date)
        first = calculator.get_pharmacy_detailed_revenue()
        self.assertEqual(first, calculator.get_pharmacy_detailed_revenue())

    def test_injected_calculator_matches_freshly_built_one(self):
        previous_start, previous_end = _get_previous_period(self.start_date, self.end_date)
        calculator = DepartmentRevenueCalculator(self.start_date, self.end_date)
        calculator.get_pharmacy_detailed_revenue()  # warm the memo

        injected = RevenueComparisonAnalyzer(
            self.start_date, self.end_date, previous_start, previous_end,
            current_calculator=calculator,
        ).get_period_comparison()

        fresh = RevenueComparisonAnalyzer(
            self.start_date, self.end_date, previous_start, previous_end,
        ).get_period_comparison()

        self.assertEqual(injected, fresh)


class SpecialtyDepartmentBreakdownTests(TestCase):
    """The grouped breakdown must match the per-department queries it replaced."""

    def setUp(self):
        self.start_date, self.end_date = _get_date_range('current_month')
        self.analyzer = RevenuePointBreakdownAnalyzer(self.start_date, self.end_date)

    def _per_department_totals(self, department):
        """The per-department invoice aggregate the grouped query replaced."""
        payments = BillingPayment.objects.filter(
            payment_date__date__range=[self.start_date, self.end_date],
            invoice__source_app=department,
        ).aggregate(amount=Sum('amount'), count=Count('id'))

        return payments['amount'] or Decimal('0.00'), payments['count'] or 0

    def _make_wallet_transaction(self, description, amount):
        from patients.models import Patient, PatientWallet

        patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            date_of_birth='1990-01-01',
            gender='male',
            address='1 Test Street',
            city='Testville',
            state='Test State',
            patient_id=f'TEST-{description[:8]}',
        )
        wallet = PatientWallet.objects.get_or_create(patient=patient)[0]
        return WalletTransaction.objects.create(
            patient=patient,
            patient_wallet=wallet,
            transaction_type='credit',
            amount=amount,
            balance_after=amount,
            description=description,
            reference_number=f'REF-{description[:8]}',
            created_at=timezone.now(),
        )

    def test_every_specialty_department_resolves_to_a_model(self):
        # The old hard-coded name table was wrong for family_planning and
        # gynae_emergency, and a single failing import silently zeroed the
        # record count for every department listed after them.
        for department in SPECIALTY_DEPARTMENTS:
            with self.subTest(department=department):
                self.assertIsNotNone(
                    apps.get_model(department, f'{department.capitalize()}Record')
                )

    def test_grouped_breakdown_matches_per_department_queries(self):
        breakdown = self.analyzer._get_specialty_departments_breakdown()

        for department in SPECIALTY_DEPARTMENTS:
            with self.subTest(department=department):
                revenue, transactions = self._per_department_totals(department)
                self.assertEqual(breakdown[department]['revenue'], revenue)
                self.assertEqual(breakdown[department]['transactions'], transactions)

    def test_wallet_descriptions_do_not_leak_into_specialty_revenue(self):
        # "Payment for Invoice ..." contains "ent", and every such wallet row is
        # already counted as a BillingPayment against its own department, so a
        # description match must contribute nothing.
        self._make_wallet_transaction('Payment for Invoice #INV1 via Wallet', Decimal('5000.00'))
        self._make_wallet_transaction('Dental treatment balance advance', Decimal('7000.00'))

        breakdown = self.analyzer._get_specialty_departments_breakdown()

        for department in SPECIALTY_DEPARTMENTS:
            with self.subTest(department=department):
                self.assertEqual(breakdown[department]['revenue'], Decimal('0.00'))
                self.assertEqual(breakdown[department]['transactions'], 0)

    def test_detail_view_revenue_excludes_wallet_descriptions(self):
        self._make_wallet_transaction('Payment for Invoice #INV2 via Wallet', Decimal('9000.00'))

        calculator = DepartmentRevenueCalculator(self.start_date, self.end_date)
        detail = calculator.get_specialty_department_detailed_revenue('ent')

        self.assertEqual(detail['total_revenue'], Decimal('0.00'))
        self.assertNotIn('wallet_revenue', detail)

    def test_record_counts_reach_departments_after_the_old_import_break(self):
        # ophthalmic sat after the failing import, so its count was always 0.
        record_model = apps.get_model('ophthalmic', 'OphthalmicRecord')
        expected = record_model.objects.filter(
            created_at__date__range=[self.start_date, self.end_date]
        ).count()

        counts = self.analyzer._get_specialty_record_counts()

        self.assertEqual(counts['ophthalmic'], expected)
        self.assertEqual(set(counts), set(SPECIALTY_DEPARTMENTS))
