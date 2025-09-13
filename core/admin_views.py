"""
Admin views for monitoring system operations including admission charges and sessions.
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.contrib.sessions.models import Session

from inpatient.models import Admission
from patients.models import WalletTransaction, PatientWallet
from inpatient.tasks import process_daily_admission_charges, process_single_admission_charge

logger = logging.getLogger(__name__)


@staff_member_required
def admission_charges_dashboard(request):
    """
    Dashboard for monitoring daily admission charge processing.
    """
    # Get date range for filtering
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)  # Last 30 days
    
    if request.GET.get('start_date'):
        try:
            start_date = datetime.strptime(request.GET['start_date'], '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if request.GET.get('end_date'):
        try:
            end_date = datetime.strptime(request.GET['end_date'], '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Get admission charge statistics
    daily_charges = WalletTransaction.objects.filter(
        transaction_type='daily_admission_charge',
        created_at__date__range=[start_date, end_date]
    ).select_related('wallet__patient', 'admission__bed__ward')
    
    # Calculate summary statistics
    total_charges = daily_charges.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id')
    )
    
    # Group by date
    daily_stats = {}
    for charge in daily_charges:
        date = charge.created_at.date()
        if date not in daily_stats:
            daily_stats[date] = {
                'date': date,
                'count': 0,
                'amount': Decimal('0.00'),
                'patients': set()
            }
        daily_stats[date]['count'] += 1
        daily_stats[date]['amount'] += charge.amount
        daily_stats[date]['patients'].add(charge.wallet.patient.get_full_name())
    
    # Convert to list and sort
    daily_stats_list = []
    for date, stats in daily_stats.items():
        stats['patient_count'] = len(stats['patients'])
        stats['patients'] = list(stats['patients'])
        daily_stats_list.append(stats)
    
    daily_stats_list.sort(key=lambda x: x['date'], reverse=True)
    
    # Get current active admissions
    active_admissions = Admission.objects.filter(
        status='admitted',
        discharge_date__isnull=True
    ).select_related('patient', 'bed__ward').count()
    
    # Get failed charges (negative wallet balances)
    negative_wallets = PatientWallet.objects.filter(
        balance__lt=0,
        is_active=True
    ).select_related('patient').count()
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_charges': total_charges,
        'daily_stats': daily_stats_list,
        'active_admissions': active_admissions,
        'negative_wallets': negative_wallets,
        'date_range_days': (end_date - start_date).days + 1
    }
    
    return render(request, 'admin/admission_charges_dashboard.html', context)


@staff_member_required
def session_monitoring_dashboard(request):
    """
    Dashboard for monitoring user sessions and security.
    """
    now = timezone.now()
    
    # Session statistics
    total_sessions = Session.objects.count()
    active_sessions = Session.objects.filter(expire_date__gt=now).count()
    expired_sessions = total_sessions - active_sessions
    
    # Recent session activity (last 24 hours)
    yesterday = now - timedelta(days=1)
    recent_sessions = Session.objects.filter(
        expire_date__gte=yesterday
    ).count()
    
    # Long-running sessions (potentially suspicious)
    long_session_threshold = 3 * 3600  # 3 hours
    long_sessions = Session.objects.filter(
        expire_date__gt=now + timedelta(seconds=long_session_threshold)
    ).count()
    
    # Session breakdown by age
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(weeks=1)
    
    session_stats = {
        'total': total_sessions,
        'active': active_sessions,
        'expired': expired_sessions,
        'recent_24h': recent_sessions,
        'long_running': long_sessions,
        'active_1h': Session.objects.filter(expire_date__gte=one_hour_ago).count(),
        'active_1d': Session.objects.filter(expire_date__gte=one_day_ago).count(),
        'active_1w': Session.objects.filter(expire_date__gte=one_week_ago).count(),
    }
    
    # Recent transactions for activity monitoring
    recent_activity = WalletTransaction.objects.filter(
        created_at__gte=yesterday
    ).select_related('wallet__patient', 'created_by').order_by('-created_at')[:50]
    
    context = {
        'session_stats': session_stats,
        'recent_activity': recent_activity,
        'current_time': now,
    }
    
    return render(request, 'admin/session_monitoring_dashboard.html', context)


@staff_member_required
def manual_charge_processing(request):
    """
    Interface for manually processing admission charges.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'process_today':
            # Process charges for today
            try:
                result = process_daily_admission_charges.delay()
                messages.success(request, f"Daily charge processing started. Task ID: {result.id}")
            except Exception as e:
                messages.error(request, f"Failed to start charge processing: {str(e)}")
        
        elif action == 'process_date':
            # Process charges for specific date
            target_date = request.POST.get('target_date')
            try:
                result = process_daily_admission_charges.delay(target_date)
                messages.success(request, f"Charge processing started for {target_date}. Task ID: {result.id}")
            except Exception as e:
                messages.error(request, f"Failed to start charge processing for {target_date}: {str(e)}")
        
        elif action == 'process_admission':
            # Process charge for specific admission
            admission_id = request.POST.get('admission_id')
            charge_date = request.POST.get('charge_date')
            try:
                result = process_single_admission_charge.delay(int(admission_id), charge_date)
                messages.success(request, f"Single admission charge processing started. Task ID: {result.id}")
            except Exception as e:
                messages.error(request, f"Failed to process admission charge: {str(e)}")
        
        return redirect('admin:manual_charge_processing')
    
    # Get active admissions for manual processing
    active_admissions = Admission.objects.filter(
        status='admitted',
        discharge_date__isnull=True
    ).select_related('patient', 'bed__ward', 'attending_doctor')[:100]
    
    context = {
        'active_admissions': active_admissions,
        'today': timezone.now().date(),
    }
    
    return render(request, 'admin/manual_charge_processing.html', context)


@staff_member_required
def wallet_management_dashboard(request):
    """
    Dashboard for managing patient wallets and transactions.
    """
    # Wallet statistics
    total_wallets = PatientWallet.objects.count()
    active_wallets = PatientWallet.objects.filter(is_active=True).count()
    
    # Balance statistics
    wallet_stats = PatientWallet.objects.aggregate(
        total_balance=Sum('balance'),
        avg_balance=Sum('balance') / Count('id') if Count('id') > 0 else 0
    )
    
    # Low/negative balance wallets
    low_balance_threshold = Decimal('100.00')
    low_balance_wallets = PatientWallet.objects.filter(
        balance__lt=low_balance_threshold,
        is_active=True
    ).select_related('patient').order_by('balance')[:20]
    
    negative_balance_wallets = PatientWallet.objects.filter(
        balance__lt=0,
        is_active=True
    ).select_related('patient').order_by('balance')[:20]
    
    # Recent large transactions
    large_transaction_threshold = Decimal('1000.00')
    recent_large_transactions = WalletTransaction.objects.filter(
        amount__gte=large_transaction_threshold,
        created_at__gte=timezone.now() - timedelta(days=7)
    ).select_related('wallet__patient', 'created_by').order_by('-created_at')[:20]
    
    context = {
        'total_wallets': total_wallets,
        'active_wallets': active_wallets,
        'wallet_stats': wallet_stats,
        'low_balance_wallets': low_balance_wallets,
        'negative_balance_wallets': negative_balance_wallets,
        'recent_large_transactions': recent_large_transactions,
        'low_balance_threshold': low_balance_threshold,
    }
    
    return render(request, 'admin/wallet_management_dashboard.html', context)


@staff_member_required
def system_health_check(request):
    """
    System health check for monitoring overall system status.
    """
    health_status = {
        'timestamp': timezone.now(),
        'status': 'healthy',
        'issues': []
    }
    
    try:
        # Check database connectivity
        PatientWallet.objects.count()
        
        # Check for stuck admissions (admitted for too long without charges)
        old_admissions = Admission.objects.filter(
            status='admitted',
            admission_date__lt=timezone.now() - timedelta(days=7),
            wallet_transactions__isnull=True
        ).count()
        
        if old_admissions > 0:
            health_status['issues'].append(f"{old_admissions} old admissions without charges")
        
        # Check for excessive negative balances
        excessive_negative = PatientWallet.objects.filter(
            balance__lt=-1000
        ).count()
        
        if excessive_negative > 0:
            health_status['issues'].append(f"{excessive_negative} wallets with excessive negative balances")
        
        # Check session health
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now()).count()
        if expired_sessions > 1000:
            health_status['issues'].append(f"{expired_sessions} expired sessions need cleanup")
        
        # Determine overall status
        if health_status['issues']:
            health_status['status'] = 'warning' if len(health_status['issues']) < 3 else 'critical'
        
    except Exception as e:
        health_status['status'] = 'error'
        health_status['issues'].append(f"Database connectivity issue: {str(e)}")
    
    if request.GET.get('format') == 'json':
        return JsonResponse(health_status, json_dumps_params={'default': str})
    
    context = {'health_status': health_status}
    return render(request, 'admin/system_health_check.html', context)