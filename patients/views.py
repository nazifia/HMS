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
from .models import Patient, MedicalHistory, Vitals, PatientWallet, WalletTransaction, ClinicalNote, PhysiotherapyRequest, SharedWallet, WalletMembership
from .forms import PatientForm, MedicalHistoryForm, VitalsForm, AddFundsForm, WalletWithdrawalForm, WalletTransferForm, WalletRefundForm, WalletAdjustmentForm, ClinicalNoteForm, PhysiotherapyRequestForm
from .utils import get_safe_vitals_for_patient
from accounts.permissions import permission_required, user_has_permission
from appointments.models import Appointment
from consultations.models import Consultation
from pharmacy.models import Prescription
from laboratory.models import TestRequest
from radiology.models import RadiologyOrder
from datetime import datetime, timedelta


@login_required
@permission_required('patients.view')
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
        diagnosis = request.GET.get('diagnosis', '').strip()
        retainership_number = request.GET.get('retainership_number', '').strip()

        # Apply search query filter
        if search_query:
            patients = patients.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(patient_id__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(retainership_info__retainership_reg_number__icontains=search_query)
            )

        # Apply diagnosis filter
        if diagnosis:
            # Search across consultations, medical histories, and physiotherapy requests
            patients = patients.filter(
                Q(consultations__diagnosis__icontains=diagnosis) |
                Q(medical_histories__diagnosis__icontains=diagnosis) |
                Q(physiotherapy_requests__diagnosis__icontains=diagnosis)
            ).distinct()

        # Apply additional filters
        if gender:
            patients = patients.filter(gender=gender)
        if blood_group:
            patients = patients.filter(blood_group=blood_group)
        if patient_type:
            patients = patients.filter(patient_type=patient_type)
        if city:
            patients = patients.filter(city__icontains=city)
        if retainership_number:
            patients = patients.filter(retainership_info__retainership_reg_number__icontains=retainership_number)
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
            patient = form.save(commit=False)
            # Ensure patient is always registered as active
            patient.is_active = True
            patient.save()
            messages.success(request, f'Patient {patient.get_full_name()} registered successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = PatientForm(initial={'is_active': True})
    
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
    
    # Get physiotherapy requests
    physiotherapy_requests = PhysiotherapyRequest.objects.filter(patient=patient).order_by('-request_date')
    
    # Get NHIA and Retainership information
    nhia_info = getattr(patient, 'nhia_info', None)
    retainership_info = getattr(patient, 'retainership_info', None)
    
    # Get wallet information
    has_wallet = hasattr(patient, 'wallet') and patient.wallet is not None
    wallet_is_active = has_wallet and patient.wallet.is_active
    
    # Get retainership wallet information
    retainership_wallet = None
    if hasattr(patient, 'wallet_memberships'):
        retainership_wallet = patient.wallet_memberships.filter(wallet__wallet_type='retainership').first()
    # Get recent vitals using the safe utility function
    vitals = get_safe_vitals_for_patient(patient)
    
    context = {
        'patient': patient,
        'age': age,
        'recent_appointments': recent_appointments,
        'recent_consultations': recent_consultations,
        'recent_prescriptions': recent_prescriptions,
        'medical_histories': medical_histories,
        'clinical_notes': clinical_notes,
        'physiotherapy_requests': physiotherapy_requests,
        'nhia_info': nhia_info,
        'retainership_info': retainership_info,
        'has_wallet': has_wallet,
        'wallet_is_active': wallet_is_active,
        'retainership_wallet': retainership_wallet,
        'vitals': vitals,
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
@permission_required('patients.view')
def search_patients(request):
    """View for searching patients"""
    # Handle AJAX search requests
    if 'q' in request.GET or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.GET.get('q', '')
        patients = Patient.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(patient_id__icontains=query) |
            Q(phone_number__icontains=query)
        ).filter(is_active=True)[:10]
        
        patient_data = []
        for patient in patients:
            patient_data.append({
                'id': patient.id,
                'name': patient.get_full_name(),
                'patient_id': patient.patient_id,
                'phone_number': patient.phone_number or 'N/A',
            })
        
        return JsonResponse({'patients': patient_data})
    
    # Handle regular page requests
    context = {
        'page_title': 'Search Patients',
        'active_nav': 'patients',
    }
    
    return render(request, 'patients/search.html', context)


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
        'total_invoice_outstanding': total_outstanding,  # Alias for clarity in template
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
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    if created:
        messages.info(request, f'A wallet has been automatically created for {patient.get_full_name()}.')
    
    # Get wallet transactions
    transactions = wallet.transactions.all().order_by('-created_at')
    
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
        'wallet': wallet,
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
    """View to display all patient wallets with search functionality"""
    from .forms import WalletSearchForm
    
    # Initialize search form
    search_form = WalletSearchForm(request.GET or None)
    
    # Start with all wallets
    wallets = PatientWallet.objects.select_related('patient').all()
    
    # Apply search filters if form is valid
    if search_form.is_valid():
        patient_name = search_form.cleaned_data.get('patient_name')
        patient_id_or_phone = search_form.cleaned_data.get('patient_id_or_phone')
        patient_type = search_form.cleaned_data.get('patient_type')
        balance_filter = search_form.cleaned_data.get('balance_filter')
        min_balance = search_form.cleaned_data.get('min_balance')
        max_balance = search_form.cleaned_data.get('max_balance')
        
        # Apply name search filter
        if patient_name:
            wallets = wallets.filter(
                Q(patient__first_name__icontains=patient_name) |
                Q(patient__last_name__icontains=patient_name)
            )
        
        # Apply ID or phone number search filter
        if patient_id_or_phone:
            wallets = wallets.filter(
                Q(patient__patient_id__icontains=patient_id_or_phone) |
                Q(patient__phone_number__icontains=patient_id_or_phone)
            )
        
        # Apply patient type filter
        if patient_type:
            if patient_type == 'nhia':
                wallets = wallets.filter(patient__is_nhia=True)
            elif patient_type == 'retainership':
                wallets = wallets.filter(patient__is_retainership=True)
            elif patient_type == 'regular':
                wallets = wallets.filter(patient__is_nhia=False, patient__is_retainership=False)
        
        # Apply balance filter
        if balance_filter:
            if balance_filter == 'positive':
                wallets = wallets.filter(balance__gt=0)
            elif balance_filter == 'zero':
                wallets = wallets.filter(balance=0)
            elif balance_filter == 'negative':
                wallets = wallets.filter(balance__lt=0)
        
        # Apply min/max balance filters
        if min_balance is not None:
            wallets = wallets.filter(balance__gte=min_balance)
        
        if max_balance is not None:
            wallets = wallets.filter(balance__lte=max_balance)
    
    # Calculate statistics for filtered results
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
        'search_form': search_form,
        'total_wallets': wallets.count(),
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
    from nhia.models import NHIAPatient
    from nhia.views import generate_nhia_reg_number
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check if patient is already registered for NHIA
    if hasattr(patient, 'nhia_info'):
        messages.warning(request, f'{patient.get_full_name()} is already registered for NHIA.')
        return redirect('patients:detail', patient_id=patient.id)
    
    if request.method == 'POST':
        # Update patient type to NHIA
        patient.patient_type = 'nhia'
        patient.save()
        
        # Create NHIA patient record
        nhia_patient = NHIAPatient.objects.create(
            patient=patient,
            nhia_reg_number=generate_nhia_reg_number(),
            is_active=True
        )
        
        messages.success(request, f'{patient.get_full_name()} has been successfully registered for NHIA with registration number {nhia_patient.nhia_reg_number}.')
        return redirect('patients:detail', patient_id=patient.id)
    
    # For GET request, show confirmation form
    context = {
        'patient': patient,
        'title': f'Register {patient.get_full_name()} for NHIA'
    }
    return render(request, 'patients/nhia_registration_form.html', context)


@login_required
def edit_nhia_patient(request, patient_id):
    """View for editing NHIA patient"""
    from nhia.models import NHIAPatient
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check if patient has NHIA record
    if not hasattr(patient, 'nhia_info'):
        messages.error(request, f'{patient.get_full_name()} is not registered for NHIA.')
        return redirect('patients:detail', patient_id=patient.id)
    
    nhia_patient = patient.nhia_info
    
    if request.method == 'POST':
        # Update NHIA status
        is_active = request.POST.get('is_active', 'off') == 'on'
        nhia_patient.is_active = is_active
        nhia_patient.save()
        
        status = "activated" if is_active else "deactivated"
        messages.success(request, f'{patient.get_full_name()} NHIA registration has been {status}.')
        return redirect('patients:detail', patient_id=patient.id)
    
    # For GET request, show edit form
    context = {
        'patient': patient,
        'nhia_patient': nhia_patient,
        'title': f'Edit NHIA Registration for {patient.get_full_name()}'
    }
    return render(request, 'patients/edit_nhia_patient.html', context)


@login_required
def register_retainership_patient(request, patient_id):
    """View for registering retainership patient"""
    from retainership.models import RetainershipPatient
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check if patient is already registered for retainership
    if hasattr(patient, 'retainership_info'):
        messages.warning(request, f'{patient.get_full_name()} is already registered for retainership.')
        return redirect('patients:detail', patient_id=patient.id)
    
    if request.method == 'POST':
        # Update patient type to retainership
        patient.patient_type = 'retainership'
        patient.save()
        
        # Generate a retainership registration number (3 billion to 4 billion range)
        import random
        while True:
            retainership_reg_number = random.randint(3000000000, 3999999999)
            if not RetainershipPatient.objects.filter(retainership_reg_number=retainership_reg_number).exists():
                break
        
        # Create retainership patient record
        retainership_patient = RetainershipPatient.objects.create(
            patient=patient,
            retainership_reg_number=retainership_reg_number,
            is_active=True
        )
        
        messages.success(request, f'{patient.get_full_name()} has been successfully registered for retainership with registration number {retainership_patient.retainership_reg_number}.')
        return redirect('patients:detail', patient_id=patient.id)
    
    # For GET request, show confirmation form
    context = {
        'patient': patient,
        'title': f'Register {patient.get_full_name()} for Retainership'
    }
    return render(request, 'patients/retainership_registration_form.html', context)


@login_required
def add_vaccination(request, patient_id):
    """View for adding vaccination record to patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == 'POST':
        # Extract form data
        vaccine_type = request.POST.get('vaccine_type')
        vaccine_name = request.POST.get('vaccine_name')
        manufacturer = request.POST.get('manufacturer')
        lot_number = request.POST.get('lot_number')
        expiration_date = request.POST.get('expiration_date')
        dose_number = request.POST.get('dose_number')
        vaccination_date = request.POST.get('vaccination_date')
        admin_by = request.POST.get('administered_by')
        site = request.POST.get('site')
        notes = request.POST.get('notes')
        
        # Basic validation
        if not all([vaccine_type, vaccine_name, vaccination_date, admin_by]):
            messages.error(request, 'Please fill in all required vaccination fields.')
            return redirect('patients:detail', patient_id=patient.id)
        
        try:
            # Create vaccination record (model needs to be created if it doesn't exist)
            from patients.models import VaccinationRecord
            vaccination = VaccinationRecord.objects.create(
                patient=patient,
                vaccine_type=vaccine_type,
                vaccine_name=vaccine_name,
                manufacturer=manufacturer,
                lot_number=lot_number,
                expiration_date=expiration_date,
                dose_number=dose_number,
                vaccination_date=vaccination_date,
                admin_by=request.user if admin_by else None,
                site=site,
                notes=notes
            )
            
            messages.success(request, f'Vaccination record added successfully for {patient.get_full_name()}.')
            return redirect('patients:detail', patient_id=patient.id)
            
        except Exception as e:
            messages.error(request, f'Error adding vaccination record: {str(e)}')
            return redirect('patients:detail', patient_id=patient.id)
    
    # For GET request, show confirmation form
    context = {
        'patient': patient,
        'title': f'Add Vaccination for {patient.get_full_name()}'
    }
    return render(request, 'patients/vaccination_form.html', context)


@login_required
def edit_retainership_patient(request, patient_id):
    """View for editing retainership patient"""
    from retainership.models import RetainershipPatient
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check if patient has retainership record
    if not hasattr(patient, 'retainership_info'):
        messages.error(request, f'{patient.get_full_name()} is not registered for retainership.')
        return redirect('patients:detail', patient_id=patient.id)
    
    retainership_patient = patient.retainership_info
    
    if request.method == 'POST':
        # Update retainership status
        is_active = request.POST.get('is_active', 'off') == 'on'
        retainership_patient.is_active = is_active
        retainership_patient.save()
        
        status = "activated" if is_active else "deactivated"
        messages.success(request, f'{patient.get_full_name()} retainership registration has been {status}.')
        return redirect('patients:detail', patient_id=patient.id)
    
    # For GET request, show edit form
    context = {
        'patient': patient,
        'retainership_patient': retainership_patient,
        'title': f'Edit Retainership Registration for {patient.get_full_name()}'
    }
    return render(request, 'patients/edit_retainership_patient.html', context)


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


@login_required
@permission_required('medical.create')
def create_physiotherapy_request(request, patient_id):
    """View for creating a physiotherapy request for a patient"""
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'POST':
        form = PhysiotherapyRequestForm(request.POST, user=request.user)
        if form.is_valid():
            physiotherapy_request = form.save(commit=False)
            physiotherapy_request.patient = patient
            physiotherapy_request.save()
            messages.success(request, 'Physiotherapy request created successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = PhysiotherapyRequestForm(user=request.user)

    context = {
        'form': form,
        'patient': patient,
        'page_title': f'Create Physiotherapy Request - {patient.get_full_name()}',
        'active_nav': 'patients',
    }

    return render(request, 'patients/physiotherapy_request_form.html', context)


@login_required
def edit_physiotherapy_request(request, request_id):
    """View for editing a physiotherapy request"""
    physiotherapy_request = get_object_or_404(PhysiotherapyRequest, id=request_id)

    if request.method == 'POST':
        form = PhysiotherapyRequestForm(request.POST, instance=physiotherapy_request, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Physiotherapy request updated successfully.')
            return redirect('patients:detail', patient_id=physiotherapy_request.patient.id)
    else:
        form = PhysiotherapyRequestForm(instance=physiotherapy_request, user=request.user)

    context = {
        'form': form,
        'physiotherapy_request': physiotherapy_request,
        'patient': physiotherapy_request.patient,
        'page_title': f'Edit Physiotherapy Request - {physiotherapy_request.patient.get_full_name()}',
        'active_nav': 'patients',
    }

    return render(request, 'patients/physiotherapy_request_form.html', context)


@login_required
def delete_physiotherapy_request(request, request_id):
    """View for deleting a physiotherapy request"""
    physiotherapy_request = get_object_or_404(PhysiotherapyRequest, id=request_id)
    patient_id = physiotherapy_request.patient.id

    if request.method == 'POST':
        physiotherapy_request.delete()
        messages.success(request, 'Physiotherapy request deleted successfully.')
        return redirect('patients:detail', patient_id=patient_id)

    context = {
        'physiotherapy_request': physiotherapy_request,
        'patient': physiotherapy_request.patient,
        'page_title': f'Delete Physiotherapy Request - {physiotherapy_request.patient.get_full_name()}',
        'active_nav': 'patients',
    }

    return render(request, 'patients/delete_physiotherapy_request.html', context)


@login_required
def update_physiotherapy_status(request, request_id, status):
    """View for updating physiotherapy request status"""
    physiotherapy_request = get_object_or_404(PhysiotherapyRequest, id=request_id)
    
    if status == 'approved':
        physiotherapist_id = request.POST.get('physiotherapist')
        if physiotherapist_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            physiotherapist = get_object_or_404(User, id=physiotherapist_id)
            physiotherapy_request.mark_as_approved(physiotherapist=physiotherapist)
        else:
            physiotherapy_request.mark_as_approved()
    elif status == 'in_progress':
        physiotherapy_request.mark_as_in_progress()
    elif status == 'completed':
        physiotherapy_request.mark_as_completed()
    elif status == 'cancelled':
        physiotherapy_request.cancel_request()
    
    messages.success(request, f'Physiotherapy request marked as {status}.')
    return redirect('patients:detail', patient_id=physiotherapy_request.patient.id)


@login_required
def sync_admission_charges(request, patient_id):
    """View to sync admission charges with wallet transactions"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get or create wallet for patient
    wallet, created = PatientWallet.objects.get_or_create(patient=patient)
    
    if request.method == 'POST':
        try:
            from inpatient.models import Admission
            from django.db import transaction
            from decimal import Decimal
            
            with transaction.atomic():
                # Get current admission
                current_admission = Admission.objects.filter(
                    patient=patient,
                    status='admitted'
                ).first()
                
                if not current_admission:
                    messages.warning(request, 'No active admission found to sync.')
                    return redirect('patients:wallet_dashboard', patient_id=patient.id)
                
                # Get outstanding admission cost
                outstanding_cost = current_admission.get_outstanding_admission_cost()
                
                if outstanding_cost <= 0:
                    messages.info(request, 'No outstanding admission charges to sync.')
                    return redirect('patients:wallet_dashboard', patient_id=patient.id)
                
                # Create wallet transaction for admission fee
                admission_fee = 0
                try:
                    # Check if patient is NHIA
                    is_nhia_patient = (hasattr(patient, 'nhia_info') and
                                     patient.nhia_info and
                                     patient.nhia_info.is_active)
                    if not is_nhia_patient and current_admission.get_duration() >= 1:
                        # Calculate admission fee based on bed charges
                        if current_admission.bed and current_admission.bed.ward:
                            admission_fee = current_admission.bed.ward.charge_per_day
                except:
                    pass
                
                # Create admission fee transaction if applicable
                if admission_fee > 0:
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='admission_fee',
                        amount=admission_fee,
                        balance_after=wallet.balance - admission_fee,
                        description=f'Admission fee synced for Admission #{current_admission.id}',
                        admission=current_admission,
                        created_by=request.user
                    )
                    # Update wallet balance
                    wallet.balance -= admission_fee
                    wallet.save(update_fields=['balance'])
                
                # Create daily admission charge transactions
                duration = current_admission.get_duration()
                daily_charge = 0
                if current_admission.bed and current_admission.bed.ward:
                    daily_charge = current_admission.bed.ward.charge_per_day
                
                # Create charges for days already stayed (exclude today if just admitted)
                days_to_charge = max(0, duration - 1)
                if daily_charge > 0 and days_to_charge > 0:
                    for day in range(days_to_charge):
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            transaction_type='daily_admission_charge',
                            amount=daily_charge,
                            balance_after=wallet.balance - daily_charge,
                            description=f'Daily charge synced - Day {day + 1} for Admission #{current_admission.id}',
                            admission=current_admission,
                            created_by=request.user
                        )
                        # Update wallet balance
                        wallet.balance -= daily_charge
                        wallet.save(update_fields=['balance'])
                
                total_synced = admission_fee + (daily_charge * days_to_charge)
                messages.success(
                    request, 
                    f'Successfully synced ₦{total_synced} in admission charges for {patient.get_full_name()}. '
                    f'Created {1 if admission_fee > 0 else 0} admission fee transaction and {days_to_charge} daily charge transactions.'
                )
                
            return redirect('patients:wallet_dashboard', patient_id=patient.id)
            
        except Exception as e:
            messages.error(request, f'Error syncing admission charges: {str(e)}')
            return redirect('patients:wallet_dashboard', patient_id=patient.id)
    
    # For GET request, show confirmation page
    context = {
        'patient': patient,
        'wallet': wallet,
        'page_title': f'Sync Admission Charges - {patient.get_full_name()}',
        'active_nav': 'patients',
    }
    return render(request, 'patients/sync_admission_charges.html', context)