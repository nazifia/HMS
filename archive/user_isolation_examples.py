"""
User Isolation Implementation Examples for HMS
This file shows how to implement user isolation in views and models.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, UpdateView
from django.contrib import messages
from django.db import transaction
from user_isolation_middleware import (
    require_user_isolation, 
    resource_lock_required, 
    DatabaseIsolationMixin,
    get_user_isolation_info
)

# Example: Patient management with user isolation

@login_required
@require_user_isolation
@resource_lock_required('patient')
def edit_patient(request, patient_id):
    """
    Edit patient with user isolation to prevent concurrent modifications.
    """
    from patients.models import Patient
    from patients.forms import PatientForm
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check if user has access to this patient
    isolation_mixin = DatabaseIsolationMixin()
    if not isolation_mixin.check_object_access(request, patient):
        messages.error(request, "You don't have permission to edit this patient.")
        return redirect('patients:list')
    
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            with transaction.atomic():
                # Save with isolation context
                patient = form.save()
                
                # Log the modification with user isolation info
                isolation_info = get_user_isolation_info(request)
                print(f"Patient {patient.id} modified by session {isolation_info['session_id']}")
                
                messages.success(request, "Patient updated successfully.")
                return redirect('patients:detail', patient_id=patient.id)
    else:
        form = PatientForm(instance=patient)
    
    return render(request, 'patients/edit.html', {
        'form': form,
        'patient': patient,
        'isolation_info': get_user_isolation_info(request)
    })


@login_required
@require_user_isolation
@resource_lock_required('prescription')
def dispense_medication(request, prescription_id):
    """
    Dispense medication with user isolation to prevent double dispensing.
    """
    from pharmacy.models import Prescription, DispensingLog
    from pharmacy.forms import DispensingForm
    
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Check if prescription is already being processed
    isolation_info = get_user_isolation_info(request)
    if f"prescription_{prescription_id}" in isolation_info['active_locks']:
        return JsonResponse({
            'error': 'This prescription is currently being processed by another user.',
            'status': 'locked'
        }, status=423)
    
    if request.method == 'POST':
        form = DispensingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Create dispensing log
                dispensing_log = DispensingLog.objects.create(
                    prescription_item=prescription.items.first(),
                    quantity_dispensed=form.cleaned_data['quantity'],
                    dispensed_by=request.user,
                    session_id=isolation_info['session_id']
                )
                
                # Update prescription status
                prescription.status = 'dispensed'
                prescription.save()
                
                messages.success(request, "Medication dispensed successfully.")
                return JsonResponse({'status': 'success', 'message': 'Dispensed successfully'})
    else:
        form = DispensingForm()
    
    return render(request, 'pharmacy/dispense.html', {
        'form': form,
        'prescription': prescription,
        'isolation_info': isolation_info
    })


class IsolatedPatientListView(ListView, DatabaseIsolationMixin):
    """
    Patient list view with user isolation.
    """
    model = None  # Will be set dynamically
    template_name = 'patients/list.html'
    context_object_name = 'patients'
    paginate_by = 20
    
    def get_queryset(self):
        from patients.models import Patient
        
        # Get base queryset
        queryset = Patient.objects.all()
        
        # Apply user isolation filtering
        queryset = self.get_isolated_queryset(self.request, queryset)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['isolation_info'] = get_user_isolation_info(self.request)
        return context


class IsolatedPatientDetailView(DetailView, DatabaseIsolationMixin):
    """
    Patient detail view with user isolation.
    """
    model = None  # Will be set dynamically
    template_name = 'patients/detail.html'
    context_object_name = 'patient'
    
    def get_object(self, queryset=None):
        from patients.models import Patient
        
        obj = get_object_or_404(Patient, pk=self.kwargs['pk'])
        
        # Check access with isolation
        if not self.check_object_access(self.request, obj):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to view this patient.")
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['isolation_info'] = get_user_isolation_info(self.request)
        
        # Check if patient is currently being edited by another user
        patient_id = self.object.id
        isolation_info = context['isolation_info']
        context['is_locked'] = f"patient_{patient_id}" in isolation_info.get('active_locks', [])
        
        return context


# Example: Billing with user isolation

@login_required
@require_user_isolation
@resource_lock_required('invoice')
def process_payment(request, invoice_id):
    """
    Process payment with user isolation to prevent double payments.
    """
    from billing.models import Invoice, Payment
    from billing.forms import PaymentForm
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Check if invoice is already paid
    if invoice.status == 'paid':
        messages.warning(request, "This invoice has already been paid.")
        return redirect('billing:detail', invoice_id=invoice.id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Create payment record
                payment = Payment.objects.create(
                    invoice=invoice,
                    amount=form.cleaned_data['amount'],
                    payment_method=form.cleaned_data['payment_method'],
                    processed_by=request.user
                )
                
                # Update invoice status
                invoice.status = 'paid'
                invoice.save()
                
                # Log with isolation info
                isolation_info = get_user_isolation_info(request)
                print(f"Payment processed for invoice {invoice.id} by session {isolation_info['session_id']}")
                
                messages.success(request, "Payment processed successfully.")
                return redirect('billing:detail', invoice_id=invoice.id)
    else:
        form = PaymentForm()
    
    return render(request, 'billing/payment.html', {
        'form': form,
        'invoice': invoice,
        'isolation_info': get_user_isolation_info(request)
    })


# Example: Laboratory with user isolation

@login_required
@require_user_isolation
@resource_lock_required('test_result')
def enter_test_results(request, test_request_id):
    """
    Enter test results with user isolation to prevent conflicts.
    """
    from laboratory.models import TestRequest, TestResult
    from laboratory.forms import TestResultForm
    
    test_request = get_object_or_404(TestRequest, id=test_request_id)
    
    # Check if results already exist
    if hasattr(test_request, 'result'):
        messages.warning(request, "Results have already been entered for this test.")
        return redirect('laboratory:test_detail', test_id=test_request.id)
    
    if request.method == 'POST':
        form = TestResultForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Create test result
                result = TestResult.objects.create(
                    test_request=test_request,
                    result_value=form.cleaned_data['result_value'],
                    notes=form.cleaned_data['notes'],
                    entered_by=request.user
                )
                
                # Update test request status
                test_request.status = 'completed'
                test_request.save()
                
                messages.success(request, "Test results entered successfully.")
                return redirect('laboratory:test_detail', test_id=test_request.id)
    else:
        form = TestResultForm()
    
    return render(request, 'laboratory/enter_results.html', {
        'form': form,
        'test_request': test_request,
        'isolation_info': get_user_isolation_info(request)
    })


# Utility functions for monitoring user isolation

def get_isolation_status(request):
    """
    Get current isolation status for monitoring dashboard.
    """
    if hasattr(request, 'isolation_context'):
        middleware = None
        # Get middleware instance (this would need to be implemented properly)
        # middleware = get_middleware_instance('UserIsolationMiddleware')
        
        if middleware:
            return middleware.get_active_sessions_info()
    
    return {
        'total_sessions': 0,
        'active_locks': 0,
        'sessions': {},
        'locks': {}
    }


@login_required
def isolation_monitoring_dashboard(request):
    """
    Dashboard to monitor user isolation status.
    """
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Superuser privileges required.")
        return redirect('dashboard:home')
    
    isolation_status = get_isolation_status(request)
    
    return render(request, 'admin/isolation_monitoring.html', {
        'isolation_status': isolation_status,
        'current_user_isolation': get_user_isolation_info(request)
    })


# Example template context processor for isolation info

def isolation_context_processor(request):
    """
    Context processor to add isolation info to all templates.
    """
    return {
        'user_isolation_info': get_user_isolation_info(request)
    }
