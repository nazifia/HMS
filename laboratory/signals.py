from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone
from django.db import models
from decimal import Decimal
from .models import TestResult, TestRequest, Test
from billing.models import Invoice, Payment


@receiver(post_save, sender=TestResult)
def update_revenue_on_test_result_save(sender, instance, created, **kwargs):
    """
    Update revenue analysis when a test result is created or updated.
    This ensures revenue calculations reflect the latest test completion status.
    """
    # Clear revenue-related cache keys
    cache_keys_to_clear = [
        'lab_revenue_daily',
        'lab_revenue_monthly', 
        'lab_revenue_yearly',
        f'lab_revenue_doctor_{instance.test_request.doctor.id}',
        f'lab_revenue_test_{instance.test.id}',
        'lab_statistics_overall'
    ]
    
    for key in cache_keys_to_clear:
        cache.delete(key)
    
    # Update test request status if all tests are completed
    test_request = instance.test_request
    total_tests = test_request.tests.count()
    completed_results = TestResult.objects.filter(test_request=test_request).count()
    
    if completed_results >= total_tests and test_request.status != 'completed':
        test_request.status = 'completed'
        test_request.save()


@receiver(post_delete, sender=TestResult)
def update_revenue_on_test_result_delete(sender, instance, **kwargs):
    """
    Update revenue analysis when a test result is deleted.
    """
    # Clear revenue-related cache keys
    cache_keys_to_clear = [
        'lab_revenue_daily',
        'lab_revenue_monthly', 
        'lab_revenue_yearly',
        f'lab_revenue_doctor_{instance.test_request.doctor.id}',
        f'lab_revenue_test_{instance.test.id}',
        'lab_statistics_overall'
    ]
    
    for key in cache_keys_to_clear:
        cache.delete(key)
    
    # Update test request status if needed
    test_request = instance.test_request
    remaining_results = TestResult.objects.filter(test_request=test_request).count()
    
    if remaining_results == 0 and test_request.status == 'completed':
        test_request.status = 'processing'
        test_request.save()


@receiver(post_save, sender=Payment)
def update_revenue_on_payment(sender, instance, created, **kwargs):
    """
    Update revenue analysis when a payment is made for laboratory services.
    """
    # Check if this payment is for a laboratory invoice
    if hasattr(instance.invoice, 'lab_test_request'):
        # Clear revenue-related cache keys
        cache_keys_to_clear = [
            'lab_revenue_daily',
            'lab_revenue_monthly', 
            'lab_revenue_yearly',
            'lab_payment_statistics',
            'lab_statistics_overall'
        ]
        
        for key in cache_keys_to_clear:
            cache.delete(key)
        
        # Update invoice amount_paid
        total_payments = Payment.objects.filter(invoice=instance.invoice).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        instance.invoice.amount_paid = total_payments
        instance.invoice.save()


@receiver(post_save, sender=TestRequest)
def update_revenue_on_test_request_change(sender, instance, created, **kwargs):
    """
    Update revenue analysis when test request status changes.
    """
    if not created:  # Only for updates, not new creations
        # Clear revenue-related cache keys
        cache_keys_to_clear = [
            'lab_revenue_daily',
            'lab_revenue_monthly', 
            'lab_revenue_yearly',
            f'lab_revenue_doctor_{instance.doctor.id}',
            'lab_statistics_overall'
        ]
        
        for key in cache_keys_to_clear:
            cache.delete(key)


@receiver(post_save, sender=Test)
def update_revenue_on_test_price_change(sender, instance, created, **kwargs):
    """
    Update revenue analysis when test prices are modified.
    """
    if not created:  # Only for price updates
        # Clear all revenue-related cache keys since price changes affect calculations
        cache_keys_to_clear = [
            'lab_revenue_daily',
            'lab_revenue_monthly', 
            'lab_revenue_yearly',
            f'lab_revenue_test_{instance.id}',
            'lab_statistics_overall'
        ]
        
        for key in cache_keys_to_clear:
            cache.delete(key)


def clear_all_lab_revenue_cache():
    """
    Utility function to clear all laboratory revenue-related cache.
    Can be called manually when needed.
    """
    cache_patterns = [
        'lab_revenue_*',
        'lab_statistics_*',
        'lab_payment_*'
    ]
    
    # Note: This is a simplified approach. In production, you might want to use
    # a more sophisticated cache invalidation strategy with cache versioning
    cache.clear()
