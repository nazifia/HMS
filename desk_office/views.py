from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
import string
import random
from .forms import AuthorizationCodeForm, PatientSearchForm
from nhia.models import AuthorizationCode
from patients.models import Patient

@login_required
def generate_authorization_code(request):
    # Handle AJAX POST request for code generation from modal
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 'patient_id' in request.POST:
        try:
            patient_id = request.POST.get('patient_id')
            amount = request.POST.get('amount')
            expiry_days = int(request.POST.get('expiry_days', 30))
            code_type = request.POST.get('code_type', 'auto')
            notes = request.POST.get('notes', '')
            manual_code = request.POST.get('manual_code', '')

            # Validate patient
            try:
                patient = Patient.objects.get(id=patient_id, patient_type='nhia')
            except Patient.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid patient selected. Please select an NHIA patient.'
                })

            # Validate amount
            try:
                amount = float(amount)
                if amount <= 0:
                    return JsonResponse({
                        'success': False,
                        'message': 'Amount must be greater than zero.'
                    })
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid amount provided.'
                })

            # Generate or use manual code
            if code_type == 'manual' and manual_code:
                code_str = manual_code.strip().upper()
                # Check if code already exists
                if AuthorizationCode.objects.filter(code=code_str).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Authorization code "{code_str}" already exists. Please use a different code.'
                    })
            else:
                # Auto-generate unique code
                while True:
                    date_str = timezone.now().strftime('%Y%m%d')
                    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    code_str = f"AUTH-{date_str}-{random_str}"
                    if not AuthorizationCode.objects.filter(code=code_str).exists():
                        break

            # Calculate expiry date
            expiry_date = timezone.now() + timedelta(days=expiry_days)

            # Create authorization code
            auth_code = AuthorizationCode.objects.create(
                code=code_str,
                patient=patient,
                service_type='general',  # Default service type
                amount=amount,
                expiry_date=expiry_date,
                status='active',
                notes=notes,
                generated_by=request.user
            )

            return JsonResponse({
                'success': True,
                'code': auth_code.code,
                'message': f'Authorization code {auth_code.code} generated successfully for {patient.get_full_name()}.'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error generating authorization code: {str(e)}'
            })

    patient_search_form = PatientSearchForm()
    authorization_form = None
    selected_patient = None

    # Handle patient search
    if request.method == 'POST' and 'search_patients' in request.POST:
        patient_search_form = PatientSearchForm(request.POST)
        if patient_search_form.is_valid():
            search_query = patient_search_form.cleaned_data.get('search')
            if search_query:
                # Search for NHIA patients by name or patient ID
                patients = Patient.objects.filter(
                    patient_type='nhia'
                ).filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(patient_id__icontains=search_query)
                )
                context = {
                    'patient_search_form': patient_search_form,
                    'patients': patients,
                    'search_query': search_query
                }
                return render(request, 'desk_office/generate_authorization_code.html', context)
    
    # Handle patient selection
    if request.method == 'GET' and 'patient_id' in request.GET:
        try:
            # Try to look up by primary key first, then by custom patient_id
            patient_identifier = request.GET.get('patient_id')
            try:
                if str(patient_identifier).isdigit():
                    selected_patient = Patient.objects.get(id=patient_identifier, patient_type='nhia')
                else:
                    raise Patient.DoesNotExist
            except Patient.DoesNotExist:
                # Try custom patient_id
                selected_patient = Patient.objects.get(patient_id=patient_identifier, patient_type='nhia')
            
            # Check for existing active authorization code
            existing_code = AuthorizationCode.objects.filter(
                patient=selected_patient,
                status='active'
            ).first()
            
            initial_data = {}
            if existing_code:
                messages.warning(request, f'This patient already has an active authorization code: {existing_code.code}')
            
            # Pre-fill amount if provided in URL
            if 'amount' in request.GET:
                try:
                    amount = float(request.GET.get('amount'))
                    initial_data['amount'] = amount
                except (ValueError, TypeError):
                    pass
            
            authorization_form = AuthorizationCodeForm(patient=selected_patient, initial=initial_data)
            
            # Pass existing code to context
            context = {
                'patient_search_form': patient_search_form,
                'authorization_form': authorization_form,
                'selected_patient': selected_patient,
                'existing_code': existing_code
            }
            return render(request, 'desk_office/generate_authorization_code.html', context)
            
        except Patient.DoesNotExist:
            messages.error(request, 'Selected patient not found or is not an NHIA patient.')

    # Handle authorization code generation
    if request.method == 'POST' and 'generate_code' in request.POST:
        try:
            patient_id = request.POST.get('patient_id')
            selected_patient = Patient.objects.get(id=patient_id, patient_type='nhia')
            authorization_form = AuthorizationCodeForm(request.POST, patient=selected_patient)
            if authorization_form.is_valid():
                authorization_code = authorization_form.save()
                messages.success(request, f'Authorization code {authorization_code.code} generated successfully.')
                return redirect('desk_office:authorization_code_list')
            else:
                # Form is not valid, we'll display errors
                pass
        except Patient.DoesNotExist:
            messages.error(request, 'Selected patient not found or is not an NHIA patient.')
            authorization_form = AuthorizationCodeForm()
    
    context = {
        'patient_search_form': patient_search_form,
        'authorization_form': authorization_form,
        'selected_patient': selected_patient
    }
    return render(request, 'desk_office/generate_authorization_code.html', context)

def verify_authorization_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            authorization_code = AuthorizationCode.objects.get(code=code)
            # You can add more logic here to check the status of the code
            messages.success(request, f'Authorization code {authorization_code.code} is valid.')
            return render(request, 'desk_office/verify_authorization_code.html', {'authorization_code': authorization_code})
        except AuthorizationCode.DoesNotExist:
            messages.error(request, 'Invalid authorization code.')
            return redirect('desk_office:verify_authorization_code')
    return render(request, 'desk_office/verify_authorization_code.html')

def search_nhia_patients_ajax(request):
    """AJAX endpoint for searching NHIA patients"""
    if request.method == 'GET' and 'q' in request.GET:
        term = request.GET.get('q')
        patient_type = request.GET.get('patient_type', 'nhia')
        quick = request.GET.get('quick', 'false')
        
        if len(term) >= 2:
            patients = Patient.objects.filter(
                patient_type=patient_type
            ).filter(
                Q(first_name__icontains=term) |
                Q(last_name__icontains=term) |
                Q(patient_id__icontains=term) |
                Q(nhia_info__nhia_reg_number__icontains=term) |
                Q(phone_number__icontains=term)
            ).select_related('nhia_info')[:10]
            
            results = []
            for patient in patients:
                patient_data = {
                    'id': patient.pk,
                    'text': f"{patient.get_full_name()} ({patient.patient_id})",
                    'full_name': patient.get_full_name(),
                    'patient_id': patient.patient_id,
                    'age': patient.age,
                    'gender': patient.get_gender_display(),
                    'patient_type': patient.get_patient_type_display
                }
                
                if patient.nhia_info:
                    patient_data['nhia_number'] = patient.nhia_info.nhia_reg_number
                
                if quick == 'true':
                    # For quick code generation modal
                    results.append({
                        'id': patient.pk,
                        'text': f"{patient.get_full_name()} ({patient.patient_id})",
                        'full_name': patient.get_full_name(),
                        'patient_id': patient.patient_id
                    })
                else:
                    # For regular patient search
                    nhia_info = f'<br><small class="text-info">NHIA: {patient.nhia_info.nhia_reg_number}</small>' if patient.nhia_info else ''
                    auth_dashboard_url = reverse('desk_office:authorization_dashboard')
                    html = f"""
                    <div class="patient-result-item card mb-2 p-3" onclick="window.location.href='{auth_dashboard_url}?patient_id={patient.pk}'">
                        <div class="row">
                            <div class="col-md-8">
                                <strong>{patient.get_full_name()}</strong>
                                <br>
                                <small class="text-muted">
                                    ID: {patient.patient_id} | 
                                    Phone: {patient.phone_number} |
                                    Age: {patient.age}
                                </small>
                                {nhia_info}
                            </div>
                            <div class="col-md-4 text-end">
                                <span class="badge bg-primary">{patient.get_patient_type_display}</span>
                                <span class="badge bg-secondary">{patient.get_gender_display}</span>
                            </div>
                        </div>
                    </div>
                    """
                    results.append({
                        'id': patient.pk,
                        'html': html
                    })
            
            return JsonResponse({'results': results})
    
    return JsonResponse({'results': []})


def cancel_authorization_code(request, code_id):
    """Cancel an authorization code"""
    if request.method == 'POST':
        try:
            auth_code = AuthorizationCode.objects.get(code=code_id)
            if auth_code.status == 'active':
                auth_code.status = 'cancelled'
                auth_code.save()
                messages.success(request, f'Authorization code {auth_code.code} has been cancelled.')
            else:
                messages.warning(request, 'Only active authorization codes can be cancelled.')
        except AuthorizationCode.DoesNotExist:
            messages.error(request, 'Authorization code not found.')
    
    return redirect(request.META.get('HTTP_REFERER', 'desk_office:authorization_code_list'))


def authorization_code_detail(request, code_id):
    """AJAX endpoint for authorization code details"""
    from django.http import HttpResponse
    try:
        auth_code = AuthorizationCode.objects.select_related('patient', 'generated_by').get(code=code_id)

        nhia_info = f'<p><strong>NHIA Number:</strong> {auth_code.patient.nhia_info.nhia_reg_number}</p>' if hasattr(auth_code.patient, 'nhia_info') and auth_code.patient.nhia_info else ''

        # Determine status badge color
        status_colors = {
            'active': 'success',
            'used': 'info',
            'expired': 'secondary',
            'cancelled': 'danger'
        }
        status_color = status_colors.get(auth_code.status, 'secondary')

        # Format used information
        used_info = ''
        if auth_code.status == 'used' and hasattr(auth_code, 'used_at') and auth_code.used_at:
            used_info = f'<p><strong>Used At:</strong> {auth_code.used_at.strftime("%b %d, %Y %H:%M")}</p>'

        # Format notes
        notes_info = f'<p><strong>Notes:</strong> {auth_code.notes}</p>' if auth_code.notes else ''

        html = f"""
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-primary mb-3"><i class="fas fa-qrcode"></i> Code Information</h6>
                <p><strong>Code:</strong> <code class="text-primary">{auth_code.code}</code></p>
                <p><strong>Status:</strong> <span class="badge bg-{status_color}">{auth_code.get_status_display()}</span></p>
                <p><strong>Generated:</strong> {auth_code.generated_at.strftime('%b %d, %Y %H:%M')}</p>
                <p><strong>Generated By:</strong> {auth_code.generated_by.get_full_name() if auth_code.generated_by else 'System'}</p>
                <p><strong>Expires:</strong> {auth_code.expiry_date.strftime('%b %d, %Y') if auth_code.expiry_date else 'Never'}</p>
                {used_info}
                <p><strong>Amount:</strong> <span class="text-success fw-bold">₦{auth_code.amount:,.2f}</span></p>
                {notes_info}
            </div>
            <div class="col-md-6">
                <h6 class="text-primary mb-3"><i class="fas fa-user"></i> Patient Information</h6>
                <p><strong>Name:</strong> {auth_code.patient.get_full_name()}</p>
                <p><strong>Patient ID:</strong> {auth_code.patient.patient_id}</p>
                <p><strong>Patient Type:</strong> <span class="badge bg-info">{auth_code.patient.get_patient_type_display()}</span></p>
                {nhia_info}
                <p><strong>Phone:</strong> {auth_code.patient.phone_number if auth_code.patient.phone_number else 'N/A'}</p>
                <p><strong>Age:</strong> {auth_code.patient.age if hasattr(auth_code.patient, 'age') else 'N/A'}</p>
                <p><strong>Gender:</strong> {auth_code.patient.get_gender_display() if hasattr(auth_code.patient, 'get_gender_display') else 'N/A'}</p>
            </div>
        </div>
        """
        return HttpResponse(html)
    except AuthorizationCode.DoesNotExist:
        return HttpResponse('<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> Authorization code not found.</div>')