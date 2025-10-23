from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F, Count
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.db import transaction
from django.db import models
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .models import (
    InterDispensaryTransfer, Medication, Dispensary, 
    MedicationInventory, DispensaryTransfer, MedicationTransfer
)
from .enhanced_transfer_forms import (
    EnhancedMedicationTransferForm,
    BulkMedicationTransferForm,
    MedicationTransferItemFormSet,
    TransferSearchForm,
    TransferApprovalForm,
    TransferRejectionForm
)


@login_required
def enhanced_transfer_dashboard(request):
    """Main dashboard for medication transfers"""
    
    # Get pending transfers
    pending_transfers = InterDispensaryTransfer.objects.filter(
        status='pending'
    ).select_related(
        'medication', 'from_dispensary', 'to_dispensary', 'requested_by'
    ).order_by('-created_at')
    
    # Get recent transfers
    recent_transfers = InterDispensaryTransfer.objects.filter(
        status__in=['completed', 'in_transit']
    ).select_related(
        'medication', 'from_dispensary', 'to_dispensary', 'transferred_by'
    ).order_by('-transferred_at')[:10]
    
    # Get dispensary inventory status
    dispensary_inventory = MedicationInventory.objects.select_related(
        'medication', 'dispensary'
    ).filter(
        stock_quantity__lte=F('reorder_level')
    ).order_by('dispensary', 'medication')
    
    # Get bulk transfer status
    pending_bulk_transfers = MedicationTransfer.objects.filter(
        status='pending'
    ).select_related(
        'medication', 'from_bulk_store', 'to_active_store', 'requested_by'
    ).order_by('-created_at')
    
    context = {
        'pending_transfers': pending_transfers,
        'recent_transfers': recent_transfers,
        'dispensary_inventory': dispensary_inventory,
        'pending_bulk_transfers': pending_bulk_transfers,
        'title': 'Medication Transfer Dashboard'
    }
    
    return render(request, 'pharmacy/enhanced_transfer_dashboard.html', context)


@login_required
def create_single_transfer(request):
    """View for creating a single medication transfer"""
    
    if request.method == 'POST':
        form = EnhancedMedicationTransferForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    transfer = InterDispensaryTransfer.create_transfer(
                        medication=form.cleaned_data['medication'],
                        from_dispensary=form.cleaned_data['from_dispensary'],
                        to_dispensary=form.cleaned_data['to_dispensary'],
                        quantity=form.cleaned_data['quantity'],
                        requested_by=request.user,
                        notes=form.cleaned_data.get('notes', '')
                    )
                
                messages.success(
                    request, 
                    f'Transfer #{transfer.id} created successfully. '
                    'It is now pending approval.'
                )
                return redirect('pharmacy:enhanced_transfer_list')
                
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = EnhancedMedicationTransferForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Create Single Transfer',
        'is_single': True
    }
    
    return render(request, 'pharmacy/enhanced_create_transfer.html', context)


@login_required
def create_bulk_transfer(request):
    """View for creating bulk medication transfers"""
    
    if request.method == 'POST':
        form = BulkMedicationTransferForm(request.POST, user=request.user)
        formset = MedicationTransferItemFormSet(request.POST, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    from_dispensary = form.cleaned_data['from_dispensary']
                    to_dispensary = form.cleaned_data['to_dispensary']
                    bulk_notes = form.cleaned_data.get('notes', '')
                    
                    transfers_created = []
                    
                    for item_form in formset:
                        if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE'):
                            medication = item_form.cleaned_data['medication']
                            quantity = item_form.cleaned_data['quantity']
                            
                            # Create individual transfer
                            transfer = InterDispensaryTransfer.create_transfer(
                                medication=medication,
                                from_dispensary=from_dispensary,
                                to_dispensary=to_dispensary,
                                quantity=quantity,
                                requested_by=request.user,
                                notes=f"{bulk_notes} (Part of bulk transfer)"
                            )
                            transfers_created.append(transfer)
                
                messages.success(
                    request, 
                    f'Created {len(transfers_created)} transfers successfully. '
                    'They are now pending approval.'
                )
                return redirect('pharmacy:enhanced_transfer_list')
                
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = BulkMedicationTransferForm(user=request.user)
        formset = MedicationTransferItemFormSet(prefix='items')
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create Bulk Transfer',
        'is_bulk': True
    }
    
    return render(request, 'pharmacy/enhanced_create_transfer.html', context)


@login_required
def enhanced_transfer_list(request):
    """Enhanced view for listing transfers with advanced filtering"""
    
    form = TransferSearchForm(request.GET)
    transfers = InterDispensaryTransfer.objects.all()
    
    # Apply filters
    if form.is_valid():
        cleaned_data = form.cleaned_data
        
        if cleaned_data.get('search_term'):
            search_term = cleaned_data['search_term']
            transfers = transfers.filter(
                Q(medication__name__icontains=search_term) |
                Q(id__icontains=search_term) |
                Q(notes__icontains=search_term)
            )
        
        if cleaned_data.get('from_dispensary'):
            transfers = transfers.filter(from_dispensary=cleaned_data['from_dispensary'])
        
        if cleaned_data.get('to_dispensary'):
            transfers = transfers.filter(to_dispensary=cleaned_data['to_dispensary'])
        
        if cleaned_data.get('status'):
            transfers = transfers.filter(status=cleaned_data['status'])
        
        if cleaned_data.get('date_from'):
            transfers = transfers.filter(created_at__date__gte=cleaned_data['date_from'])
        
        if cleaned_data.get('date_to'):
            transfers = transfers.filter(created_at__date__lte=cleaned_data['date_to'])
    
    # Order by creation date
    transfers = transfers.select_related(
        'medication', 'from_dispensary', 'to_dispensary', 
        'requested_by', 'approved_by', 'transferred_by'
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transfers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    transfer_stats = {
        'pending': InterDispensaryTransfer.objects.filter(status='pending').count(),
        'approved': InterDispensaryTransfer.objects.filter(status='approved').count(),
        'in_transit': InterDispensaryTransfer.objects.filter(status='in_transit').count(),
        'completed': InterDispensaryTransfer.objects.filter(status='completed').count(),
        'cancelled': InterDispensaryTransfer.objects.filter(status='cancelled').count(),
        'rejected': InterDispensaryTransfer.objects.filter(status='rejected').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'transfer_stats': transfer_stats,
        'title': 'Medication Transfers'
    }
    
    return render(request, 'pharmacy/enhanced_transfer_list.html', context)


@login_required
def enhanced_transfer_detail(request, transfer_id):
    """Enhanced view for transfer details with audit trail"""
    
    transfer = get_object_or_404(
        InterDispensaryTransfer.objects.select_related(
            'medication', 'from_dispensary', 'to_dispensary',
            'requested_by', 'approved_by', 'transferred_by'
        ),
        id=transfer_id
    )
    
    # Get related inventory information
    try:
        source_inventory = MedicationInventory.objects.get(
            medication=transfer.medication,
            dispensary=transfer.from_dispensary
        )
    except MedicationInventory.DoesNotExist:
        source_inventory = None
    
    try:
        dest_inventory = MedicationInventory.objects.get(
            medication=transfer.medication,
            dispensary=transfer.to_dispensary
        )
    except MedicationInventory.DoesNotExist:
        dest_inventory = None
    
    # Get related transfers (same medication, recent)
    related_transfers = InterDispensaryTransfer.objects.filter(
        medication=transfer.medication,
        created_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).exclude(id=transfer.id).select_related(
        'from_dispensary', 'to_dispensary', 'transferred_by'
    ).order_by('-created_at')[:5]
    
    context = {
        'transfer': transfer,
        'source_inventory': source_inventory,
        'dest_inventory': dest_inventory,
        'related_transfers': related_transfers,
        'title': f'Transfer Details - #{transfer.id}'
    }
    
    return render(request, 'pharmacy/enhanced_transfer_detail.html', context)


@login_required
@require_POST
def approve_transfer(request, transfer_id):
    """Approve a transfer"""
    
    transfer = get_object_or_404(InterDispensaryTransfer, id=transfer_id)
    form = TransferApprovalForm(request.POST)
    
    if form.is_valid():
        try:
            with transaction.atomic():
                transfer.approve_transfer(request.user)
                if form.cleaned_data.get('approval_notes'):
                    transfer.notes = f"{transfer.notes}\n\nApproval Notes: {form.cleaned_data['approval_notes']}"
                    transfer.save()
            
            messages.success(request, f'Transfer #{transfer.id} approved successfully.')
            
        except ValueError as e:
            messages.error(request, str(e))
    
    return redirect('pharmacy:enhanced_transfer_detail', transfer_id=transfer_id)


@login_required
@require_POST
def reject_transfer(request, transfer_id):
    """Reject a transfer"""
    
    transfer = get_object_or_404(InterDispensaryTransfer, id=transfer_id)
    form = TransferRejectionForm(request.POST)
    
    if form.is_valid():
        try:
            with transaction.atomic():
                transfer.reject_transfer(
                    request.user, 
                    form.cleaned_data['rejection_reason']
                )
            
            messages.success(request, f'Transfer #{transfer.id} rejected successfully.')
            
        except ValueError as e:
            messages.error(request, str(e))
    
    return redirect('pharmacy:enhanced_transfer_detail', transfer_id=transfer_id)


@login_required
@require_POST
def execute_transfer(request, transfer_id):
    """Execute an approved transfer"""
    
    transfer = get_object_or_404(InterDispensaryTransfer, id=transfer_id)
    
    try:
        with transaction.atomic():
            transfer.execute_transfer(request.user)
        
        messages.success(request, f'Transfer #{transfer.id} executed successfully.')
        
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect('pharmacy:enhanced_transfer_detail', transfer_id=transfer_id)


@login_required
@csrf_exempt
@require_POST
def approve_bulk_transfers(request):
    """Approve multiple transfers at once"""
    
    transfer_ids = request.POST.getlist('transfer_ids')
    
    if not transfer_ids:
        return JsonResponse({'error': 'No transfers selected'}, status=400)
    
    approved_count = 0
    errors = []
    
    with transaction.atomic():
        for transfer_id in transfer_ids:
            try:
                transfer = InterDispensaryTransfer.objects.get(id=transfer_id)
                transfer.approve_transfer(request.user)
                approved_count += 1
            except Exception as e:
                errors.append(f"Transfer #{transfer_id}: {str(e)}")
    
    if errors:
        return JsonResponse({
            'approved_count': approved_count,
            'errors': errors
        }, status=400)
    
    return JsonResponse({
        'message': f'Approved {approved_count} transfers successfully',
        'approved_count': approved_count
    })


@login_required
@csrf_exempt
def check_inventory_api(request):
    """API endpoint to check inventory availability"""
    
    medication_id = request.GET.get('medication_id')
    dispensary_id = request.GET.get('dispensary_id')
    quantity = request.GET.get('quantity', 0)
    
    if not medication_id or not dispensary_id:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    
    try:
        medication = Medication.objects.get(id=medication_id)
        dispensary = Dispensary.objects.get(id=dispensary_id)
        
        inventory, created = MedicationInventory.objects.get_or_create(
            medication=medication,
            dispensary=dispensary,
            defaults={'stock_quantity': 0, 'reorder_level': 10}
        )
        
        available = inventory.stock_quantity
        required = int(quantity)
        feasible = available >= required
        
        return JsonResponse({
            'available': available,
            'required': required,
            'feasible': feasible,
            'message': f'Available: {available}, Required: {required} - {"✓ Feasible" if feasible else "✗ Insufficient stock"}'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@csrf_exempt
def get_medication_inventory_ajax(request):
    """AJAX endpoint to get medication inventory for a specific dispensary"""
    
    dispensary_id = request.GET.get('dispensary_id')
    medication_id = request.GET.get('medication_id')
    
    if not dispensary_id or not medication_id:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    
    try:
        inventory = MedicationInventory.objects.select_related('medication').get(
            medication_id=medication_id,
            dispensary_id=dispensary_id
        )
        
        return JsonResponse({
            'stock_quantity': inventory.stock_quantity,
            'reorder_level': inventory.reorder_level,
            'medication_name': inventory.medication.name,
            'available': inventory.stock_quantity
        })
        
    except MedicationInventory.DoesNotExist:
        return JsonResponse({
            'stock_quantity': 0,
            'reorder_level': 0,
            'medication_name': 'Unknown',
            'available': 0
        })


@login_required
def transfer_reports(request):
    """Generate transfer reports and statistics"""
    
    # Get date range from request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    transfers = InterDispensaryTransfer.objects.all()
    
    if date_from:
        transfers = transfers.filter(created_at__date__gte=date_from)
    if date_to:
        transfers = transfers.filter(created_at__date__lte=date_to)
    
    # Calculate statistics
    stats = {
        'total_transfers': transfers.count(),
        'pending_transfers': transfers.filter(status='pending').count(),
        'approved_transfers': transfers.filter(status='approved').count(),
        'completed_transfers': transfers.filter(status='completed').count(),
        'rejected_transfers': transfers.filter(status='rejected').count(),
    }
    
    # Get transfers by medication
    transfers_by_medication = transfers.values(
        'medication__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        transfer_count=models.Count('id')
    ).order_by('-total_quantity')[:10]
    
    # Get transfers by dispensary
    transfers_by_dispensary = transfers.values(
        'from_dispensary__name',
        'to_dispensary__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        transfer_count=models.Count('id')
    ).order_by('-transfer_count')[:10]
    
    context = {
        'stats': stats,
        'transfers_by_medication': transfers_by_medication,
        'transfers_by_dispensary': transfers_by_dispensary,
        'date_from': date_from,
        'date_to': date_to,
        'title': 'Transfer Reports'
    }
    
    return render(request, 'pharmacy/transfer_reports.html', context)
