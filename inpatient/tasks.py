"""
Celery tasks for inpatient operations.
This module contains asynchronous tasks for handling inpatient-related operations
such as automatic admission charge deductions.
"""

import logging
from decimal import Decimal
from datetime import datetime
from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from django.db import transaction
from django.conf import settings

from .models import Admission
from patients.models import PatientWallet, WalletTransaction
from core.utils import send_notification_email

logger = logging.getLogger(__name__)


@shared_task(bind=True, retry_kwargs={'max_retries': 3, 'countdown': 60})
def process_daily_admission_charges(self, target_date=None):
    """
    Celery task to process daily admission charges for all active admissions.
    This task is scheduled to run at 12:00 AM daily.
    
    Args:
        target_date (str, optional): Date to process in YYYY-MM-DD format. Defaults to today.
    
    Returns:
        dict: Summary of processing results
    """
    try:
        if target_date:
            try:
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                logger.error(f"Invalid target_date format: {target_date}")
                target_date = timezone.now().date()
        else:
            target_date = timezone.now().date()

        logger.info(f"Starting daily admission charges processing for {target_date}")

        # Use the existing management command for consistency
        call_command('daily_admission_charges', date=target_date.strftime('%Y-%m-%d'))
        
        # Get processing summary
        summary = get_processing_summary(target_date)
        
        logger.info(f"Daily admission charges processing completed for {target_date}: {summary}")
        return summary

    except Exception as exc:
        logger.error(f"Error processing daily admission charges: {str(exc)}")
        # Retry the task if it fails
        raise self.retry(exc=exc)


@shared_task
def process_single_admission_charge(admission_id, charge_date=None):
    """
    Process daily charge for a specific admission.
    
    Args:
        admission_id (int): ID of the admission to process
        charge_date (str, optional): Date to process in YYYY-MM-DD format
    
    Returns:
        dict: Processing result
    """
    try:
        if charge_date:
            charge_date = datetime.strptime(charge_date, '%Y-%m-%d').date()
        else:
            charge_date = timezone.now().date()

        admission = Admission.objects.select_related(
            'patient', 'bed__ward', 'attending_doctor'
        ).get(id=admission_id)

        result = process_admission_charge_internal(admission, charge_date)
        
        logger.info(f"Single admission charge processed: Admission {admission_id}, Amount: {result.get('amount', 'N/A')}")
        return result

    except Admission.DoesNotExist:
        error_msg = f"Admission with ID {admission_id} not found"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}
    except Exception as exc:
        error_msg = f"Error processing charge for admission {admission_id}: {str(exc)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}


@shared_task
def send_low_balance_notifications():
    """
    Send notifications to patients with low wallet balances.
    This task runs every 2 hours to check for low balances.
    """
    try:
        # Define low balance threshold
        low_balance_threshold = Decimal(getattr(settings, 'WALLET_LOW_BALANCE_THRESHOLD', '100.00'))
        
        # Get wallets with low balances
        low_balance_wallets = PatientWallet.objects.filter(
            balance__lt=low_balance_threshold,
            balance__gt=-1000,  # Don't spam users with extremely negative balances
            is_active=True
        ).select_related('patient')

        notifications_sent = 0
        
        for wallet in low_balance_wallets:
            # Check if notification was sent recently (within last 24 hours)
            recent_notification = WalletTransaction.objects.filter(
                wallet=wallet,
                transaction_type='balance_notification',
                created_at__gte=timezone.now() - timezone.timedelta(days=1)
            ).exists()
            
            if not recent_notification:
                send_balance_notification(wallet)
                notifications_sent += 1
                
                # Create a record to track notification
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='balance_notification',
                    amount=Decimal('0.00'),
                    balance_after=wallet.balance,
                    description=f"Low balance notification sent (Balance: ₦{wallet.balance})",
                    status='completed'
                )

        logger.info(f"Sent {notifications_sent} low balance notifications")
        return {'notifications_sent': notifications_sent}

    except Exception as exc:
        logger.error(f"Error sending low balance notifications: {str(exc)}")
        return {'error': str(exc)}


def process_admission_charge_internal(admission, charge_date):
    """
    Internal function to process daily charge for a single admission.
    This mirrors the logic from the management command but returns structured data.
    """
    # Check if patient is NHIA - NHIA patients are exempt from admission fees
    try:
        is_nhia_patient = (hasattr(admission.patient, 'nhia_info') and
                         admission.patient.nhia_info and
                         admission.patient.nhia_info.is_active)
    except:
        is_nhia_patient = False

    if is_nhia_patient:
        return {'success': True, 'amount': None, 'reason': 'NHIA patient - exempt from charges'}

    # Check if admission was active on the charge date
    admission_date = admission.admission_date.date()
    discharge_date = admission.discharge_date.date() if admission.discharge_date else None

    if charge_date < admission_date:
        return {'success': False, 'reason': 'Charge date before admission'}

    if discharge_date and charge_date > discharge_date:
        return {'success': False, 'reason': 'Charge date after discharge'}

    # Calculate daily charge
    if not admission.bed or not admission.bed.ward:
        return {'success': False, 'reason': 'No bed/ward assigned'}

    daily_charge = admission.bed.ward.charge_per_day
    if daily_charge <= 0:
        return {'success': False, 'reason': 'No daily charge configured'}

    # Get or create patient wallet
    wallet, created = PatientWallet.objects.get_or_create(
        patient=admission.patient,
        defaults={'balance': Decimal('0.00')}
    )

    # Check if daily charge already exists for this date
    existing_charge = WalletTransaction.objects.filter(
        wallet=wallet,
        admission=admission,
        transaction_type='daily_admission_charge',
        created_at__date=charge_date
    ).exists()

    if existing_charge:
        return {'success': False, 'reason': 'Charge already processed for this date'}

    # Process the charge
    try:
        with transaction.atomic():
            wallet.debit(
                amount=daily_charge,
                description=f"Daily admission charge for {charge_date} - {admission.bed.ward.name}",
                transaction_type="daily_admission_charge",
                user=admission.attending_doctor,
                admission=admission
            )

            return {
                'success': True,
                'amount': daily_charge,
                'new_balance': wallet.balance,
                'ward': admission.bed.ward.name
            }

    except Exception as e:
        logger.error(f'Failed to process daily charge for admission {admission.id}: {str(e)}')
        return {'success': False, 'error': str(e)}


def get_processing_summary(target_date):
    """
    Get summary of daily admission charges processing for a specific date.
    """
    # Get all transactions for the target date
    daily_charges = WalletTransaction.objects.filter(
        transaction_type='daily_admission_charge',
        created_at__date=target_date
    ).select_related('wallet__patient')

    total_amount = sum(txn.amount for txn in daily_charges)
    total_processed = daily_charges.count()

    return {
        'date': target_date.strftime('%Y-%m-%d'),
        'total_processed': total_processed,
        'total_amount': float(total_amount),
        'affected_patients': list(set(txn.wallet.patient.get_full_name() for txn in daily_charges))
    }


def send_balance_notification(wallet):
    """
    Send low balance notification to patient.
    """
    try:
        # You can customize this based on your notification preferences
        if wallet.patient.email:
            send_notification_email(
                subject="HMS - Low Wallet Balance Alert",
                message=f"""
                Dear {wallet.patient.get_full_name()},
                
                Your HMS wallet balance is low: ₦{wallet.balance}
                
                To avoid service interruptions, please add funds to your wallet.
                
                Thank you,
                HMS Team
                """,
                recipient_list=[wallet.patient.email],
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@hms.com')
            )
            
        logger.info(f"Low balance notification sent to {wallet.patient.get_full_name()}")
        
    except Exception as e:
        logger.error(f"Failed to send low balance notification to {wallet.patient.get_full_name()}: {str(e)}")