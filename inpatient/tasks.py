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
from .services import charge_admission_for_date
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
                patient_wallet=wallet,
                transaction_type='balance_notification',
                created_at__gte=timezone.now() - timezone.timedelta(days=1)
            ).exists()
            
            if not recent_notification:
                send_balance_notification(wallet)
                notifications_sent += 1
                
                # Create a record to track notification
                WalletTransaction.objects.create(
                    patient_wallet=wallet,
                    patient=wallet.patient,
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
    Wraps inpatient.services.charge_admission_for_date, which the management
    command uses too, and returns structured data.
    """
    try:
        amount, reason = charge_admission_for_date(admission, charge_date)
    except Exception as e:
        logger.error(f'Failed to process daily charge for admission {admission.id}: {str(e)}')
        return {'success': False, 'error': str(e)}

    if amount is None:
        return {'success': False, 'reason': reason}

    return {
        'success': True,
        'amount': amount,
        'new_balance': admission.patient.wallet.balance,
        'ward': admission.bed.ward.name,
    }


def get_processing_summary(target_date):
    """
    Get summary of daily admission charges processing for a specific date.
    """
    # Get all transactions for the target date
    daily_charges = WalletTransaction.objects.filter(
        transaction_type='daily_admission_charge',
        created_at__date=target_date
    ).select_related('patient_wallet__patient', 'patient')

    total_amount = sum(txn.amount for txn in daily_charges)
    total_processed = daily_charges.count()

    def patient_of(txn):
        patient = txn.patient or (txn.patient_wallet.patient if txn.patient_wallet else None)
        return patient.get_full_name() if patient else 'Unknown'

    return {
        'date': target_date.strftime('%Y-%m-%d'),
        'total_processed': total_processed,
        'total_amount': float(total_amount),
        'affected_patients': sorted({patient_of(txn) for txn in daily_charges}),
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