from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import SharedWallet, WalletMembership, PatientWallet, Patient
from .forms import SharedWalletForm, WalletMembershipForm, AddFundsToSharedWalletForm, TransferBetweenWalletsForm
from accounts.permissions import permission_required
from decimal import Decimal


@login_required
@permission_required('patients.manage_shared_wallets')
def shared_wallet_list(request):
    """List all shared wallets"""
    wallets = SharedWallet.objects.all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        wallets = wallets.filter(
            Q(wallet_name__icontains=search_query) |
            Q(retainership_registration__icontains=search_query) |
            Q(wallet_type__icontains=search_query)
        )
    
    # Filter by type
    wallet_type = request.GET.get('type', '')
    if wallet_type:
        wallets = wallets.filter(wallet_type=wallet_type)
    
    # Pagination
    paginator = Paginator(wallets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'wallet_type': wallet_type,
        'title': 'Shared Wallets'
    }
    return render(request, 'patients/shared_wallet_list.html', context)


@login_required
@permission_required('patients.manage_shared_wallets')
def create_shared_wallet(request):
    """Create a new shared wallet"""
    if request.method == 'POST':
        form = SharedWalletForm(request.POST)
        if form.is_valid():
            wallet = form.save()
            messages.success(request, f'Shared wallet "{wallet.wallet_name}" created successfully.')
            return redirect('patients:shared_wallet_detail', wallet_id=wallet.id)
    else:
        form = SharedWalletForm()
    
    context = {
        'form': form,
        'title': 'Create Shared Wallet'
    }
    return render(request, 'patients/shared_wallet_form.html', context)


@login_required
@permission_required('patients.manage_shared_wallets')
def shared_wallet_detail(request, wallet_id):
    """View details of a shared wallet"""
    wallet = get_object_or_404(SharedWallet, id=wallet_id)
    
    # Get active members
    active_members = wallet.get_members()
    
    # Get transaction history
    transactions = wallet.get_transaction_history(limit=20)
    
    # Get statistics
    total_credits = transactions.filter(
        transaction_type__in=['credit', 'deposit', 'refund', 'transfer_in']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_debits = transactions.filter(
        transaction_type__in=['debit', 'payment', 'withdrawal', 'transfer_out']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'wallet': wallet,
        'active_members': active_members,
        'transactions': transactions,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'title': f'Shared Wallet: {wallet.wallet_name}'
    }
    return render(request, 'patients/shared_wallet_detail.html', context)


@login_required
@permission_required('patients.manage_shared_wallets')
def add_member_to_wallet(request, wallet_id):
    """Add a patient to a shared wallet"""
    wallet = get_object_or_404(SharedWallet, id=wallet_id)
    
    if request.method == 'POST':
        form = WalletMembershipForm(request.POST, wallet=wallet)
        if form.is_valid():
            membership = form.save(commit=False)
            membership.wallet = wallet
            membership.save()
            
            # Link patient's wallet to shared wallet
            patient = membership.patient
            patient_wallet, created = PatientWallet.objects.get_or_create(
                patient=patient,
                defaults={'balance': Decimal('0.00')}
            )
            patient_wallet.shared_wallet = wallet
            patient_wallet.save()
            
            messages.success(request, f'Patient {patient.get_full_name()} added to wallet successfully.')
            return redirect('patients:shared_wallet_detail', wallet_id=wallet.id)
    else:
        form = WalletMembershipForm(wallet=wallet)
    
    context = {
        'form': form,
        'wallet': wallet,
        'title': f'Add Member to {wallet.wallet_name}'
    }
    return render(request, 'patients/wallet_membership_form.html', context)


@login_required
@permission_required('patients.manage_shared_wallets')
def remove_member_from_wallet(request, wallet_id, membership_id):
    """Remove a patient from a shared wallet"""
    membership = get_object_or_404(WalletMembership, id=membership_id, wallet_id=wallet_id)
    
    if request.method == 'POST':
        patient = membership.patient
        wallet = membership.wallet
        
        # Unlink patient's wallet from shared wallet
        try:
            patient_wallet = PatientWallet.objects.get(patient=patient)
            patient_wallet.shared_wallet = None
            patient_wallet.save()
        except PatientWallet.DoesNotExist:
            pass
        
        # Remove membership
        membership.delete()
        
        messages.success(request, f'Patient {patient.get_full_name()} removed from wallet successfully.')
        return redirect('patients:shared_wallet_detail', wallet_id=wallet.id)
    
    context = {
        'membership': membership,
        'wallet': membership.wallet,
        'title': 'Remove Member from Wallet'
    }
    return render(request, 'patients/remove_wallet_member_confirm.html', context)


@login_required
@permission_required('patients.manage_shared_wallets')
def add_funds_to_shared_wallet(request, wallet_id):
    """Add funds to a shared wallet"""
    wallet = get_object_or_404(SharedWallet, id=wallet_id)
    
    if request.method == 'POST':
        form = AddFundsToSharedWalletForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description'] or f"Funds added via {form.cleaned_data['payment_method']}"
            
            # Credit the shared wallet
            wallet._credit(
                amount=amount,
                description=description,
                transaction_type='deposit',
                user=request.user
            )
            
            messages.success(request, f'₦{amount} added to {wallet.wallet_name} successfully.')
            return redirect('patients:shared_wallet_detail', wallet_id=wallet.id)
    else:
        form = AddFundsToSharedWalletForm()
    
    context = {
        'form': form,
        'wallet': wallet,
        'title': f'Add Funds to {wallet.wallet_name}'
    }
    return render(request, 'patients/add_funds_shared_wallet.html', context)


@login_required
@permission_required('patients.manage_shared_wallets')
def transfer_between_wallets(request, wallet_id):
    """Transfer funds between shared wallets"""
    source_wallet = get_object_or_404(SharedWallet, id=wallet_id)
    
    if request.method == 'POST':
        form = TransferBetweenWalletsForm(request.POST, source_wallet=source_wallet)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description'] or "Wallet transfer"
            recipient_wallet = form.cleaned_data['recipient_wallet']
            
            if source_wallet.balance < amount:
                messages.error(request, 'Insufficient funds in source wallet.')
            else:
                # Debit source wallet
                source_wallet._debit(
                    amount=amount,
                    description=f"Transfer to {recipient_wallet.wallet_name} - {description}",
                    transaction_type='transfer_out',
                    user=request.user
                )
                
                # Credit recipient wallet
                recipient_wallet._credit(
                    amount=amount,
                    description=f"Transfer from {source_wallet.wallet_name} - {description}",
                    transaction_type='transfer_in',
                    user=request.user
                )
                
                messages.success(request, f'₦{amount} transferred from {source_wallet.wallet_name} to {recipient_wallet.wallet_name} successfully.')
                return redirect('patients:shared_wallet_detail', wallet_id=source_wallet.id)
    else:
        form = TransferBetweenWalletsForm(source_wallet=source_wallet)
    
    context = {
        'form': form,
        'wallet': source_wallet,
        'title': f'Transfer Funds from {source_wallet.wallet_name}'
    }
    return render(request, 'patients/transfer_between_wallets.html', context)


@login_required
@permission_required('patients.manage_shared_wallets')
def retainership_wallet_list(request):
    """List all retainership wallets"""
    wallets = SharedWallet.objects.filter(wallet_type='retainership').order_by('-created_at')
    
    context = {
        'wallets': wallets,
        'title': 'Retainership Wallets'
    }
    return render(request, 'patients/retainership_wallet_list.html', context)
