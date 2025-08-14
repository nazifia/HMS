from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import TestRequest, TestResult, Test, TestParameter, TestResultParameter
from .enhanced_forms import ManualResultEntryForm
from patients.models import Patient

User = get_user_model()


@login_required
@require_http_methods(["GET", "POST"])
def manual_result_entry(request, test_request_id):
    """
    Manual result entry view for laboratory tests
    """
    test_request = get_object_or_404(TestRequest, id=test_request_id)
    
    # Get lab staff for dropdowns
    lab_staff = User.objects.filter(
        is_active=True,
        groups__name__in=['Laboratory Staff', 'Lab Technicians', 'Medical Laboratory Scientists']
    ).distinct()
    
    # Get previous results for this patient
    previous_results = TestResult.objects.filter(
        test_request__patient=test_request.patient
    ).exclude(test_request=test_request).order_by('-result_date')[:5]
    
    if request.method == 'POST':
        return handle_manual_result_submission(request, test_request, lab_staff)
    
    # GET request - show form
    form = ManualResultEntryForm(test_request=test_request)
    
    context = {
        'test_request': test_request,
        'form': form,
        'lab_staff': lab_staff,
        'previous_results': previous_results,
        'title': f'Manual Result Entry - {test_request.patient.get_full_name()}'
    }
    
    return render(request, 'laboratory/manual_result_entry.html', context)


def handle_manual_result_submission(request, test_request, lab_staff):
    """Handle the submission of manual result entry"""
    
    form = ManualResultEntryForm(request.POST, request.FILES, test_request=test_request)
    
    if form.is_valid():
        try:
            with transaction.atomic():
                # Create the test result
                test_result = TestResult.objects.create(
                    test_request=test_request,
                    test=form.cleaned_data['test'],
                    result_date=form.cleaned_data['result_date'],
                    sample_collection_date=form.cleaned_data.get('sample_collection_date'),
                    sample_collected_by=form.cleaned_data.get('sample_collected_by'),
                    result_file=form.cleaned_data.get('result_file'),
                    notes=form.cleaned_data.get('technician_notes', ''),
                    performed_by=form.cleaned_data['performed_by']
                )
                
                # Process manual parameters
                parameter_count = 0
                for key in request.POST.keys():
                    if key.startswith('parameter_name_'):
                        index = key.split('_')[-1]
                        
                        param_name = request.POST.get(f'parameter_name_{index}')
                        param_value = request.POST.get(f'parameter_value_{index}')
                        param_unit = request.POST.get(f'parameter_unit_{index}', '')
                        param_range = request.POST.get(f'parameter_range_{index}', '')
                        param_status = request.POST.get(f'parameter_status_{index}', 'normal')
                        param_notes = request.POST.get(f'parameter_notes_{index}', '')
                        
                        if param_name and param_value:
                            # Create or get test parameter
                            test_parameter, created = TestParameter.objects.get_or_create(
                                test=form.cleaned_data['test'],
                                name=param_name,
                                defaults={
                                    'unit': param_unit,
                                    'normal_range': param_range,
                                    'parameter_type': 'quantitative' if param_unit else 'qualitative'
                                }
                            )
                            
                            # Create test result parameter
                            TestResultParameter.objects.create(
                                test_result=test_result,
                                parameter=test_parameter,
                                value=param_value,
                                is_normal=(param_status == 'normal'),
                                notes=param_notes
                            )
                            parameter_count += 1
                
                # Add result text and interpretation as notes
                result_content = []
                if form.cleaned_data.get('result_text'):
                    result_content.append(f"RESULTS:\n{form.cleaned_data['result_text']}")
                
                if form.cleaned_data.get('interpretation'):
                    result_content.append(f"INTERPRETATION:\n{form.cleaned_data['interpretation']}")
                
                if result_content:
                    if test_result.notes:
                        test_result.notes += f"\n\n{chr(10).join(result_content)}"
                    else:
                        test_result.notes = chr(10).join(result_content)
                    test_result.save()
                
                # Handle submission action
                action = request.POST.get('action', 'save_draft')
                
                if action == 'submit_result':
                    # Mark as completed and update test request status
                    test_result.verified_by = request.user
                    test_result.save()
                    
                    # Check if all tests in the request have results
                    total_tests = test_request.tests.count()
                    completed_tests = TestResult.objects.filter(test_request=test_request).count()
                    
                    if completed_tests >= total_tests:
                        test_request.status = 'completed'
                        test_request.save()
                    
                    messages.success(
                        request,
                        f'Result submitted successfully for {form.cleaned_data["test"].name}. '
                        f'{parameter_count} parameters recorded.'
                    )
                else:
                    messages.success(
                        request,
                        f'Result draft saved for {form.cleaned_data["test"].name}. '
                        f'{parameter_count} parameters recorded.'
                    )
                
                # Return JSON response for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Result processed successfully',
                        'result_id': test_result.id,
                        'parameter_count': parameter_count
                    })
                
                return redirect('laboratory:test_request_detail', test_request.id)
                
        except Exception as e:
            messages.error(request, f'Error processing result: {str(e)}')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                })
    else:
        # Form has errors
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
    
    # Re-render form with errors
    previous_results = TestResult.objects.filter(
        test_request__patient=test_request.patient
    ).exclude(test_request=test_request).order_by('-result_date')[:5]
    
    context = {
        'test_request': test_request,
        'form': form,
        'lab_staff': lab_staff,
        'previous_results': previous_results,
        'title': f'Manual Result Entry - {test_request.patient.get_full_name()}'
    }
    
    return render(request, 'laboratory/manual_result_entry.html', context)


@login_required
def get_test_parameters(request, test_id):
    """
    AJAX endpoint to get predefined parameters for a test
    """
    test = get_object_or_404(Test, id=test_id)
    parameters = test.parameters.all()
    
    parameter_data = []
    for param in parameters:
        parameter_data.append({
            'id': param.id,
            'name': param.name,
            'unit': param.unit or '',
            'normal_range': param.normal_range or '',
            'parameter_type': param.parameter_type
        })
    
    return JsonResponse({
        'parameters': parameter_data,
        'test_info': {
            'name': test.name,
            'category': test.category.name if test.category else '',
            'sample_type': test.sample_type or '',
            'normal_range': test.normal_range or '',
            'preparation_instructions': test.preparation_instructions or ''
        }
    })


@login_required
def get_test_info(request, test_id):
    """
    AJAX endpoint to get test information
    """
    test = get_object_or_404(Test, id=test_id)
    
    return JsonResponse({
        'test': {
            'id': test.id,
            'name': test.name,
            'category': test.category.name if test.category else '',
            'sample_type': test.sample_type or '',
            'normal_range': test.normal_range or '',
            'preparation_instructions': test.preparation_instructions or '',
            'price': float(test.price)
        }
    })


@login_required
def bulk_manual_result_entry(request):
    """
    Bulk manual result entry for multiple tests
    """
    if request.method == 'POST':
        test_request_ids = request.POST.getlist('test_request_ids')
        test_requests = TestRequest.objects.filter(id__in=test_request_ids)
        
        # Process bulk results
        results_created = 0
        
        try:
            with transaction.atomic():
                for test_request in test_requests:
                    # Create basic results for all tests in each request
                    for test in test_request.tests.all():
                        if not TestResult.objects.filter(test_request=test_request, test=test).exists():
                            TestResult.objects.create(
                                test_request=test_request,
                                test=test,
                                result_date=timezone.now().date(),
                                notes='Bulk entry - pending detailed results',
                                performed_by=request.user
                            )
                            results_created += 1
                
                messages.success(
                    request,
                    f'Bulk result entry completed. {results_created} result placeholders created.'
                )
                
        except Exception as e:
            messages.error(request, f'Error in bulk result entry: {str(e)}')
    
    # Get pending test requests
    pending_requests = TestRequest.objects.filter(
        status__in=['pending', 'in_progress']
    ).order_by('-request_date')
    
    context = {
        'pending_requests': pending_requests,
        'title': 'Bulk Manual Result Entry'
    }
    
    return render(request, 'laboratory/bulk_manual_result_entry.html', context)


@login_required
def result_templates(request):
    """
    Manage result templates for quick entry
    """
    # This would handle result template management
    # For now, return a simple response
    return JsonResponse({
        'templates': [
            {
                'name': 'Normal CBC',
                'content': 'Complete Blood Count within normal limits.',
                'parameters': [
                    {'name': 'Hemoglobin', 'normal_range': '12-16 g/dL'},
                    {'name': 'WBC Count', 'normal_range': '4000-11000 /μL'},
                    {'name': 'Platelet Count', 'normal_range': '150000-450000 /μL'}
                ]
            }
        ]
    })
