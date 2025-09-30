from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from .models import RadiologyOrder, RadiologyResult
from .enhanced_forms import EnhancedRadiologyResultForm, RadiologyResultVerificationForm
from patients.models import Patient


@login_required
def enhanced_add_result(request, order_id):
    """Enhanced view for adding/editing radiology test results"""
    order = get_object_or_404(RadiologyOrder, pk=order_id)

    # Check authorization requirement BEFORE allowing result entry
    can_process, message = order.can_be_processed()
    if not can_process:
        messages.error(request, message)
        return redirect('radiology:order_detail', order_id=order.id)

    # Check if result already exists
    try:
        result = order.result
    except RadiologyResult.DoesNotExist:
        result = None
    
    # Handle form submission
    if request.method == 'POST':
        form = EnhancedRadiologyResultForm(
            request.POST, 
            request.FILES, 
            instance=result,
            radiology_order=order
        )
        
        # Handle different submit actions
        if 'save_draft' in request.POST:
            if form.is_valid():
                result_obj = form.save(commit=False)
                result_obj.order = order
                result_obj.performed_by = request.user
                result_obj.result_status = 'draft'
                result_obj.save()
                messages.success(request, 'Result saved as draft successfully.')
                return redirect('radiology:enhanced_add_result', order_id=order.id)
                
        elif 'submit_result' in request.POST:
            if form.is_valid():
                result_obj = form.save(commit=False)
                result_obj.order = order
                result_obj.performed_by = request.user
                result_obj.result_status = 'submitted'
                result_obj.save()
                messages.success(request, 'Result submitted successfully.')
                return redirect('radiology:order_detail', order_id=order.id)
                
        elif 'submit_and_verify' in request.POST:
            # This requires special permissions
            if request.user.groups.filter(
                name__in=['Senior Radiologists', 'Radiology Consultants']
            ).exists():
                if form.is_valid():
                    result_obj = form.save(commit=False)
                    result_obj.order = order
                    result_obj.performed_by = request.user
                    result_obj.result_status = 'verified'
                    result_obj.verified_by = request.user
                    result_obj.verified_date = timezone.now()
                    result_obj.save()
                    messages.success(request, 'Result submitted and verified successfully.')
                    return redirect('radiology:order_detail', order_id=order.id)
            else:
                messages.error(request, 'You do not have permission to verify results.')
    else:
        # Initialize form with default values
        form = EnhancedRadiologyResultForm(instance=result, radiology_order=order)
    
    # Get previous studies for this patient
    previous_studies = RadiologyResult.objects.filter(
        order__patient=order.patient
    ).exclude(
        order=order
    ).select_related('order__test').order_by('-study_date')[:5]
    
    context = {
        'form': form,
        'radiology_order': order,
        'result': result,
        'previous_studies': previous_studies,
        'title': f'Radiology Result Entry - {order.test.name}'
    }
    
    return render(request, 'radiology/enhanced_result_entry.html', context)


@login_required
def verify_result(request, result_id):
    """View for verifying radiology results"""
    result = get_object_or_404(RadiologyResult, pk=result_id)
    
    # Check permissions
    if not request.user.groups.filter(name__in=['Senior Radiologists', 'Radiology Consultants']).exists():
        messages.error(request, 'You do not have permission to verify results.')
        return redirect('radiology:order_detail', order_id=result.order.id)
    
    if request.method == 'POST':
        form = RadiologyResultVerificationForm(request.POST, instance=result)
        if form.is_valid():
            with transaction.atomic():
                result_obj = form.save(commit=False)
                result_obj.result_status = 'verified'
                result_obj.verified_date = timezone.now()
                result_obj.save()
                
                # Add verification notes if provided
                verification_notes = form.cleaned_data.get('verification_notes')
                if verification_notes:
                    if result_obj.verification_notes:
                        result_obj.verification_notes += f"\n\n--- Verification on {timezone.now().strftime('%Y-%m-%d %H:%M')} ---\n{verification_notes}"
                    else:
                        result_obj.verification_notes = verification_notes
                    result_obj.save()
                
                messages.success(request, 'Result verified successfully.')
                return redirect('radiology:order_detail', order_id=result.order.id)
    else:
        form = RadiologyResultVerificationForm(instance=result)
    
    context = {
        'form': form,
        'result': result,
        'title': f'Verify Result - {result.order.test.name}'
    }
    
    return render(request, 'radiology/verify_result.html', context)


@login_required
def finalize_result(request, result_id):
    """View for finalizing radiology results"""
    result = get_object_or_404(RadiologyResult, pk=result_id)
    
    # Check permissions
    if not request.user.groups.filter(name__in=['Senior Radiologists', 'Radiology Consultants', 'Department Heads']).exists():
        messages.error(request, 'You do not have permission to finalize results.')
        return redirect('radiology:order_detail', order_id=result.order.id)
    
    if request.method == 'POST':
        # Finalize the result
        result.result_status = 'finalized'
        result.save()
        messages.success(request, 'Result finalized successfully.')
        return redirect('radiology:order_detail', order_id=result.order.id)
    
    context = {
        'result': result,
        'title': f'Finalize Result - {result.order.test.name}'
    }
    
    return render(request, 'radiology/finalize_result.html', context)


@login_required
def result_search(request):
    """View for searching radiology results"""
    from .enhanced_forms import RadiologyResultSearchForm
    from django.db import models
    
    form = RadiologyResultSearchForm(request.GET or None)
    results = []
    
    if form.is_valid():
        search = form.cleaned_data.get('search')
        test = form.cleaned_data.get('test')
        category = form.cleaned_data.get('category')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        status = form.cleaned_data.get('status')
        radiologist = form.cleaned_data.get('radiologist')
        
        # Build queryset
        queryset = RadiologyResult.objects.select_related(
            'order__patient', 
            'order__test', 
            'order__test__category',
            'performed_by',
            'radiologist'
        )
        
        # Apply filters
        if search:
            queryset = queryset.filter(
                models.Q(order__patient__first_name__icontains=search) |
                models.Q(order__patient__last_name__icontains=search) |
                models.Q(order__test__name__icontains=search)
            )
            
        if test:
            queryset = queryset.filter(order__test=test)
            
        if category:
            queryset = queryset.filter(order__test__category=category)
            
        if date_from:
            queryset = queryset.filter(study_date__gte=date_from)
            
        if date_to:
            queryset = queryset.filter(study_date__lte=date_to)
            
        if status:
            queryset = queryset.filter(result_status=status)
            
        if radiologist:
            queryset = queryset.filter(radiologist=radiologist)
            
        results = queryset.order_by('-study_date')
    
    context = {
        'form': form,
        'results': results,
        'title': 'Radiology Results Search'
    }
    
    return render(request, 'radiology/result_search.html', context)


@login_required
def quick_result_entry(request, order_id):
    """Quick result entry for simple cases"""
    from .enhanced_forms import QuickRadiologyResultForm
    
    order = get_object_or_404(RadiologyOrder, pk=order_id)
    
    if request.method == 'POST':
        form = QuickRadiologyResultForm(request.POST)
        if form.is_valid():
            findings = form.cleaned_data['findings']
            impression = form.cleaned_data['impression']
            status = form.cleaned_data['status']
            
            # Create or update result
            result, created = RadiologyResult.objects.get_or_create(
                order=order,
                defaults={
                    'performed_by': request.user,
                    'findings': findings,
                    'impression': impression,
                    'is_abnormal': status != 'normal',
                }
            )
            
            if not created:
                result.findings = findings
                result.impression = impression
                result.is_abnormal = status != 'normal'
                result.updated_at = timezone.now()
                result.save()
            
            # Handle urgent status
            if status == 'urgent':
                # Send notification or flag for urgent review
                messages.warning(request, 'This result has been flagged as urgent and requires immediate attention.')
            
            messages.success(request, 'Quick result saved successfully.')
            return redirect('radiology:order_detail', order_id=order.id)
    else:
        form = QuickRadiologyResultForm()
    
    context = {
        'form': form,
        'order': order,
        'title': f'Quick Result Entry - {order.test.name}'
    }
    
    return render(request, 'radiology/quick_result_entry.html', context)