from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse_lazy

from .models import InterDispensaryTransfer, MedicationInventory, Dispensary
from .inter_dispensary_forms import (
    InterDispensaryTransferForm,
    InterDispensaryTransferSearchForm,
    InterDispensaryTransferApprovalForm,
    InterDispensaryTransferRejectForm
)


@login_required
def inter_dispensary_transfer_list(request):
    """View for listing inter-dispensary transfers"""
    form = InterDispensaryTransferSearchForm(request.GET)
    transfers = InterDispensaryTransfer.objects.all()
    
    # Apply filters
    if form.is_valid():
        cleaned_data = form.cleaned_data
        
        if cleaned_data.get('from_dispensary'):
            transfers = transfers.filter(from_dispensary=cleaned_data['from_dispensary'])
        
        if cleaned_data.get('to_dispensary'):
            transfers = transfers.filter(to_dispensary=cleaned_data['to_dispensary'])
        
        if cleaned_data.get('medication'):
            transfers = transfers.filter(medication=cleaned_data['medication'])
        
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
    paginator = Paginator(transfers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'title': 'Inter-Dispensary Transfers'
    }
    
    return render(request, 'pharmacy/inter_dispensary_transfer_list.html', context)


@login_required
def inter_dispensary_transfer_detail(request, transfer_id):
    """View for transfer details"""
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
    
    context = {
        'transfer': transfer,
        'source_inventory': source_inventory,
        'dest_inventory': dest_inventory,
        'title': f'Transfer Details - #{transfer.id}'
    }
    
    return render(request, 'pharmacy/inter_dispensary_transfer_detail.html', context)


@login_required
def create_inter_dispensary_transfer(request):
    """View for creating a new inter-dispensary transfer"""
    if request.method == 'POST':
        form = InterDispensaryTransferForm(request.POST, user=request.user)
        if form.is_valid():
            try:
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
                    f'Inter-dispensary transfer #{transfer.id} created successfully. '
                    'It is now pending approval.'
                )
                return redirect('pharmacy:inter_dispensary_transfer_detail', transfer_id=transfer.id)
                
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = InterDispensaryTransferForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Create Inter-Dispensary Transfer',
        'submit_text': 'Create Transfer'
    }
    
    return render(request, 'pharmacy/create_inter_dispensary_transfer.html', context)


@login_required
def approve_inter_dispensary_transfer(request, transfer_id):
    """View for approving an inter-dispensary transfer"""
    transfer = get_object_or_404(InterDispensaryTransfer, id=transfer_id)
    
    if request.method == 'POST':
        form = InterDispensaryTransferApprovalForm(request.POST, instance=transfer)
        if form.is_valid():
            try:
                transfer.approve_transfer(request.user)
                messages.success(request, f'Transfer #{transfer.id} approved successfully.')
                return redirect('pharmacy:inter_dispensary_transfer_detail', transfer_id=transfer.id)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = InterDispensaryTransferApprovalForm(instance=transfer)
    
    # Get availability check
    can_transfer, message = transfer.check_availability()
    
    context = {
        'transfer': transfer,
        'form': form,
        'title': f'Approve Transfer #{transfer.id}',
        'can_transfer': can_transfer,
        'availability_message': message
    }
    
    return render(request, 'pharmacy/approve_inter_dispensary_transfer.html', context)


@login_required
def reject_inter_dispensary_transfer(request, transfer_id):
    """View for rejecting an inter-dispensary transfer"""
    transfer = get_object_or_404(InterDispensaryTransfer, id=transfer_id)
    
    if transfer.status != 'pending':
        messages.error(request, 'This transfer cannot be rejected.')
        return redirect('pharmacy:inter_dispensary_transfer_detail', transfer_id=transfer.id)
    
    if request.method == 'POST':
        form = InterDispensaryTransferRejectForm(request.POST)
        if form.is_valid():
            try:
                transfer.reject_transfer(
                    request.user, 
                    form.cleaned_data['rejection_reason']
                )
                messages.success(request, f'Transfer #{transfer.id} rejected successfully.')
                return redirect('pharmacy:inter_dispensary_transfer_detail', transfer_id=transfer.id)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = InterDispensaryTransferRejectForm()
    
    context = {
        'transfer': transfer,
        'form': form,
        'title': f'Reject Transfer #{transfer.id}'
    }
    
    return render(request, 'pharmacy/reject_inter_dispensary_transfer.html', context)


@login_required
def execute_inter_dispensary_transfer(request, transfer_id):
    """View for executing an approved inter-dispensary transfer"""
    transfer = get_object_or_404(InterDispensaryTransfer, id=transfer_id)
    
    if not transfer.can_execute():
        messages.error(request, 'This transfer cannot be executed in its current status.')
        return redirect('pharmacy:inter_dispensary_transfer_detail', transfer_id=transfer.id)
    
    if request.method == 'POST':
        try:
            transfer.execute_transfer(request.user)
            messages.success(request, f'Transfer #{transfer.id} executed successfully!')
            return redirect('pharmacy:inter_dispensary_transfer_detail', transfer_id=transfer.id)
        except ValueError as e:
            messages.error(request, str(e))
    
    # Get current availability
    can_transfer, message = transfer.check_availability()
    
    context = {
        'transfer': transfer,
        'can_transfer': can_transfer,
        'availability_message': message,
        'title': f'Execute Transfer #{transfer.id}'
    }
    
    return render(request, 'pharmacy/execute_inter_dispensary_transfer.html', context)


@login_required
def cancel_inter_dispensary_transfer(request, transfer_id):
    """View for cancelling a pending inter-dispensary transfer"""
    transfer = get_object_or_404(InterDispensaryTransfer, id=transfer_id)
    
    if transfer.status not in ['pending', 'in_transit']:
        messages.error(request, 'This transfer cannot be cancelled.')
        return redirect('pharmacy:inter_dispensary_transfer_detail', transfer_id=transfer.id)
    
    if transfer.status == 'in_transit' and transfer.approved_by:
        # Only the approver or admin can cancel approved transfers
        if transfer.approved_by != request.user and not request.user.is_superuser:
            messages.error(request, 'Only the approver can cancel approved transfers.')
            return redirect('pharmacy:inter_dispensary_transfer_detail', transfer_id=transfer.id)
    
    if request.method == 'POST':
        transfer.status = 'cancelled'
        transfer.save()
        messages.success(request, f'Transfer #{transfer.id} cancelled successfully.')
        return redirect('pharmacy:inter_dispensary_transfer_detail', transfer_id=transfer.id)
    
    context = {
        'transfer': transfer,
        'title': f'Cancel Transfer #{transfer.id}'
    }
    
    return render(request, 'pharmacy/cancel_inter_dispensary_transfer.html', context)


@login_required
def check_medication_inventory(request):
    """AJAX endpoint to check medication inventory availability"""
    medication_id = request.GET.get('medication_id')
    dispensary_id = request.GET.get('dispensary_id')
    quantity = request.GET.get('quantity', 0)
    
    if not medication_id or not dispensary_id:
        return JsonResponse({'error': 'Medication and dispensary required'}, status=400)
    
    try:
        medication = Medication.objects.get(id=medication_id)
        dispensary = Dispensary.objects.get(id=dispensary_id)
        quantity = int(quantity)
        
        try:
            inventory = MedicationInventory.objects.get(
                medication=medication,
                dispensary=dispensary
            )
            available = inventory.stock_quantity
            feasible = available >= quantity
            
            return JsonResponse({
                'available': available,
                'required': quantity,
                'feasible': feasible,
                'message': 'Sufficient stock available' if feasible else f'Insufficient stock. Available: {available}, Required: {quantity}'
            })
        except MedicationInventory.DoesNotExist:
            return JsonResponse({
                'available': 0,
                'required': quantity,
                'feasible': False,
                'message': f'No inventory found for {medication.name} in {dispensary.name}'
            })
            
    except (Medication.DoesNotExist, Dispensary.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid parameters'}, status=400)


@login_required
def transfer_statistics(request):
    """View for inter-dispensary transfer statistics"""
    today = timezone.now().date()
    
    # Get statistics
    total_transfers = InterDispensaryTransfer.objects.count()
    pending_transfers = InterDispensaryTransfer.objects.filter(status='pending').count()
    in_transit_transfers = InterDispensaryTransfer.objects.filter(status='in_transit').count()
    completed_transfers = InterDispensaryTransfer.objects.filter(status='completed').count()
    cancelled_transfers = InterDispensaryTransfer.objects.filter(status='cancelled').count()
    rejected_transfers = InterDispensaryTransfer.objects.filter(status='rejected').count()
    
    # Get today's transfers
    today_transfers = InterDispensaryTransfer.objects.filter(created_at__date=today).count()
    
    # Get recent transfers
    recent_transfers = InterDispensaryTransfer.objects.filter(
        created_at__gte=today - timezone.timedelta(days=7)
    ).select_related('medication', 'from_dispensary', 'to_dispensary')[:10]
    
    # Get outgoing transfers for user's dispensary
    user_dispensary = None
    outgoing_transfers = InterDispensaryTransfer.objects.none()
    
    if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'dispensary'):
        user_dispensary = request.user.profile.dispensary
        outgoing_transfers = InterDispensaryTransfer.objects.filter(
            from_dispensary=user_dispensary
        ).select_related('medication', 'to_dispensary', 'requested_by')[:5]
    
    context = {
        'title': 'Transfer Statistics',
        'total_transfers': total_transfers,
        'pending_transfers': pending_transfers,
        'in_transit_transfers': in_transit_transfers,
        'completed_transfers': completed_transfers,
        'cancelled_transfers': cancelled_transfers,
        'rejected_transfers': rejected_transfers,
        'today_transfers': today_transfers,
        'recent_transfers': recent_transfers,
        'user_dispensary': user_dispensary,
        'outgoing_transfers': outgoing_transfers
    }
    
    return render(request, 'pharmacy/transfer_statistics.html', context)


class TransferDetailView(LoginRequiredMixin, DetailView):
    """Generic detail view for inter-dispensary transfers"""
    model = InterDispensaryTransfer
    template_name = 'pharmacy/inter_dispensary_transfer_detail.html'
    context_object_name = 'transfer'
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'medication', 'from_dispensary', 'to_dispensary',
            'requested_by', 'approved_by', 'transferred_by'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transfer = self.get_object()
        
        # Get inventory information
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
        
        context.update({
            'source_inventory': source_inventory,
            'dest_inventory': dest_inventory,
            'title': f'Transfer Details - #{transfer.id}'
        })
        
        return context


class TransferListView(LoginRequiredMixin, ListView):
    """Generic list view for inter-dispensary transfers"""
    model = InterDispensaryTransfer
    template_name = 'pharmacy/inter_dispensary_transfer_list.html'
    context_object_name = 'page_obj'  # Use same name as function-based view
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'medication', 'from_dispensary', 'to_dispensary',
            'requested_by', 'approved_by', 'transferred_by'
        )
        
        # Apply filters
        form = InterDispensaryTransferSearchForm(self.request.GET)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            
            if cleaned_data.get('from_dispensary'):
                queryset = queryset.filter(from_dispensary=cleaned_data['from_dispensary'])
            
            if cleaned_data.get('to_dispensary'):
                queryset = queryset.filter(to_dispensary=cleaned_data['to_dispensary'])
            
            if cleaned_data.get('medication'):
                queryset = queryset.filter(medication=cleaned_data['medication'])
            
            if cleaned_data.get('status'):
                queryset = queryset.filter(status=cleaned_data['status'])
            
            if cleaned_data.get('date_from'):
                queryset = queryset.filter(created_at__date__gte=cleaned_data['date_from'])
            
            if cleaned_data.get('date_to'):
                queryset = queryset.filter(created_at__date__lte=cleaned_data['date_to'])
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = InterDispensaryTransferSearchForm(self.request.GET)
        context['title'] = 'Inter-Dispensary Transfers'
        return context
