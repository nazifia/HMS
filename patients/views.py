from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Patient, MedicalHistory, Vitals
from inpatient.models import Admission
from nhia.models import NHIAPatient
from .forms import NHIARegistrationForm
from .forms import PatientForm, MedicalHistoryForm, VitalsForm, PatientSearchForm
from core.audit_utils import log_audit_action
from core.utils import send_notification_email, send_sms_notification
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .models import PatientWallet, WalletTransaction
from .forms import (AddFundsForm, WalletWithdrawalForm, WalletTransferForm,
                   WalletRefundForm, WalletAdjustmentForm, WalletTransactionSearchForm)

@login_required
def patient_list(request):
    """View for listing all registered patients (active and inactive) with search and filter functionality"""
    search_form = PatientSearchForm(request.GET)
    # Retrieve all patients, regardless of is_active status
    patients = Patient.objects.all().order_by('-registration_date')

    # Apply filters if the form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        gender = search_form.cleaned_data.get('gender')
        blood_group = search_form.cleaned_data.get('blood_group')
        city = search_form.cleaned_data.get('city')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if search_query:
            patients = patients.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(patient_id__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        if gender:
            patients = patients.filter(gender=gender)

        if blood_group:
            patients = patients.filter(blood_group=blood_group)

        if city:
            patients = patients.filter(city__icontains=city)

        if date_from:
            patients = patients.filter(registration_date__gte=date_from)

        if date_to:
            patients = patients.filter(registration_date__lte=date_to)

    # Pagination
    paginator = Paginator(patients, 10)  # Show 10 patients per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_patients': patients.count(),
    }

    return render(request, 'patients/patient_list.html', context)

@login_required
def register_patient(request):
    """View for registering a new patient"""
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.updated_by = request.user
            patient.save()
            # Audit log for registration
            log_audit_action(request.user, 'register_patient', patient, f"Registered patient {patient.get_full_name()} (ID: {patient.patient_id})")
            # Send notification email/SMS to patient (stub)
            if patient.email:
                send_notification_email(
                    subject="Welcome to Hospital Management System",
                    message=f"Dear {patient.get_full_name()}, your registration is complete. Patient ID: {patient.patient_id}",
                    recipient_list=[patient.email]
                )
            if patient.phone_number:
                send_sms_notification(
                    phone_number=patient.phone_number,
                    message=f"Welcome to HMS. Your Patient ID: {patient.patient_id}"
                )
            messages.success(request, f'Patient {patient.get_full_name()} has been registered successfully with ID: {patient.patient_id}')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = PatientForm()

    context = {
        'form': form,
        'title': 'Register New Patient'
    }

    return render(request, 'patients/patient_form.html', context)

@login_required
def patient_detail(request, patient_id):
    """View for displaying patient details"""
    patient = get_object_or_404(Patient, id=patient_id)
    medical_histories = patient.medical_histories.all().order_by('-date')
    vitals = patient.vitals.all().order_by('-date_time')[:10]  # Get the 10 most recent vitals

    # Handle adding new medical history
    if request.method == 'POST' and 'add_medical_history' in request.POST:
        medical_history_form = MedicalHistoryForm(request.POST)
        if medical_history_form.is_valid():
            medical_history = medical_history_form.save(commit=False)
            medical_history.patient = patient
            # Set the doctor_name field to the current user's name
            if not medical_history.doctor_name:
                medical_history.doctor_name = f"{request.user.get_full_name()} ({request.user.username})"
            medical_history.save()
            # Audit log for medical history creation
            log_audit_action(request.user, 'add_medical_history', medical_history, f"Added medical history for patient {patient.get_full_name()} (ID: {patient.patient_id})")
            messages.success(request, 'Medical history record added successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        medical_history_form = MedicalHistoryForm()

    # Handle adding new vitals
    if request.method == 'POST' and 'add_vitals' in request.POST:
        vitals_form = VitalsForm(request.POST)
        if vitals_form.is_valid():
            new_vitals = vitals_form.save(commit=False)
            new_vitals.patient = patient
            new_vitals.date_time = timezone.now()
            new_vitals.recorded_by = f"{request.user.get_full_name()} ({request.user.username})"
            new_vitals.save()
            messages.success(request, 'Vitals recorded successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        vitals_form = VitalsForm()

    # Wallet information
    has_wallet = hasattr(patient, 'wallet') and patient.wallet is not None
    wallet_is_active = has_wallet and patient.wallet.is_active

    # NHIA Information
    nhia_info = None
    try:
        nhia_info = patient.nhia_info
    except NHIAPatient.DoesNotExist:
        pass

    context = {
        'patient': patient,
        'medical_histories': medical_histories,
        'vitals': vitals,
        'medical_history_form': medical_history_form,
        'vitals_form': vitals_form,
        'age': patient.get_age(),
        'today': timezone.now(),
        'has_wallet': has_wallet,
        'wallet_is_active': wallet_is_active,
        'nhia_info': nhia_info, # Pass NHIA info to template
    }

    return render(request, 'patients/patient_detail.html', context)

@login_required
def register_nhia_patient(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    # Check if patient already has an NHIA record
    if hasattr(patient, 'nhia_info'):
        messages.warning(request, f'Patient {patient.get_full_name()} already has an NHIA record. Please edit the existing record.')
        return redirect('patients:detail', patient_id=patient.id)

    if request.method == 'POST':
        form = NHIARegistrationForm(request.POST)
        if form.is_valid():
            nhia_patient = form.save(commit=False)
            nhia_patient.patient = patient
            nhia_patient.save()
            messages.success(request, f'NHIA record for {patient.get_full_name()} created successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = NHIARegistrationForm()

    context = {
        'form': form,
        'patient': patient,
        'title': f'Register NHIA Patient: {patient.get_full_name()}'
    }
    return render(request, 'patients/nhia_registration_form.html', context)

@login_required
def edit_nhia_patient(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    nhia_patient = get_object_or_404(NHIAPatient, patient=patient)

    if request.method == 'POST':
        form = NHIARegistrationForm(request.POST, instance=nhia_patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'NHIA record for {patient.get_full_name()} updated successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = NHIARegistrationForm(instance=nhia_patient)

    context = {
        'form': form,
        'patient': patient,
        'nhia_patient': nhia_patient,
        'title': f'Edit NHIA Patient: {patient.get_full_name()}'
    }
    return render(request, 'patients/nhia_registration_form.html', context)

@login_required
def edit_patient(request, patient_id):
    """View for editing patient information"""
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            updated_patient = form.save(commit=False)
            updated_patient.updated_by = request.user
            updated_patient.save()
            # Audit log for update
            log_audit_action(request.user, 'update_patient', updated_patient, f"Updated patient {updated_patient.get_full_name()} (ID: {updated_patient.patient_id})")
            messages.success(request, f'Patient {patient.get_full_name()} information has been updated successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = PatientForm(instance=patient)

    context = {
        'form': form,
        'patient': patient,
        'title': f'Edit Patient: {patient.get_full_name()}'
    }

    return render(request, 'patients/patient_form.html', context)


@login_required
@require_POST
def toggle_patient_status(request, patient_id):
    """View for activating or deactivating a patient."""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Toggle the is_active status
    patient.is_active = not patient.is_active
    patient.save()
    
    # Determine the action for the audit log and message
    action = "activated" if patient.is_active else "deactivated"
    
    # Audit log for patient status change
    log_audit_action(
        request.user, 
        f'{action}_patient', 
        patient, 
        f"{action.capitalize()} patient {patient.get_full_name()} (ID: {patient.patient_id})"
    )
    
    # Success message
    messages.success(request, f'Patient {patient.get_full_name()} has been {action}.')
    
    return redirect('patients:list')


@login_required
def add_funds_to_wallet(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)

    if request.method == 'POST':
        form = AddFundsForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data.get('description', f'Funds added via {form.cleaned_data["payment_method"]}')

            wallet.credit(
                amount=amount,
                description=description,
                transaction_type='deposit',
                user=request.user
            )

            log_audit_action(request.user, 'add_funds_to_wallet', wallet, f"Added ₦{amount} to wallet of {patient.get_full_name()} (ID: {patient.patient_id})")
            messages.success(request, f'Successfully added ₦{amount} to the wallet of {patient.get_full_name()}. New balance: ₦{wallet.balance}')
            return redirect('patients:wallet_dashboard', patient_id=patient.id)
    else:
        form = AddFundsForm()

    context = {
        'form': form,
        'patient': patient,
        'wallet': wallet,
        'title': f'Add Funds to Wallet for {patient.get_full_name()}'
    }
    return render(request, 'patients/add_funds_form.html', context)


@login_required
def wallet_dashboard(request, patient_id):
    """Comprehensive wallet dashboard for a patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)

    # Get recent transactions
    recent_transactions = wallet.get_transaction_history(limit=10)

    # Get comprehensive wallet statistics
    wallet_stats = wallet.get_transaction_statistics()
    total_credits = wallet.get_total_credits()
    total_debits = wallet.get_total_debits()

    # Get monthly transaction summary
    from django.db.models import Sum
    from datetime import datetime, timedelta

    thirty_days_ago = datetime.now() - timedelta(days=30)

    # Enhanced monthly statistics
    credit_types = [
        'credit', 'deposit', 'refund', 'transfer_in', 'adjustment',
        'insurance_claim', 'bonus', 'cashback', 'reversal'
    ]
    debit_types = [
        'debit', 'withdrawal', 'payment', 'transfer_out', 'admission_fee',
        'daily_admission_charge', 'lab_test_payment', 'pharmacy_payment',
        'consultation_fee', 'procedure_fee', 'penalty_fee', 'discount_applied'
    ]

    monthly_credits = wallet.transactions.filter(
        created_at__gte=thirty_days_ago,
        transaction_type__in=credit_types
    ).aggregate(total=Sum('amount'))['total'] or 0

    monthly_debits = wallet.transactions.filter(
        created_at__gte=thirty_days_ago,
        transaction_type__in=debit_types
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Get recent admissions for the patient
    recent_admissions = patient.admissions.all().order_by('-admission_date')[:5] # Get last 5 admissions

    context = {
        'patient': patient,
        'wallet': wallet,
        'recent_transactions': recent_transactions,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'monthly_credits': monthly_credits,
        'monthly_debits': monthly_debits,
        'wallet_stats': wallet_stats,
        'recent_admissions': recent_admissions,
        'title': f'Wallet Dashboard - {patient.get_full_name()}'
    }
    return render(request, 'patients/wallet_dashboard.html', context)


@login_required
def wallet_transactions(request, patient_id):
    """View all wallet transactions with search and filter"""
    patient = get_object_or_404(Patient, id=patient_id)
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)

    # Get search form
    search_form = WalletTransactionSearchForm(request.GET)
    transactions = wallet.transactions.all()

    # Apply filters
    if search_form.is_valid():
        search = search_form.cleaned_data.get('search')
        transaction_type = search_form.cleaned_data.get('transaction_type')
        status = search_form.cleaned_data.get('status')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        amount_min = search_form.cleaned_data.get('amount_min')
        amount_max = search_form.cleaned_data.get('amount_max')

        if search:
            transactions = transactions.filter(
                Q(description__icontains=search) |
                Q(reference_number__icontains=search)
            )

        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)

        if status:
            transactions = transactions.filter(status=status)

        if date_from:
            transactions = transactions.filter(created_at__date__gte=date_from)

        if date_to:
            transactions = transactions.filter(created_at__date__lte=date_to)

        if amount_min:
            transactions = transactions.filter(amount__gte=amount_min)

        if amount_max:
            transactions = transactions.filter(amount__lte=amount_max)

    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'patient': patient,
        'wallet': wallet,
        'search_form': search_form,
        'page_obj': page_obj,
        'title': f'Wallet Transactions - {patient.get_full_name()}'
    }
    return render(request, 'patients/wallet_transactions.html', context)


@login_required
def wallet_withdrawal(request, patient_id):
    """Withdraw funds from patient wallet"""
    patient = get_object_or_404(Patient, id=patient_id)
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)

    if request.method == 'POST':
        form = WalletWithdrawalForm(request.POST, wallet=wallet)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data.get('description', f'Withdrawal via {form.cleaned_data["withdrawal_method"]}')

            try:
                wallet.debit(
                    amount=amount,
                    description=description,
                    transaction_type='withdrawal',
                    user=request.user
                )

                log_audit_action(request.user, 'wallet_withdrawal', wallet, f"Withdrew ₦{amount} from wallet of {patient.get_full_name()} (ID: {patient.patient_id})")
                messages.success(request, f'Successfully withdrew ₦{amount} from the wallet of {patient.get_full_name()}. New balance: ₦{wallet.balance}')
                return redirect('patients:wallet_dashboard', patient_id=patient.id)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = WalletWithdrawalForm(wallet=wallet)

    context = {
        'form': form,
        'patient': patient,
        'wallet': wallet,
        'title': f'Withdraw from Wallet - {patient.get_full_name()}'
    }
    return render(request, 'patients/wallet_withdrawal.html', context)


@login_required
def wallet_transfer(request, patient_id):
    """Transfer funds between patient wallets with enhanced error handling"""
    patient = get_object_or_404(Patient, id=patient_id)
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)

    # Check if sender wallet is active
    if not wallet.is_active:
        messages.error(request, f'Wallet for {patient.get_full_name()} is not active. Please contact administrator.')
        return redirect('patients:wallet_dashboard', patient_id=patient.id)

    if request.method == 'POST':
        form = WalletTransferForm(request.POST, wallet=wallet)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            recipient_patient = form.cleaned_data['recipient_patient']
            description = form.cleaned_data.get('description', 'Wallet transfer')

            try:
                # Get or create recipient wallet
                recipient_wallet, recipient_created = PatientWallet.objects.get_or_create(
                    patient=recipient_patient,
                    defaults={'is_active': True}
                )

                # Ensure recipient wallet is active
                if not recipient_wallet.is_active:
                    messages.error(request, f'Recipient wallet for {recipient_patient.get_full_name()} is not active. Please contact administrator.')
                    return render(request, 'patients/wallet_transfer.html', {
                        'form': form,
                        'patient': patient,
                        'wallet': wallet,
                        'title': f'Transfer from Wallet - {patient.get_full_name()}'
                    })

                # Store initial balances for detailed success message
                initial_sender_balance = wallet.balance
                initial_recipient_balance = recipient_wallet.balance

                # Use the enhanced transfer_to method for atomic processing
                sender_transaction, recipient_transaction = wallet.transfer_to(
                    recipient_wallet=recipient_wallet,
                    amount=amount,
                    description=description,
                    user=request.user
                )

                # Refresh wallet balances from database
                wallet.refresh_from_db()
                recipient_wallet.refresh_from_db()

                # Comprehensive audit logging
                log_audit_action(
                    request.user, 
                    'wallet_transfer', 
                    wallet, 
                    f"Transferred ₦{amount:,.2f} from {patient.get_full_name()} (ID: {patient.patient_id}) "
                    f"to {recipient_patient.get_full_name()} (ID: {recipient_patient.patient_id}). "
                    f"Sender balance: ₦{initial_sender_balance:,.2f} → ₦{wallet.balance:,.2f}, "
                    f"Recipient balance: ₦{initial_recipient_balance:,.2f} → ₦{recipient_wallet.balance:,.2f}. "
                    f"Transaction refs: {sender_transaction.reference_number}, {recipient_transaction.reference_number}"
                )

                # Detailed success message
                messages.success(
                    request, 
                    f'✅ Successfully transferred ₦{amount:,.2f} to {recipient_patient.get_full_name()}. '
                    f'Your new balance: ₦{wallet.balance:,.2f}. '
                    f'Transaction reference: {sender_transaction.reference_number}'
                )
                
                return redirect('patients:wallet_dashboard', patient_id=patient.id)

            except ValueError as e:
                # Handle validation errors from the transfer_to method
                messages.error(request, f'Transfer failed: {str(e)}')
                
            except Exception as e:
                # Handle unexpected errors
                messages.error(request, f'An unexpected error occurred during the transfer. Please try again or contact support. Error: {str(e)}')
                
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Wallet transfer error for user {request.user.id}: {str(e)}", exc_info=True)

        else:
            # Form validation errors
            messages.error(request, 'Please correct the errors below and try again.')
    else:
        form = WalletTransferForm(wallet=wallet)

    context = {
        'form': form,
        'patient': patient,
        'wallet': wallet,
        'title': f'Transfer from Wallet - {patient.get_full_name()}'
    }
    return render(request, 'patients/wallet_transfer.html', context)


@login_required
def wallet_refund(request, patient_id):
    """Process refund to patient wallet"""
    patient = get_object_or_404(Patient, id=patient_id)
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)

    if request.method == 'POST':
        form = WalletRefundForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            reason = form.cleaned_data['reason']
            reference_invoice = form.cleaned_data.get('reference_invoice', '')

            description = f'Refund: {reason}'
            if reference_invoice:
                description += f' (Ref: {reference_invoice})'

            wallet.credit(
                amount=amount,
                description=description,
                transaction_type='refund',
                user=request.user
            )

            log_audit_action(request.user, 'wallet_refund', wallet, f"Processed refund of ₦{amount} to {patient.get_full_name()} - {reason}")
            messages.success(request, f'Successfully processed refund of ₦{amount} to {patient.get_full_name()}. New balance: ₦{wallet.balance}')
            return redirect('patients:wallet_dashboard', patient_id=patient.id)
    else:
        form = WalletRefundForm()

    context = {
        'form': form,
        'patient': patient,
        'wallet': wallet,
        'title': f'Process Refund - {patient.get_full_name()}'
    }
    return render(request, 'patients/wallet_refund.html', context)


@login_required
def wallet_adjustment(request, patient_id):
    """Make manual adjustment to patient wallet"""
    patient = get_object_or_404(Patient, id=patient_id)
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)

    if request.method == 'POST':
        form = WalletAdjustmentForm(request.POST, wallet=wallet)
        if form.is_valid():
            adjustment_type = form.cleaned_data['adjustment_type']
            amount = form.cleaned_data['amount']
            reason = form.cleaned_data['reason']

            description = f'Manual {adjustment_type} adjustment: {reason}'

            try:
                if adjustment_type == 'credit':
                    wallet.credit(
                        amount=amount,
                        description=description,
                        transaction_type='adjustment',
                        user=request.user
                    )
                else:  # debit
                    wallet.debit(
                        amount=amount,
                        description=description,
                        transaction_type='adjustment',
                        user=request.user
                    )

                log_audit_action(request.user, 'wallet_adjustment', wallet, f"Made {adjustment_type} adjustment of ₦{amount} to {patient.get_full_name()} - {reason}")
                messages.success(request, f'Successfully made {adjustment_type} adjustment of ₦{amount}. New balance: ₦{wallet.balance}')
                return redirect('patients:wallet_dashboard', patient_id=patient.id)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = WalletAdjustmentForm(wallet=wallet)

    context = {
        'form': form,
        'patient': patient,
        'wallet': wallet,
        'title': f'Wallet Adjustment - {patient.get_full_name()}'
    }
    return render(request, 'patients/wallet_adjustment.html', context)


@login_required
def search_patients(request):
    """AJAX view for searching patients"""
    search_term = request.GET.get('term', '')

    if len(search_term) < 3:
        return JsonResponse([], safe=False)

    patients = Patient.objects.filter(
        Q(first_name__icontains=search_term) |
        Q(last_name__icontains=search_term) |
        Q(patient_id__icontains=search_term) |
        Q(phone_number__icontains=search_term)
    ).filter(is_active=True)[:10]

    results = [{
        'id': patient.id,
        'text': f"{patient.get_full_name()} ({patient.patient_id})",
        'patient_id': patient.patient_id,
        'name': patient.get_full_name(),
        'gender': patient.get_gender_display(),
        'phone': patient.phone_number,
        'age': patient.get_age()
    } for patient in patients]

    return JsonResponse(results, safe=False)

@login_required
def edit_medical_history(request, history_id):
    """View for editing a medical history record"""
    history = get_object_or_404(MedicalHistory, id=history_id)
    patient = history.patient

    if request.method == 'POST':
        form = MedicalHistoryForm(request.POST, instance=history)
        if form.is_valid():
            updated_history = form.save(commit=False)
            updated_history.updated_by = request.user
            updated_history.save()
            # Audit log for medical history update
            log_audit_action(request.user, 'update_medical_history', updated_history, f"Updated medical history for patient {patient.get_full_name()} (ID: {patient.patient_id})")
            messages.success(request, 'Medical history record updated successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = MedicalHistoryForm(instance=history)

    context = {
        'form': form,
        'history': history,
        'patient': patient,
        'title': 'Edit Medical History'
    }

    return render(request, 'patients/medical_history_form.html', context)

@login_required
def delete_medical_history(request, history_id):
    """View for deleting a medical history record"""
    history = get_object_or_404(MedicalHistory, id=history_id)
    patient = history.patient

    if request.method == 'POST':
        history.delete()
        messages.success(request, 'Medical history record deleted successfully.')
        return redirect('patients:detail', patient_id=patient.id)

    context = {
        'history': history,
        'patient': patient
    }

    return render(request, 'patients/delete_medical_history.html', context)

@login_required
def patient_medical_history(request, patient_id):
    """View for displaying all medical history records for a patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    medical_histories = patient.medical_histories.all().order_by('-date')

    context = {
        'patient': patient,
        'medical_histories': medical_histories
    }

    return render(request, 'patients/patient_medical_history.html', context)

@login_required
def patient_vitals(request, patient_id):
    """View for displaying all vitals records for a patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    vitals = patient.vitals.all().order_by('-date_time')

    context = {
        'patient': patient,
        'vitals': vitals
    }

    return render(request, 'patients/patient_vitals.html', context)

@login_required
def generate_receipt(request, patient_id):
    """Stub for generating a receipt for a patient (e.g., after payment)"""
    patient = get_object_or_404(Patient, id=patient_id)
    # TODO: Integrate with billing/invoice logic and PDF export
    context = {
        'patient': patient,
        'date': timezone.now(),
        'amount': '0.00',  # Placeholder
        'details': 'Receipt details here.'
    }
    return render(request, 'patients/receipt_stub.html', context)

@login_required
def generate_medical_certificate(request, patient_id):
    """Stub for generating a medical certificate for a patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    # TODO: Add form for certificate details, doctor signature, export as PDF
    context = {
        'patient': patient,
        'date': timezone.now(),
        'certificate_text': 'Medical certificate text here.'
    }
    return render(request, 'patients/medical_certificate_stub.html', context)

@login_required
def generate_fit_note(request, patient_id):
    """Stub for generating a fit note for a patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    # TODO: Add form for fit note details, doctor signature, export as PDF
    context = {
        'patient': patient,
        'date': timezone.now(),
        'fit_note_text': 'Fit note text here.'
    }
    return render(request, 'patients/fit_note_stub.html', context)

@login_required
def generate_discharge_summary(request, patient_id):
    """Stub for generating a discharge summary for a patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    # TODO: Integrate with inpatient/clinical records, export as PDF
    context = {
        'patient': patient,
        'date': timezone.now(),
        'summary_text': 'Discharge summary text here.'
    }
    return render(request, 'patients/discharge_summary_stub.html', context)

@login_required
def scan_barcode_qr(request):
    """Stub for barcode/QR code scanning integration (e.g., for patient wristbands, medication, etc.)"""
    # TODO: Integrate with hardware scanner or camera, decode and process data
    context = {
        'title': 'Scan Barcode/QR',
        'message': 'Barcode/QR scanning logic goes here.'
    }
    return render(request, 'patients/barcode_qr_stub.html', context)

@login_required
def lookup_national_health_id(request):
    """Stub for national health ID lookup/integration"""
    # TODO: Integrate with national health ID API/service
    context = {
        'title': 'National Health ID Lookup',
        'message': 'National health ID lookup logic goes here.'
    }
    return render(request, 'patients/health_id_stub.html', context)

@login_required
def third_party_api_integration(request):
    """Stub for third-party API integration (insurance, labs, etc.)"""
    # TODO: Add logic for connecting to external APIs, handling responses, etc.
    context = {
        'title': 'Third-Party API Integration',
        'message': 'Third-party API integration logic goes here.'
    }
    return render(request, 'patients/third_party_api_stub.html', context)

@require_GET
def pwa_manifest(request):
    """Serve a real manifest.json for PWA support with advanced features."""
    manifest = {
        "name": "Hospital Management System",
        "short_name": "HMS",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1976d2",
        "description": "A modern, offline-capable hospital management system.",
        "icons": [
            {"src": "/static/icons/icon-192x192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icons/icon-512x512.png", "sizes": "512x512", "type": "image/png"}
        ],
        "scope": "/",
        "orientation": "portrait",
        "id": "/manifest.json",
        "gcm_sender_id": "103953800507",  # For push notifications
        "shortcuts": [
            {"name": "New Patient", "short_name": "Register", "url": "/patients/register/", "icons": [{"src": "/static/icons/icon-192x192.png", "sizes": "192x192"}]},
            {"name": "Dashboard", "short_name": "Dashboard", "url": "/dashboard/", "icons": [{"src": "/static/icons/icon-192x192.png", "sizes": "192x192"}]}
        ],
        "related_applications": [
            {"platform": "webapp", "url": "https://your-hms.example.com"}
        ],
        "lang": "en-US"
    }
    return HttpResponse(json.dumps(manifest), content_type='application/manifest+json')

@require_GET
def service_worker(request):
    """Serve an advanced service worker JS file for full PWA/offline support."""
    sw_js = '''
    const CACHE_NAME = 'hms-cache-v2';
    const urlsToCache = [
        '/',
        '/static/css/main.css',
        '/static/js/main.js',
        '/offline/',
        // Add more static assets and offline pages as needed
    ];
    // IndexedDB setup for offline data persistence
    function openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('hms-db', 1);
            request.onupgradeneeded = function(event) {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('formQueue')) {
                    db.createObjectStore('formQueue', { autoIncrement: true });
                }
            };
            request.onsuccess = function(event) { resolve(event.target.result); };
            request.onerror = function(event) { reject(event.target.error); };
        });
    }
    // Install event: cache static assets
    self.addEventListener('install', function(event) {
        event.waitUntil(
            caches.open(CACHE_NAME).then(function(cache) {
                return cache.addAll(urlsToCache);
            })
        );
        self.skipWaiting();
    });
    // Activate event: clean up old caches
    self.addEventListener('activate', function(event) {
        event.waitUntil(
            caches.keys().then(function(cacheNames) {
                return Promise.all(
                    cacheNames.filter(function(cacheName) {
                        return cacheName !== CACHE_NAME;
                    }).map(function(cacheName) {
                        return caches.delete(cacheName);
                    })
                );
            })
        );
        self.clients.claim();
    });
    // Fetch event: serve from cache, fallback to network, then offline page
    self.addEventListener('fetch', function(event) {
        if (event.request.method === 'GET') {
            event.respondWith(
                caches.match(event.request).then(function(response) {
                    return response || fetch(event.request).catch(() => caches.match('/offline/'));
                })
            );
        } else if (event.request.method === 'POST') {
            // Offline form queueing: clone and store in IndexedDB
            event.respondWith(
                (async () => {
                    try {
                        return await fetch(event.request);
                    } catch (err) {
                        // Store POST in IndexedDB for later sync
                        const db = await openDB();
                        const tx = db.transaction('formQueue', 'readwrite');
                        const store = tx.objectStore('formQueue');
                        const body = await event.request.clone().formData ? await event.request.clone().formData() : await event.request.clone().text();
                        await store.add({ url: event.request.url, formData: body, timestamp: Date.now() });
                        db.close();
                        return new Response(JSON.stringify({ offline: true, queued: true }), { status: 202, headers: { 'Content-Type': 'application/json' } });
                    }
                })()
            );
        }
    });

    // Background sync for queued forms (IndexedDB)
    self.addEventListener('sync', function(event) {
        if (event.tag === 'syncForms') {
            event.waitUntil(
                (async () => {
                    const db = await openDB();
                    const tx = db.transaction('formQueue', 'readwrite');
                    const store = tx.objectStore('formQueue');
                    const getAllReq = store.getAll();
                    getAllReq.onsuccess = async function() {
                        for (const item of getAllReq.result) {
                            try {
                                let body;
                                if (item.formData instanceof FormData) {
                                    body = new URLSearchParams(item.formData);
                                } else if (typeof item.formData === 'object') {
                                    body = new URLSearchParams(item.formData);
                                } else {
                                    body = item.formData;
                                }
                                await fetch(item.url, {
                                    method: 'POST',
                                    body: body,
                                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                                });
                            } catch (e) {
                                // Still offline, keep in queue
                                return;
                            }
                        }
                        store.clear();
                    };
                    db.close();
                })()
            );
        }
    });
    // Push notification support
    self.addEventListener('push', function(event) {
        const data = event.data ? event.data.json() : {};
        const title = data.title || 'HMS Notification';
        const options = {
            body: data.body || '',
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/icon-192x192.png',
            data: data.url || '/'
        };
        event.waitUntil(self.registration.showNotification(title, options));
    });
    self.addEventListener('notificationclick', function(event) {
        event.notification.close();
        event.waitUntil(
            clients.openWindow(event.notification.data)
        );
    });
    // Custom offline fallback page logic
    // TODO: Enhance with cached data display, limited actions, etc.
    '''
    return HttpResponse(sw_js, content_type='application/javascript')

@require_GET
def offline_fallback(request):
    """Serve an offline fallback page for PWA/offline support."""
    # TODO: Enhance this template for a richer offline experience (e.g., show cached data, allow limited actions)
    return render(request, 'patients/offline_fallback.html')

@login_required
def pwa_push_demo(request):
    """Demo endpoint to trigger a push notification (for development/testing only)."""
    # In a real implementation, you'd send a push message to the user's subscription using pywebpush or similar.
    # Here, just render a page with instructions or a stub.
    context = {
        'title': 'PWA Push Notification Demo',
        'message': 'This is a demo endpoint. In production, this would trigger a push notification to the browser.'
    }
    return render(request, 'patients/pwa_push_demo.html', context)

@login_required
def pwa_demo(request):
    """Demo page for PWA features: push notification and offline queueing."""
    if request.method == 'POST':
        # Simulate form submission (for offline queueing demo)
        name = request.POST.get('name', '')
        data = {'message': f"Received form for {name}", 'offline': False};
        return HttpResponse(json.dumps(data), content_type='application/json')
    return render(request, 'patients/pwa_demo.html', {})

@require_GET
def demo_push_notification(request):
    """Demo endpoint to trigger a push notification (stub)."""
    # In real use, would send a push notification to the user's subscription
    data = {
        'success': True,
        'title': 'Demo Push',
        'body': 'This is a test push notification from HMS!',
        'url': '/patients/'
    }
    return HttpResponse(json.dumps(data), content_type='application/json')

@csrf_exempt
@require_POST
def pwa_offline_queue_demo(request):
    """Demo endpoint to receive POSTs (for offline queueing test). Returns JSON indicating success or offline queue."""
    # In real use, this would process form data. Here, just echo back the data.
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}
    # Simulate processing
    response = {
        'received': True,
        'data': data,
        'message': 'Data received by server (demo endpoint).'
    }
    return JsonResponse(response)

# @login_required
# def toggle_active_patient(request, patient_id):
#     patient = get_object_or_404(Patient, id=patient_id)
#     if request.method == 'POST':
#         patient.is_active = not patient.is_active
#         patient.save()
#         status = 'activated' if patient.is_active else 'deactivated'
#         messages.success(request, f'Patient {patient.get_full_name()} has been {status}.')
#     return redirect('patients:detail', patient_id=patient.id)
