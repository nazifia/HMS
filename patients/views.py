from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from .models import Patient, MedicalHistory, Vitals, PatientWallet, WalletTransaction
from .forms import PatientForm, MedicalHistoryForm, VitalsForm, AddFundsForm, WalletWithdrawalForm, WalletTransferForm, WalletRefundForm, WalletAdjustmentForm
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
    from .forms import PatientSearchForm
    
    # Initialize search form
    search_form = PatientSearchForm(request.GET or None)
    
    # Get all active patients
    patients = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    # Apply search filters if form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        gender = search_form.cleaned_data.get('gender')
        blood_group = search_form.cleaned_data.get('blood_group')
        city = search_form.cleaned_data.get('city')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        
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
        if city:
            patients = patients.filter(city__icontains=city)
        if date_from:
            patients = patients.filter(registration_date__gte=date_from)
        if date_to:
            patients = patients.filter(registration_date__lte=date_to)
    
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
    
    context = {
        'patient': patient,
        'age': age,
        'recent_appointments': recent_appointments,
        'recent_consultations': recent_consultations,
        'recent_prescriptions': recent_prescriptions,
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


@login_required
def pwa_manifest(request):
    """View for PWA manifest"""
    from django.http import JsonResponse

    manifest = {
        "name": "Hospital Management System",
        "short_name": "HMS",
        "description": "Comprehensive Hospital Management System",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#4e73df",
        "icons": [
            {
                "src": "/static/img/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/img/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }

    return JsonResponse(manifest, content_type='application/manifest+json')


@login_required
def service_worker(request):
    """View for service worker"""
    from django.http import HttpResponse

    service_worker_js = """
    const CACHE_NAME = 'hms-cache-v1';
    const urlsToCache = [
        '/',
        '/static/css/sb-admin-2.min.css',
        '/static/js/sb-admin-2.min.js',
        '/static/vendor/jquery/jquery.min.js',
        '/static/vendor/bootstrap/js/bootstrap.bundle.min.js',
    ];

    self.addEventListener('install', function(event) {
        event.waitUntil(
            caches.open(CACHE_NAME)
                .then(function(cache) {
                    return cache.addAll(urlsToCache);
                })
        );
    });

    self.addEventListener('fetch', function(event) {
        event.respondWith(
            caches.match(event.request)
                .then(function(response) {
                    if (response) {
                        return response;
                    }
                    return fetch(event.request);
                })
        );
    });
    """

    return HttpResponse(service_worker_js, content_type='application/javascript')


@login_required
def offline_fallback(request):
    """View for offline fallback"""
    context = {
        'page_title': 'Offline - HMS',
        'message': 'You are currently offline. Please check your internet connection.',
    }
    return render(request, 'patients/offline.html', context)


@login_required
def pwa_demo(request):
    """View for PWA demo"""
    # Implementation for PWA demo
    pass


@login_required
def demo_push_notification(request):
    """View for demo push notification"""
    # Implementation for demo push notification
    pass


@login_required
def check_patient_nhia(request):
    """View for checking patient NHIA status"""
    patient_id = request.GET.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Patient ID is required'}, status=400)

    try:
        patient = Patient.objects.get(id=patient_id)
        nhia_status = {
            'has_nhia': hasattr(patient, 'nhia_info') and patient.nhia_info is not None,
            'patient_name': patient.get_full_name(),
            'patient_id': patient.patient_id,
        }

        if nhia_status['has_nhia']:
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
    
    # Calculate hospital services total (admission fees and daily charges)
    hospital_services_stats = wallet.get_transaction_statistics().get('by_category', {}).get('hospital_services', {})
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
    
    context = {
        'patient': patient,
        'hospital_services_total': hospital_services_total,
        'current_admission': current_admission,
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
    
    if request.method == 'POST':
        form = AddFundsForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description'] or 'Funds added to wallet'
            payment_method = form.cleaned_data['payment_method']
            
            # Credit the wallet
            wallet.credit(
                amount=amount,
                description=f"{description} (Payment method: {payment_method})",
                transaction_type='deposit',
                user=request.user
            )
            
            messages.success(request, f'Successfully added ₦{amount} to {patient.get_full_name()}\'s wallet.')
            return redirect('patients:wallet_dashboard', patient_id=patient.id)
    else:
        form = AddFundsForm()
    
    context = {
        'patient': patient,
        'wallet': wallet,
        'form': form,
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