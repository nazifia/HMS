from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Patient, MedicalHistory, Vitals, PatientWallet, WalletTransaction, ClinicalNote
from .forms import PatientForm, MedicalHistoryForm, VitalsForm, AddFundsForm, WalletWithdrawalForm, WalletTransferForm, WalletRefundForm, WalletAdjustmentForm, ClinicalNoteForm
from .utils import get_safe_vitals_for_patient
from appointments.models import Appointment
from consultations.models import Consultation
from pharmacy.models import Prescription
from laboratory.models import TestRequest
from radiology.models import RadiologyOrder
from datetime import datetime, timedelta


@login_required
def patient_list(request):
    """View for listing all patients with search and pagination"""
    from core.patient_search_forms import EnhancedPatientSearchForm

    # Get all active patients
    patients = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')

    # Initialize search form with GET data if present
    search_form = EnhancedPatientSearchForm(request.GET if request.GET else None)

    # Apply search filters - check if any GET parameters exist
    if request.GET:
        # Get search parameters directly from request.GET for more reliable filtering
        search_query = request.GET.get('search', '').strip()
        gender = request.GET.get('gender', '').strip()
        blood_group = request.GET.get('blood_group', '').strip()
        patient_type = request.GET.get('patient_type', '').strip()
        city = request.GET.get('city', '').strip()
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()

        # Apply search query filter
        if search_query:
            patients = patients.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(patient_id__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        # Apply additional filters
        if gender:
            patients = patients.filter(gender=gender)
        if blood_group:
            patients = patients.filter(blood_group=blood_group)
        if patient_type:
            patients = patients.filter(patient_type=patient_type)
        if city:
            patients = patients.filter(city__icontains=city)
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                patients = patients.filter(registration_date__gte=date_from_obj)
            except ValueError:
                pass
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                patients = patients.filter(registration_date__lte=date_to_obj)
            except ValueError:
                pass

    # Get total count for display
    total_patients = patients.count()

    # Pagination
    paginator = Paginator(patients, 15)  # Show 15 patients per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_patients': total_patients,
        'page_title': 'Patient List',
        'active_nav': 'patients',
    }

    # If this is an HTMX request, return only the table partial
    if request.headers.get('HX-Request'):
        return render(request, 'patients/patient_table.html', context)

    return render(request, 'patients/patient_list.html', context)
    



@login_required
def register_patient(request):
    """View for registering a new patient"""
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient {patient.get_full_name()} registered successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = PatientForm()
    
    context = {
        'form': form,
        'page_title': 'Register Patient',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/register.html', context)


@login_required
def patient_detail(request, patient_id):
    """View for displaying patient details"""
    patient = get_object_or_404(Patient, id=patient_id)

    # Set patient context in session for cross-page availability
    request.session['current_patient_id'] = patient.id
    request.session['current_patient_last_accessed'] = timezone.now().timestamp()

    # Calculate patient age
    today = timezone.now().date()
    age = today.year - patient.date_of_birth.year - (
        (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
    )

    # Get recent appointments
    recent_appointments = Appointment.objects.filter(
        patient=patient
    ).order_by('-appointment_date')[:5]

    # Get recent consultations
    recent_consultations = Consultation.objects.filter(
        patient=patient
    ).order_by('-consultation_date')[:5]

    # Get recent prescriptions
    recent_prescriptions = Prescription.objects.filter(
        patient=patient
    ).order_by('-prescription_date')[:5]

    # Get recent prescriptions
    recent_prescriptions = Prescription.objects.filter(
        patient=patient
    ).order_by('-prescription_date')[:5]
    # Get medical history and clinical notes
    medical_histories = MedicalHistory.objects.filter(patient=patient).order_by('-date')
    clinical_notes = ClinicalNote.objects.filter(patient=patient).order_by('-date')
    context = {
        'patient': patient,
        'age': age,
        'recent_appointments': recent_appointments,
        'recent_consultations': recent_consultations,
        'recent_prescriptions': recent_prescriptions,
        'medical_histories': medical_histories,
        'clinical_notes': clinical_notes,
        'page_title': f'Patient Details - {patient.get_full_name()}',
        'active_nav': 'patients',
    }

    return render(request, 'patients/patient_detail.html', context)


@login_required
def edit_patient(request, patient_id):
    """View for editing patient information"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient {patient.get_full_name()} updated successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = PatientForm(instance=patient)
    
    context = {
        'form': form,
        'patient': patient,
        'page_title': f'Edit Patient - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/edit.html', context)


@login_required
def toggle_patient_status(request, patient_id):
    """View for toggling patient active status"""
    patient = get_object_or_404(Patient, id=patient_id)
    patient.is_active = not patient.is_active
    patient.save()
    
    status = "activated" if patient.is_active else "deactivated"
    messages.success(request, f'Patient {patient.get_full_name()} has been {status}.')
    
    return redirect('patients:detail', patient_id=patient.id)


@login_required
def search_patients(request):
    """View for searching patients via AJAX"""
    query = request.GET.get('q', '')
    patients = Patient.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(patient_id__icontains=query)
    ).filter(is_active=True)[:10]
    
    patient_data = []
    for patient in patients:
        patient_data.append({
            'id': patient.id,
            'name': patient.get_full_name(),
            'patient_id': patient.patient_id,
            'phone_number': patient.phone_number,
        })
    
    return JsonResponse({'patients': patient_data})


@login_required
def edit_medical_history(request, history_id):
    """View for editing patient medical history"""
    medical_history = get_object_or_404(MedicalHistory, id=history_id)
    
    if request.method == 'POST':
        form = MedicalHistoryForm(request.POST, instance=medical_history)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medical history updated successfully.')
            return redirect('patients:medical_history', patient_id=medical_history.patient.id)
    else:
        form = MedicalHistoryForm(instance=medical_history)
    
    context = {
        'form': form,
        'medical_history': medical_history,
        'patient': medical_history.patient,
        'page_title': f'Edit Medical History - {medical_history.patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/medical_history_form.html', context)


@login_required
def delete_medical_history(request, history_id):
    """View for deleting patient medical history"""
    medical_history = get_object_or_404(MedicalHistory, id=history_id)
    patient_id = medical_history.patient.id
    
    if request.method == 'POST':
        medical_history.delete()
        messages.success(request, 'Medical history deleted successfully.')
        return redirect('patients:medical_history', patient_id=patient_id)
    
    context = {
        'medical_history': medical_history,
        'patient': medical_history.patient,
        'page_title': f'Delete Medical History - {medical_history.patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/delete_medical_history.html', context)


@login_required
def patient_medical_history(request, patient_id):
    """View for displaying patient medical history"""
    patient = get_object_or_404(Patient, id=patient_id)
    medical_histories = MedicalHistory.objects.filter(patient=patient).order_by('-date')
    
    context = {
        'patient': patient,
        'medical_histories': medical_histories,
        'page_title': f'Medical History - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/patient_medical_history.html', context)


@login_required
def patient_vitals(request, patient_id):
    """View for displaying patient vitals"""
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'POST':
        vitals_form = VitalsForm(request.POST, user=request.user)
        if vitals_form.is_valid():
            vital = vitals_form.save(commit=False)
            vital.patient = patient
            # Auto-populate recorded_by if not provided
            if not vital.recorded_by and request.user.is_authenticated:
                if hasattr(request.user, 'get_full_name') and request.user.get_full_name():
                    vital.recorded_by = request.user.get_full_name()
                else:
                    vital.recorded_by = request.user.username
            vital.save()
            messages.success(request, 'Vital signs recorded successfully.')
            return redirect('patients:vitals', patient_id=patient.id)
    else:
        vitals_form = VitalsForm(user=request.user)

    # Use safe vitals utility function to handle InvalidOperation errors
    vitals = get_safe_vitals_for_patient(patient)
    if not vitals:
        # Check if there were any vitals at all (vs. just invalid ones)
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM patients_vitals WHERE patient_id = %s", [patient_id])
                total_count = cursor.fetchone()[0]
            if total_count > 0:
                messages.warning(request, 'Some vital records could not be displayed due to data issues.')
        except Exception:
            pass

    context = {
        'patient': patient,
        'vitals': vitals,
        'vitals_form': vitals_form,
        'page_title': f'Patient Vitals - {patient.get_full_name()}',
        'active_nav': 'patients',
    }

    return render(request, 'patients/patient_vitals.html', context)


# PWA functionality disabled
# @login_required
# def pwa_manifest(request):
#     """View for PWA manifest"""
#     from django.http import JsonResponse
# 
#     manifest = {
#         "name": "Hospital Management System",
#         "short_name": "HMS",
#         "description": "Comprehensive Hospital Management System",
#         "start_url": "/",
#         "display": "standalone",
#         "background_color": "#ffffff",
#         "theme_color": "#4e73df",
#         "icons": [
#             {
#                 "src": "/static/img/icon-192x192.png",
#                 "sizes": "192x192",
#                 "type": "image/png"
#             },
#             {
#                 "src": "/static/img/icon-512x512.png",
#                 "sizes": "512x512",
#                 "type": "image/png"
#             }
#         ]
#     }
# 
#     return JsonResponse(manifest, content_type='application/manifest+json')


# PWA functionality disabled
# @login_required
# def service_worker(request):
#     """View for service worker"""
#     from django.http import HttpResponse
# 
#     service_worker_js = """
#     const CACHE_NAME = 'hms-cache-v1';
#     const urlsToCache = [
#         '/',
#         '/static/css/sb-admin-2.min.css',
#         '/static/js/sb-admin-2.min.js',
#         '/static/vendor/jquery/jquery.min.js',
#         '/static/vendor/bootstrap/js/bootstrap.bundle.min.js',
#     ];
# 
#     self.addEventListener('install', function(event) {
#         event.waitUntil(
#             caches.open(CACHE_NAME)
#                 .then(function(cache) {
#                     return cache.addAll(urlsToCache);
#                 })
#         );
#     });
# 
#     self.addEventListener('fetch', function(event) {
#         event.respondWith(
#             caches.match(event.request)
#                 .then(function(response) {
#                     if (response) {
#                         return response;
#                     }
#                     return fetch(event.request);
#                 })
#         );
#     });
#     """
# 
#     return HttpResponse(service_worker_js, content_type='application/javascript')
# 
# 
# @login_required
# def offline_fallback(request):
#     """View for offline fallback"""
#     context = {
#         'page_title': 'Offline - HMS',
#         'message': 'You are currently offline. Please check your internet connection.',
#     }
#     return render(request, 'patients/offline.html', context)
# 
# 
# @login_required
# def pwa_demo(request):
#     """View for PWA demo"""
#     # Implementation for PWA demo
#     pass
# 
# 
# @login_required
# def demo_push_notification(request):
#     """View for demo push notification"""
#     # Implementation for demo push notification
#     pass


@login_required
def check_patient_nhia(request):
    """View for checking patient NHIA status"""
    patient_id = request.GET.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Patient ID is required'}, status=400)

    try:
        patient = Patient.objects.get(id=patient_id)
        has_nhia = patient.is_nhia_patient()
        nhia_status = {
            'has_nhia': has_nhia,
            'patient_name': patient.get_full_name(),
            'patient_id': patient.patient_id,
        }

        if has_nhia and hasattr(patient, 'nhia_info'):
            nhia_status.update({
                'nhia_reg_number': patient.nhia_info.nhia_reg_number,
                'is_active': patient.nhia_info.is_active,
            })

        return JsonResponse(nhia_status)
    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)


@login_required
def wallet_dashboard(request, patient_id):
    """View for patient wallet dashboard"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    # Get transaction statistics
    wallet_stats = wallet.get_transaction_statistics()
    
    # Calculate totals
    total_credits = wallet.get_total_credits()
    total_debits = wallet.get_total_debits()
    
    # Calculate monthly activity
    from django.utils import timezone
    from datetime import timedelta
    
    # Get transactions from the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    monthly_transactions = wallet.transactions.filter(
        created_at__gte=thirty_days_ago
    )
    
    monthly_credits = monthly_transactions.filter(
        transaction_type__in=['credit', 'deposit', 'refund', 'transfer_in', 'adjustment']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_debits = monthly_transactions.filter(
        transaction_type__in=['debit', 'payment', 'withdrawal', 'transfer_out']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Get recent transactions (last 10)
    recent_transactions = wallet.get_transaction_history(limit=10)
    
    # Get recent admissions (last 5)
    try:
        from inpatient.models import Admission
        recent_admissions = Admission.objects.filter(
            patient=patient
        ).order_by('-admission_date')[:5]
    except:
        recent_admissions = []
    
    # Calculate hospital services total (admission fees and daily charges)
    hospital_services_stats = wallet_stats.get('by_category', {}).get('hospital_services', {})
    hospital_services_total = hospital_services_stats.get('total', 0)
    
    # Get current admission if any
    current_admission = None
    try:
        from inpatient.models import Admission
        current_admission = Admission.objects.filter(
            patient=patient,
            status='admitted'
        ).first()
    except:
        pass
    
    # Get outstanding invoices for the new functionality
    outstanding_invoices = []
    total_outstanding = 0
    try:
        from billing.models import Invoice
        outstanding_invoices = Invoice.objects.filter(
            patient=patient,
            status__in=['pending', 'partially_paid']
        ).order_by('created_at')
        total_outstanding = sum(invoice.get_balance() for invoice in outstanding_invoices)
    except:
        pass
    
    # Calculate total outstanding from admissions and invoices
    admission_outstanding = 0
    if current_admission:
        admission_outstanding = current_admission.get_outstanding_admission_cost()
    
    total_outstanding = admission_outstanding + total_outstanding
    
    context = {
        'patient': patient,
        'wallet_stats': wallet_stats,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'monthly_credits': monthly_credits,
        'monthly_debits': monthly_debits,
        'recent_transactions': recent_transactions,
        'recent_admissions': recent_admissions,
        'hospital_services_total': hospital_services_total,
        'current_admission': current_admission,
        'outstanding_invoices': outstanding_invoices,
        'total_outstanding': total_outstanding,
        'admission_outstanding': admission_outstanding,
        'wallet': wallet,
        'page_title': f'Wallet - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/wallet_dashboard.html', context)


@login_required
def add_funds_to_wallet(request, patient_id):
    """View for adding funds to patient wallet"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    # Calculate outstanding amounts for display
    from inpatient.models import Admission
    from billing.models import Invoice
    
    active_admissions = Admission.objects.filter(
        patient=patient,
        status='admitted'
    )
    
    admission_outstanding = sum(
        admission.get_outstanding_admission_cost()
        for admission in active_admissions
    )
    
    outstanding_invoices = Invoice.objects.filter(
        patient=patient,
        status__in=['pending', 'partially_paid']
    )
    
    invoice_outstanding = sum(
        invoice.get_balance() for invoice in outstanding_invoices
    )
    
    total_outstanding = admission_outstanding + invoice_outstanding
    
    if request.method == 'POST':
        form = AddFundsForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description'] or 'Funds added to wallet'
            payment_method = form.cleaned_data['payment_method']
            apply_to_outstanding = request.POST.get('apply_to_outstanding') == 'on'
            
            # Credit the wallet
            wallet.credit(
                amount=amount,
                description=f"{description} (Payment method: {payment_method})",
                transaction_type='deposit',
                user=request.user,
                apply_to_outstanding=apply_to_outstanding
            )
            
            if apply_to_outstanding and total_outstanding > 0:
                amount_applied = min(amount, total_outstanding)
                messages.success(request, f'Successfully added ₦{amount} to {patient.get_full_name()}\'s wallet. ₦{amount_applied} automatically applied to outstanding charges.')
            else:
                messages.success(request, f'Successfully added ₦{amount} to {patient.get_full_name()}\'s wallet.')
            
            return redirect('patients:wallet_dashboard', patient_id=patient.id)
    else:
        form = AddFundsForm()
    
    context = {
        'patient': patient,
        'wallet': wallet,
        'form': form,
        'total_outstanding': total_outstanding,
        'admission_outstanding': admission_outstanding,
        'invoice_outstanding': invoice_outstanding,
        'active_admissions': active_admissions,
        'outstanding_invoices': outstanding_invoices,
        'page_title': f'Add Funds - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/wallet_add_funds.html', context)


@login_required
def wallet_transactions(request, patient_id):
    """View for displaying patient wallet transactions"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get wallet transactions
    try:
        transactions = patient.wallet.transactions.all().order_by('-created_at')
        
        # Filter by admission if specified
        admission_id = request.GET.get('admission')
        if admission_id:
            try:
                from inpatient.models import Admission
                admission = Admission.objects.get(id=admission_id, patient=patient)
                transactions = transactions.filter(admission=admission)
            except:
                pass
        
        # Filter by transaction type if specified
        transaction_type = request.GET.get('type')
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
                
    except AttributeError:
        # If patient doesn't have a wallet yet
        transactions = []
    
    # Get current admission if any
    current_admission = None
    try:
        from inpatient.models import Admission
        current_admission = Admission.objects.filter(
            patient=patient,
            status='admitted'
        ).first()
    except:
        pass

    context = {
        'patient': patient,
        'transactions': transactions,
        'current_admission': current_admission,
        'page_title': f'Wallet Transactions - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/wallet_transactions.html', context)


@login_required
def wallet_withdrawal(request, patient_id):
    """View for patient wallet withdrawal"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    if request.method == 'POST':
        form = WalletWithdrawalForm(request.POST, wallet=wallet)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description'] or 'Wallet withdrawal'
            withdrawal_method = form.cleaned_data['withdrawal_method']
            
            # Debit the wallet
            wallet.debit(
                amount=amount,
                description=f"{description} (Withdrawal method: {withdrawal_method})",
                transaction_type='withdrawal',
                user=request.user
            )
            
            messages.success(request, f'Successfully withdrew ₦{amount} from {patient.get_full_name()}\'s wallet.')
            return redirect('patients:wallet_dashboard', patient_id=patient.id)
    else:
        form = WalletWithdrawalForm(wallet=wallet)
    
    context = {
        'patient': patient,
        'wallet': wallet,
        'form': form,
        'page_title': f'Withdraw Funds - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/wallet_withdrawal.html', context)


@login_required
def wallet_transfer(request, patient_id):
    """View for patient wallet transfer"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    if request.method == 'POST':
        form = WalletTransferForm(request.POST, wallet=wallet)
        if form.is_valid():
            recipient_patient = form.cleaned_data['recipient_patient']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description'] or 'Wallet transfer'
            
            # Get or create wallet for recipient
            recipient_wallet, created = PatientWallet.objects.get_or_create(patient=recipient_patient)
            
            try:
                # Transfer funds between wallets
                wallet.transfer_to(
                    recipient_wallet=recipient_wallet,
                    amount=amount,
                    description=description,
                    user=request.user
                )
                
                messages.success(request, f'Successfully transferred ₦{amount} from {patient.get_full_name()}\'s wallet to {recipient_patient.get_full_name()}\'s wallet.')
                return redirect('patients:wallet_dashboard', patient_id=patient.id)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = WalletTransferForm(wallet=wallet)
    
    context = {
        'patient': patient,
        'wallet': wallet,
        'form': form,
        'page_title': f'Transfer Funds - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/wallet_transfer.html', context)


@login_required
def wallet_refund(request, patient_id):
    """View for patient wallet refund"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    if request.method == 'POST':
        form = WalletRefundForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            reason = form.cleaned_data['reason']
            reference_invoice = form.cleaned_data['reference_invoice']
            
            # Credit the wallet (refund)
            wallet.credit(
                amount=amount,
                description=f"Refund: {reason}" + (f" (Invoice: {reference_invoice})" if reference_invoice else ""),
                transaction_type='refund',
                user=request.user
            )
            
            messages.success(request, f'Successfully refunded ₦{amount} to {patient.get_full_name()}\'s wallet.')
            return redirect('patients:wallet_dashboard', patient_id=patient.id)
    else:
        form = WalletRefundForm()
    
    context = {
        'patient': patient,
        'wallet': wallet,
        'form': form,
        'page_title': f'Process Refund - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/wallet_refund.html', context)


@login_required
def wallet_adjustment(request, patient_id):
    """View for patient wallet adjustment"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    if request.method == 'POST':
        form = WalletAdjustmentForm(request.POST)
        if form.is_valid():
            adjustment_type = form.cleaned_data['adjustment_type']
            amount = form.cleaned_data['amount']
            reason = form.cleaned_data['reason']
            
            if adjustment_type == 'credit':
                # Credit the wallet
                wallet.credit(
                    amount=amount,
                    description=f"Adjustment (Credit): {reason}",
                    transaction_type='adjustment',
                    user=request.user
                )
                messages.success(request, f'Successfully credited ₦{amount} to {patient.get_full_name()}\'s wallet.')
            else:  # debit
                # Debit the wallet
                wallet.debit(
                    amount=amount,
                    description=f"Adjustment (Debit): {reason}",
                    transaction_type='adjustment',
                    user=request.user
                )
                messages.success(request, f'Successfully debited ₦{amount} from {patient.get_full_name()}\'s wallet.')
            
            return redirect('patients:wallet_dashboard', patient_id=patient.id)
    else:
        form = WalletAdjustmentForm()
    
    context = {
        'patient': patient,
        'wallet': wallet,
        'form': form,
        'page_title': f'Wallet Adjustment - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/wallet_adjustment.html', context)


@login_required
def wallet_settlement(request, patient_id):
    """View for settling patient wallet outstanding balance"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    if request.method == 'POST':
        try:
            # Attempt to settle the outstanding balance
            settlement_result = wallet.settle_outstanding_balance(
                description="Outstanding balance settlement",
                user=request.user
            )
            
            if settlement_result['settled']:
                messages.success(request, settlement_result['message'])
            else:
                messages.info(request, settlement_result['message'])
                
        except Exception as e:
            messages.error(request, f'Error settling wallet balance: {str(e)}')
        
        return redirect('patients:wallet_dashboard', patient_id=patient.id)
    
    # For GET requests, show confirmation page
    context = {
        'patient': patient,
        'wallet': wallet,
        'outstanding_balance': abs(wallet.balance) if wallet.balance < 0 else 0,
        'page_title': f'Settle Wallet - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/wallet_settlement.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def wallet_payment(request, patient_id):
    """View for paying outstanding amounts from patient wallet balance"""
    from django.http import JsonResponse
    from billing.models import Invoice
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    if request.method == 'POST':
        try:
            # Get the settlement result
            settlement_result = wallet.settle_outstanding_balance(
                description="Wallet payment for outstanding amounts",
                user=request.user
            )
            
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('Accept') == 'application/json':
                # Return JSON response for AJAX requests
                return JsonResponse(settlement_result)
            else:
                # Return redirect for form submissions
                if settlement_result['settled']:
                    messages.success(request, settlement_result['message'])
                else:
                    messages.info(request, settlement_result['message'])
                
                return redirect('patients:wallet_dashboard', patient_id=patient.id)
                
        except Exception as e:
            error_message = f'Error processing wallet payment: {str(e)}'
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('Accept') == 'application/json':
                return JsonResponse({'error': error_message}, status=400)
            else:
                messages.error(request, error_message)
                return redirect('patients:wallet_dashboard', patient_id=patient.id)
    
    # For GET requests, show payment page
    # Get outstanding invoices
    outstanding_invoices = Invoice.objects.filter(
        patient=patient,
        status__in=['pending', 'partially_paid']
    ).order_by('created_at')
    
    total_outstanding = sum(invoice.get_balance() for invoice in outstanding_invoices)
    
    context = {
        'patient': patient,
        'wallet': wallet,
        'outstanding_invoices': outstanding_invoices,
        'total_outstanding': total_outstanding,
        'page_title': f'Wallet Payment - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/wallet_payment.html', context)


@login_required
def wallet_list(request):
    """View to display all patient wallets"""
    wallets = PatientWallet.objects.select_related('patient').all()
    
    # Calculate statistics
    total_balance = sum(wallet.balance for wallet in wallets)
    positive_wallets = sum(1 for wallet in wallets if wallet.balance > 0)
    zero_wallets = sum(1 for wallet in wallets if wallet.balance == 0)
    negative_wallets = sum(1 for wallet in wallets if wallet.balance < 0)
    
    context = {
        'wallets': wallets,
        'total_balance': total_balance,
        'positive_wallets': positive_wallets,
        'zero_wallets': zero_wallets,
        'negative_wallets': negative_wallets,
        'page_title': 'All Wallets',
        'active_nav': 'wallet',
    }
    
    return render(request, 'patients/wallet_list.html', context)


@login_required
def wallet_net_impact_fallback(request):
    """Fallback view for wallet_net_impact URL when no patient_id is provided"""
    # When no patient_id is provided, redirect to the global net impact view
    return redirect('patients:wallet_net_impact_global')


@login_required
def wallet_net_impact_global(request):
    """View for analyzing and applying net impact to patient wallet"""
    # Show the global net impact report
    # Get all wallets with their net impact
    wallets = PatientWallet.objects.select_related('patient').filter(patient__isnull=False)
    
    # Calculate net impact for each wallet
    wallet_data = []
    total_net_impact = 0
    total_balance = 0
    
    for wallet in wallets:
        net_impact = wallet.get_total_wallet_impact_with_admissions()
        wallet_data.append({
            'wallet': wallet,
            'net_impact': net_impact,
            'balance': wallet.balance,
        })
        total_net_impact += net_impact
        total_balance += wallet.balance
    
    # Calculate difference
    difference = total_net_impact - total_balance
    
    context = {
        'wallet_data': wallet_data,
        'total_net_impact': total_net_impact,
        'total_balance': total_balance,
        'difference': difference,
        'total_wallets': len(wallet_data),
        'page_title': 'Wallet Net Impact',
        'active_nav': 'wallet',
    }
    
    return render(request, 'patients/wallet_net_impact_global.html', context)


@login_required
def wallet_net_impact(request, patient_id):
    """View for showing patient's wallet net impact analysis"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    # Get all active admissions for this patient
    from inpatient.models import Admission
    active_admissions = Admission.objects.filter(
        patient=patient,
        status='admitted'
    )
    
    # Calculate outstanding admission costs
    admission_outstanding = sum(
        admission.get_outstanding_admission_cost()
        for admission in active_admissions
    )
    
    # Get all outstanding invoices for this patient
    from billing.models import Invoice
    outstanding_invoices = Invoice.objects.filter(
        patient=patient,
        status__in=['pending', 'partially_paid']
    )
    
    # Calculate outstanding invoice amounts
    invoice_outstanding = sum(
        invoice.get_balance() for invoice in outstanding_invoices
    )
    
    # Total outstanding amount (admissions + invoices)
    total_outstanding = admission_outstanding + invoice_outstanding
    
    # Calculate net impact without updating the balance
    net_impact_without_update = wallet.get_total_wallet_impact_with_admissions(update_balance=False)
    
    # Calculate projected balance after applying net impact
    projected_balance = max(net_impact_without_update, 0)
    
    context = {
        'patient': patient,
        'wallet': wallet,
        'active_admissions': active_admissions,
        'outstanding_invoices': outstanding_invoices,
        'admission_outstanding': admission_outstanding,
        'invoice_outstanding': invoice_outstanding,
        'total_outstanding': total_outstanding,
        'net_impact_without_update': net_impact_without_update,
        'projected_balance': projected_balance,
        'page_title': f'Wallet Net Impact - {patient.get_full_name()}',
    }
    
    return render(request, 'patients/wallet_net_impact.html', context)


@login_required
def apply_wallet_net_impact(request, patient_id):
    """View for applying net impact calculation to patient wallet"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    if request.method == 'POST':
        try:
            # Apply net impact calculation and update wallet balance
            net_impact = wallet.get_total_wallet_impact_with_admissions(update_balance=True)
            
            # Determine if the balance is positive or negative
            if net_impact >= 0:
                message = f'Successfully applied net impact calculation. New wallet balance: ₦{net_impact:.2f}'
                messages.success(request, message)
            else:
                message = f'Applied net impact calculation. Wallet balance is now ₦0.00 with outstanding debt of ₦{abs(net_impact):.2f}'
                messages.warning(request, message)
            
            return redirect('patients:wallet_net_impact', patient_id=patient.id)
            
        except Exception as e:
            messages.error(request, f'Error applying net impact calculation: {str(e)}')
            return redirect('patients:wallet_net_impact', patient_id=patient.id)
    
    # If not POST, redirect to the net impact page
    return redirect('patients:wallet_net_impact', patient_id=patient.id)


@login_required
def register_nhia_patient(request, patient_id):
    """View for registering NHIA patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for registering NHIA patient
    pass


@login_required
def edit_nhia_patient(request, patient_id):
    """View for editing NHIA patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    # Implementation for editing NHIA patient
    pass


@login_required
def patient_dashboard(request, patient_id):
    """Enhanced patient dashboard showing comprehensive patient information"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Calculate patient age
    today = timezone.now().date()
    age = today.year - patient.date_of_birth.year - (
        (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
    )
    
    # Get recent appointments (last 6 months)
    six_months_ago = today - timedelta(days=180)
    recent_appointments = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=six_months_ago
    ).order_by('-appointment_date')
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=today,
        status__in=['scheduled', 'confirmed']
    ).order_by('appointment_date')
    
    # Get recent consultations
    recent_consultations = Consultation.objects.filter(
        patient=patient
    ).order_by('-consultation_date')[:5]
    
    # Get recent prescriptions
    recent_prescriptions = Prescription.objects.filter(
        patient=patient
    ).order_by('-prescription_date')[:5]
    
    # Get recent lab tests
    recent_lab_tests = TestRequest.objects.filter(
        patient=patient
    ).order_by('-request_date')[:5]
    
    # Get recent radiology orders
    recent_radiology_orders = RadiologyOrder.objects.filter(
        patient=patient
    ).order_by('-order_date')[:5]
    
    # Get appointment statistics
    total_appointments = Appointment.objects.filter(patient=patient).count()
    completed_appointments = Appointment.objects.filter(
        patient=patient, 
        status='completed'
    ).count()
    
    # Get consultation statistics
    total_consultations = Consultation.objects.filter(patient=patient).count()
    completed_consultations = Consultation.objects.filter(
        patient=patient, 
        status='completed'
    ).count()
    
    context = {
        'patient': patient,
        'age': age,
        'recent_appointments': recent_appointments,
        'upcoming_appointments': upcoming_appointments,
        'recent_consultations': recent_consultations,
        'recent_prescriptions': recent_prescriptions,
        'recent_lab_tests': recent_lab_tests,
        'recent_radiology_orders': recent_radiology_orders,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'total_consultations': total_consultations,
        'completed_consultations': completed_consultations,
        'page_title': f'Patient Dashboard - {patient.get_full_name()}',
        'active_nav': 'patients',
    }

    return render(request, 'patients/patient_dashboard.html', context)


@login_required
@csrf_exempt
def clear_patient_context(request):
    """
    View for clearing the current patient context from session.
    Used by the frontend to clear patient context when needed.
    """
    if request.method == 'POST':
        # Clear patient context from session
        if 'current_patient_id' in request.session:
            del request.session['current_patient_id']

        if 'current_patient_last_accessed' in request.session:
            del request.session['current_patient_last_accessed']

        return JsonResponse({'success': True, 'message': 'Patient context cleared successfully'})

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def add_clinical_note(request, patient_id):
    """View for adding a clinical note to a patient"""
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'POST':
        form = ClinicalNoteForm(request.POST, user=request.user)
        if form.is_valid():
            clinical_note = form.save(commit=False)
            clinical_note.patient = patient
            clinical_note.save()
            messages.success(request, 'Clinical note added successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = ClinicalNoteForm(user=request.user)

    context = {
        'form': form,
        'patient': patient,
        'page_title': f'Add Clinical Note - {patient.get_full_name()}',
        'active_nav': 'patients',
    }

    return render(request, 'patients/clinical_note_form.html', context)


@login_required
def edit_clinical_note(request, note_id):
    """View for editing a clinical note"""
    clinical_note = get_object_or_404(ClinicalNote, id=note_id)

    if request.method == 'POST':
        form = ClinicalNoteForm(request.POST, instance=clinical_note, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinical note updated successfully.')
            return redirect('patients:detail', patient_id=clinical_note.patient.id)
    else:
        form = ClinicalNoteForm(instance=clinical_note, user=request.user)

    context = {
        'form': form,
        'clinical_note': clinical_note,
        'patient': clinical_note.patient,
        'page_title': f'Edit Clinical Note - {clinical_note.patient.get_full_name()}',
        'active_nav': 'patients',
    }

    return render(request, 'patients/clinical_note_form.html', context)


@login_required
def delete_clinical_note(request, note_id):
    """View for deleting a clinical note"""
    clinical_note = get_object_or_404(ClinicalNote, id=note_id)
    patient_id = clinical_note.patient.id

    if request.method == 'POST':
        clinical_note.delete()
        messages.success(request, 'Clinical note deleted successfully.')
        return redirect('patients:detail', patient_id=patient_id)

    context = {
        'clinical_note': clinical_note,
        'patient': clinical_note.patient,
        'page_title': f'Delete Clinical Note - {clinical_note.patient.get_full_name()}',
        'active_nav': 'patients',
    }

    return render(request, 'patients/delete_clinical_note.html', context)