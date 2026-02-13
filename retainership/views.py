from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.db import transaction
from decimal import Decimal

from accounts.constants import (
    ROLE_ADMIN,
    ROLE_ACCOUNTANT,
    ROLE_RECEPTIONIST,
    ROLE_HEALTH_RECORD_OFFICER,
)
from core.decorators import role_required
from patients.models import (
    Patient,
    SharedWallet,
    WalletMembership,
    PatientWallet,
    WalletTransaction,
)
from core.patient_search_forms import PatientSearchForm
from patients.forms import (
    RetainershipIndependentPatientForm,
)  # Import RetainershipIndependentPatientForm
from .models import RetainershipPatient
from .forms import (
    RetainershipPatientForm,
    RetainershipWalletLinkForm,
    AddMemberToWalletForm,
)


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def retainership_patient_list(request):
    retainership_patients = (
        RetainershipPatient.objects.select_related("patient")
        .all()
        .order_by("-date_registered")
    )

    # Add wallet information to each patient
    for retainership_patient in retainership_patients:
        patient = retainership_patient.patient
        membership = patient.wallet_memberships.filter(
            wallet__wallet_type="retainership"
        ).first()
        retainership_patient.wallet_info = membership.wallet if membership else None

    search_query = request.GET.get("search", "")
    if search_query:
        retainership_patients = retainership_patients.filter(
            Q(retainership_reg_number__icontains=search_query)
            | Q(patient__first_name__icontains=search_query)
            | Q(patient__last_name__icontains=search_query)
            | Q(patient__patient_id__icontains=search_query)
        )

    paginator = Paginator(
        retainership_patients, 10
    )  # Show 10 Retainership patients per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "title": "Retainership Patients",
    }
    return render(request, "retainership/retainership_patient_list.html", context)


from .forms import RetainershipPatientForm
from django.db.models import Sum


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def select_patient_for_retainership(request):
    search_form = PatientSearchForm(request.GET)
    # Only show patients who already have Retainership registration
    patients = (
        Patient.objects.filter(retainership_info__isnull=False)
        .select_related("retainership_info")
        .order_by("first_name")
    )

    if search_form.is_valid():
        search_query = search_form.cleaned_data.get("search")
        if search_query:
            patients = patients.filter(
                Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(patient_id__icontains=search_query)
                | Q(phone_number__icontains=search_query)
                | Q(retainership_info__retainership_reg_number__icontains=search_query)
            )

    # Add wallet info to each patient
    for patient in patients:
        membership = patient.wallet_memberships.filter(
            wallet__wallet_type="retainership"
        ).first()
        patient.has_retainership_wallet = membership is not None

    paginator = Paginator(patients, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "search_form": search_form,
        "page_obj": page_obj,
        "title": "Select Retainership Patient",
    }
    return render(request, "retainership/select_patient_for_retainership.html", context)


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def retainership_wallet_list(request):
    """List all retainership wallets with management capabilities"""
    # Get all retainership wallets
    wallets = SharedWallet.objects.filter(wallet_type="retainership").order_by(
        "-created_at"
    )

    # Search functionality - apply BEFORE pagination and annotation
    search_query = request.GET.get("search", "")
    if search_query:
        wallets = wallets.filter(
            Q(wallet_name__icontains=search_query)
            | Q(retainership_registration__icontains=search_query)
            | Q(members__patient__first_name__icontains=search_query)
            | Q(members__patient__last_name__icontains=search_query)
        ).distinct()

    # Pagination
    paginator = Paginator(wallets, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Add aggregated information to each wallet in the current page
    for wallet in page_obj:
        # Count members
        wallet.member_count = wallet.members.count()

        # Get total credits and debits
        wallet.total_credits = (
            WalletTransaction.objects.filter(
                shared_wallet=wallet,
                transaction_type__in=["credit", "deposit", "transfer_in"],
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        wallet.total_debits = (
            WalletTransaction.objects.filter(
                shared_wallet=wallet,
                transaction_type__in=["debit", "withdrawal", "transfer_out"],
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

    # Calculate totals for dashboard (on the filtered queryset, not just page)
    total_wallets = wallets.count()
    total_balance = wallets.aggregate(total=Sum("balance"))["total"] or 0
    total_members = sum(w.members.count() for w in wallets)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "title": "Retainership Wallets Management",
        "total_wallets": total_wallets,
        "total_balance": total_balance,
        "total_members": total_members,
    }

    # Check if this is an HTMX request
    if request.headers.get("HX-Request"):
        return render(request, "retainership/partials/wallet_table_rows.html", context)

    return render(request, "retainership/retainership_wallet_list.html", context)


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def view_wallet_details(request, wallet_id):
    """View detailed information about a specific retainership wallet"""
    wallet = get_object_or_404(SharedWallet, id=wallet_id, wallet_type="retainership")

    # Get all members of this wallet
    members = wallet.members.select_related("patient").all()

    # Get transaction history with pagination
    transactions = WalletTransaction.objects.filter(shared_wallet=wallet).order_by(
        "-created_at"
    )

    # Filter by transaction type if specified
    transaction_type = request.GET.get("type")
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)

    # Pagination for transactions
    paginator = Paginator(transactions, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calculate statistics
    total_credits = (
        WalletTransaction.objects.filter(
            shared_wallet=wallet,
            transaction_type__in=["credit", "deposit", "transfer_in"],
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    total_debits = (
        WalletTransaction.objects.filter(
            shared_wallet=wallet,
            transaction_type__in=["debit", "withdrawal", "transfer_out"],
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    context = {
        "wallet": wallet,
        "members": members,
        "page_obj": page_obj,
        "total_credits": total_credits,
        "total_debits": total_debits,
        "title": f"Retainership Wallet Details - {wallet.wallet_name}",
    }
    return render(request, "retainership/wallet_details.html", context)


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def manage_wallet_by_id(request, wallet_id):
    """Manage a retainership wallet by wallet ID (not patient ID)"""
    wallet = get_object_or_404(SharedWallet, id=wallet_id, wallet_type="retainership")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "credit":
            try:
                amount = Decimal(request.POST.get("amount", 0))
                description = request.POST.get("description", "Manual credit")

                if amount > 0:
                    wallet._credit(
                        amount=amount,
                        description=description,
                        transaction_type="credit",
                        user=request.user,
                        patient=None,  # Wallet-level credit, not patient-specific
                    )
                    messages.success(
                        request, f"Successfully credited ₦{amount} to wallet"
                    )
                else:
                    messages.error(request, "Amount must be positive")

            except Exception as e:
                messages.error(request, f"Error crediting wallet: {str(e)}")

        elif action == "debit":
            try:
                amount = Decimal(request.POST.get("amount", 0))
                description = request.POST.get("description", "Manual debit")

                if amount > 0:
                    wallet._debit(
                        amount=amount,
                        description=description,
                        transaction_type="debit",
                        user=request.user,
                        patient=None,  # Wallet-level debit, not patient-specific
                    )
                    messages.success(
                        request, f"Successfully debited ₦{amount} from wallet"
                    )
                else:
                    messages.error(request, "Amount must be positive")

            except Exception as e:
                messages.error(request, f"Error debiting wallet: {str(e)}")

        elif action == "transfer":
            try:
                amount = Decimal(request.POST.get("amount", 0))
                recipient_wallet_id = request.POST.get("recipient_wallet_id")
                description = request.POST.get("description", "Wallet transfer")

                if amount > 0 and recipient_wallet_id:
                    try:
                        recipient_wallet = SharedWallet.objects.get(
                            id=recipient_wallet_id, is_active=True
                        )

                        # Perform the transfer
                        sender_transaction, recipient_transaction = wallet.transfer_to(
                            recipient_wallet=recipient_wallet,
                            amount=amount,
                            description=description,
                            user=request.user,
                            patient=None,  # Wallet-level transfer
                        )

                        messages.success(
                            request,
                            f"Successfully transferred ₦{amount} to {recipient_wallet.wallet_name}",
                        )
                    except SharedWallet.DoesNotExist:
                        messages.error(
                            request, "Recipient wallet not found or is inactive"
                        )
                else:
                    messages.error(
                        request,
                        "Amount must be positive and recipient wallet must be selected",
                    )

            except Exception as e:
                messages.error(request, f"Error transferring funds: {str(e)}")

        elif action == "toggle_status":
            try:
                wallet.is_active = not wallet.is_active
                wallet.save()
                status_text = "activated" if wallet.is_active else "deactivated"
                messages.success(request, f"Wallet has been {status_text}")
            except Exception as e:
                messages.error(request, f"Error toggling wallet status: {str(e)}")

        return redirect("retainership:manage_wallet_by_id", wallet_id=wallet_id)

    # Get transaction history
    transactions = WalletTransaction.objects.filter(shared_wallet=wallet).order_by(
        "-created_at"
    )[:20]

    # Get available wallets for transfer (exclude current wallet)
    available_wallets = SharedWallet.objects.exclude(id=wallet.id).filter(
        is_active=True
    )

    # Get members
    members = wallet.members.select_related("patient").all()

    context = {
        "wallet": wallet,
        "transactions": transactions,
        "available_wallets": available_wallets,
        "members": members,
        "title": f"Manage Retainership Wallet - {wallet.wallet_name}",
    }
    return render(request, "retainership/manage_wallet_by_id.html", context)


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def register_patient_for_retainership(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    # Get existing retainership info or None if it doesn't exist
    retainership_info = None
    try:
        retainership_info = patient.retainership_info
    except RetainershipPatient.DoesNotExist:
        pass

    if request.method == "POST":
        form = RetainershipPatientForm(request.POST, instance=retainership_info)
        if form.is_valid():
            retainership_patient = form.save(commit=False)
            retainership_patient.patient = patient
            retainership_patient.save()
            messages.success(
                request,
                f"Patient {patient.get_full_name()} registered for retainership successfully.",
            )
            return redirect("retainership:retainership_patient_list")
    else:
        form = RetainershipPatientForm(instance=retainership_info)

    context = {
        "form": form,
        "patient": patient,
        "title": f"Register {patient.get_full_name()} for Retainership",
    }
    return render(
        request, "retainership/register_patient_for_retainership.html", context
    )


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def register_independent_retainership_patient(request):
    if request.method == "POST":
        form = RetainershipIndependentPatientForm(request.POST, request.FILES)
        if form.is_valid():
            patient = form.save()

            # Check if user wants to add to existing wallet
            add_to_existing_wallet = request.POST.get("add_to_existing_wallet") == "on"
            selected_wallet_id = request.POST.get("existing_wallet")
            make_primary = request.POST.get("make_primary_member") == "on"

            if add_to_existing_wallet and selected_wallet_id:
                try:
                    wallet = SharedWallet.objects.get(
                        id=selected_wallet_id,
                        wallet_type="retainership",
                        is_active=True,
                    )

                    with transaction.atomic():
                        # Check if this wallet already has a primary member
                        if make_primary:
                            existing_primary = wallet.members.filter(
                                is_primary=True
                            ).first()
                            if existing_primary:
                                messages.warning(
                                    request,
                                    f"Wallet already has primary member: {existing_primary.patient.get_full_name()}. Adding as regular member.",
                                )
                                make_primary = False

                        # Create wallet membership
                        WalletMembership.objects.create(
                            wallet=wallet, patient=patient, is_primary=make_primary
                        )

                        # Link patient wallet to shared wallet
                        patient_wallet, created = PatientWallet.objects.get_or_create(
                            patient=patient, defaults={"balance": Decimal("0.00")}
                        )
                        patient_wallet.shared_wallet = wallet
                        patient_wallet.save()

                        messages.success(
                            request,
                            f"Patient {patient.get_full_name()} added to wallet: {wallet.wallet_name}",
                        )

                except SharedWallet.DoesNotExist:
                    messages.warning(
                        request,
                        "Selected wallet not found or inactive. Patient registered but not linked to wallet.",
                    )

            messages.success(
                request,
                f"Independent Retainership Patient {patient.get_full_name()} registered successfully.",
            )
            return redirect("patients:detail", patient_id=patient.id)
    else:
        form = RetainershipIndependentPatientForm()

    # Get existing retainership wallets for dropdown
    existing_wallets = SharedWallet.objects.filter(
        wallet_type="retainership", is_active=True
    ).order_by("wallet_name")

    context = {
        "form": form,
        "title": "Register Independent Retainership Patient",
        "existing_wallets": existing_wallets,
    }
    return render(
        request, "retainership/register_independent_retainership_patient.html", context
    )


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def create_retainership_wallet(request, patient_id):
    """Create a shared wallet for a retainership patient"""
    patient = get_object_or_404(Patient, id=patient_id)

    # Check if patient already has a retainership wallet
    if patient.wallet_memberships.filter(wallet__wallet_type="retainership").exists():
        messages.warning(request, "This patient already has a retainership wallet.")
        return redirect("retainership:retainership_patient_list")

    if request.method == "POST":
        try:
            # Get retainership info
            retainership_info = patient.retainership_info

            # Get custom wallet name from form or use default
            wallet_name = request.POST.get(
                "wallet_name", f"Retainership Wallet - {patient.get_full_name()}"
            )

            # Create shared wallet for retainership
            with transaction.atomic():
                wallet = SharedWallet.objects.create(
                    wallet_name=wallet_name,
                    wallet_type="retainership",
                    retainership_registration=retainership_info.retainership_reg_number,
                    balance=Decimal("0.00"),
                )

                # Create wallet membership
                WalletMembership.objects.create(
                    wallet=wallet, patient=patient, is_primary=True
                )

                # Create patient wallet linking to shared wallet
                patient_wallet, created = PatientWallet.objects.get_or_create(
                    patient=patient
                )
                patient_wallet.shared_wallet = wallet
                patient_wallet.save()

                messages.success(
                    request,
                    f'Retainership wallet "{wallet_name}" created successfully for {patient.get_full_name()}',
                )
                return redirect("retainership:retainership_patient_list")

        except Exception as e:
            messages.error(request, f"Error creating retainership wallet: {str(e)}")
            return redirect("retainership:retainership_patient_list")

    return render(
        request,
        "retainership/confirm_create_wallet.html",
        {
            "patient": patient,
            "title": f"Create Retainership Wallet for {patient.get_full_name()}",
        },
    )


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def manage_retainership_wallet(request, patient_id):
    """Manage retainership wallet transactions and settings"""
    patient = get_object_or_404(Patient, id=patient_id)

    # Get the retainership wallet
    retainership_wallet = None
    membership = patient.wallet_memberships.filter(
        wallet__wallet_type="retainership"
    ).first()

    if membership:
        retainership_wallet = membership.wallet

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "credit" and retainership_wallet:
            try:
                amount = Decimal(request.POST.get("amount", 0))
                description = request.POST.get("description", "Manual credit")

                if amount > 0:
                    retainership_wallet._credit(
                        amount=amount,
                        description=description,
                        transaction_type="credit",
                        user=request.user,
                        patient=patient,
                    )
                    messages.success(
                        request, f"Successfully credited ₦{amount} to wallet"
                    )
                else:
                    messages.error(request, "Amount must be positive")

            except Exception as e:
                messages.error(request, f"Error crediting wallet: {str(e)}")

        elif action == "debit" and retainership_wallet:
            try:
                amount = Decimal(request.POST.get("amount", 0))
                description = request.POST.get("description", "Manual debit")

                if amount > 0:
                    retainership_wallet._debit(
                        amount=amount,
                        description=description,
                        transaction_type="debit",
                        user=request.user,
                        patient=patient,
                    )
                    messages.success(
                        request, f"Successfully debited ₦{amount} from wallet"
                    )
                else:
                    messages.error(request, "Amount must be positive")

            except Exception as e:
                messages.error(request, f"Error debiting wallet: {str(e)}")

        elif action == "transfer" and retainership_wallet:
            try:
                amount = Decimal(request.POST.get("amount", 0))
                recipient_wallet_id = request.POST.get("recipient_wallet_id")
                description = request.POST.get("description", "Wallet transfer")

                if amount > 0 and recipient_wallet_id:
                    try:
                        recipient_wallet = SharedWallet.objects.get(
                            id=recipient_wallet_id, is_active=True
                        )

                        # Perform the transfer
                        sender_transaction, recipient_transaction = (
                            retainership_wallet.transfer_to(
                                recipient_wallet=recipient_wallet,
                                amount=amount,
                                description=description,
                                user=request.user,
                                patient=patient,
                            )
                        )

                        messages.success(
                            request,
                            f"Successfully transferred ₦{amount} to {recipient_wallet.wallet_name}",
                        )
                    except SharedWallet.DoesNotExist:
                        messages.error(
                            request, "Recipient wallet not found or is inactive"
                        )
                else:
                    messages.error(
                        request,
                        "Amount must be positive and recipient wallet must be selected",
                    )

            except Exception as e:
                messages.error(request, f"Error transferring funds: {str(e)}")

        return redirect("retainership:manage_wallet", patient_id=patient_id)

    # Get transaction history
    transactions = []
    if retainership_wallet:
        transactions = WalletTransaction.objects.filter(
            shared_wallet=retainership_wallet, patient=patient
        ).order_by("-created_at")[:20]

    # Get available wallets for transfer (exclude current wallet)
    available_wallets = []
    if retainership_wallet:
        available_wallets = SharedWallet.objects.exclude(
            id=retainership_wallet.id
        ).filter(is_active=True)

    return render(
        request,
        "retainership/manage_wallet.html",
        {
            "patient": patient,
            "wallet": retainership_wallet,
            "transactions": transactions,
            "available_wallets": available_wallets,
            "title": f"Manage Retainership Wallet - {patient.get_full_name()}",
        },
    )


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def link_retainership_patient_to_wallet(request, patient_id):
    """Link a retainership patient to an existing retainership wallet"""
    patient = get_object_or_404(Patient, id=patient_id)

    # Check if patient is already linked to a retainership wallet
    existing_membership = patient.wallet_memberships.filter(
        wallet__wallet_type="retainership"
    ).first()
    if existing_membership:
        messages.warning(
            request,
            f"This patient is already linked to a retainership wallet: {existing_membership.wallet.wallet_name}",
        )
        return redirect("retainership:retainership_patient_list")

    if request.method == "POST":
        form = RetainershipWalletLinkForm(request.POST)
        if form.is_valid():
            wallet = form.cleaned_data["wallet"]
            is_primary = form.cleaned_data["is_primary"]

            try:
                with transaction.atomic():
                    # Check if this wallet already has a primary member
                    if is_primary:
                        existing_primary = wallet.members.filter(
                            is_primary=True
                        ).first()
                        if existing_primary:
                            messages.warning(
                                request,
                                f"This wallet already has a primary member: {existing_primary.patient.get_full_name()}",
                            )
                            messages.info(
                                request,
                                "Adding this patient as a regular member instead.",
                            )
                            is_primary = False

                    # Create wallet membership
                    membership = WalletMembership.objects.create(
                        wallet=wallet, patient=patient, is_primary=is_primary
                    )

                    # Create or update patient wallet to link to shared wallet
                    patient_wallet, created = PatientWallet.objects.get_or_create(
                        patient=patient
                    )
                    patient_wallet.shared_wallet = wallet
                    patient_wallet.save()

                    messages.success(
                        request,
                        f"Successfully linked {patient.get_full_name()} to retainership wallet: {wallet.wallet_name}",
                    )
                    return redirect("retainership:retainership_patient_list")

            except Exception as e:
                messages.error(request, f"Error linking patient to wallet: {str(e)}")
                return redirect("retainership:retainership_patient_list")
    else:
        form = RetainershipWalletLinkForm()

    return render(
        request,
        "retainership/link_patient_to_wallet.html",
        {
            "form": form,
            "patient": patient,
            "title": f"Link {patient.get_full_name()} to Retainership Wallet",
        },
    )


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def add_member_to_retainership_wallet(request, wallet_id):
    """Add a patient to a retainership wallet"""
    wallet = get_object_or_404(SharedWallet, id=wallet_id, wallet_type="retainership")

    if request.method == "POST":
        form = AddMemberToWalletForm(request.POST, wallet=wallet)
        if form.is_valid():
            patient = form.cleaned_data["patient"]
            is_primary = form.cleaned_data["is_primary"]

            try:
                with transaction.atomic():
                    # Check if patient is already in this wallet
                    if wallet.members.filter(patient=patient).exists():
                        messages.warning(
                            request,
                            f"{patient.get_full_name()} is already a member of this wallet.",
                        )
                        return redirect(
                            "retainership:view_wallet_details", wallet_id=wallet.id
                        )

                    # Check if this wallet already has a primary member
                    if is_primary:
                        existing_primary = wallet.members.filter(
                            is_primary=True
                        ).first()
                        if existing_primary:
                            messages.warning(
                                request,
                                f"This wallet already has a primary member: {existing_primary.patient.get_full_name()}",
                            )
                            messages.info(
                                request,
                                "Adding this patient as a regular member instead.",
                            )
                            is_primary = False

                    # Create wallet membership
                    membership = WalletMembership.objects.create(
                        wallet=wallet, patient=patient, is_primary=is_primary
                    )

                    # Create or update patient wallet to link to shared wallet
                    patient_wallet, created = PatientWallet.objects.get_or_create(
                        patient=patient, defaults={"balance": Decimal("0.00")}
                    )
                    patient_wallet.shared_wallet = wallet
                    patient_wallet.save()

                    messages.success(
                        request,
                        f"Successfully added {patient.get_full_name()} to retainership wallet: {wallet.wallet_name}",
                    )
                    return redirect(
                        "retainership:view_wallet_details", wallet_id=wallet.id
                    )

            except Exception as e:
                messages.error(request, f"Error adding member to wallet: {str(e)}")
                return redirect("retainership:view_wallet_details", wallet_id=wallet.id)
    else:
        form = AddMemberToWalletForm(wallet=wallet)

    context = {
        "form": form,
        "wallet": wallet,
        "title": f"Add Member to {wallet.wallet_name}",
    }
    return render(request, "retainership/add_member_to_wallet.html", context)


@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def htmx_search_patients_for_wallet(request, wallet_id):
    """HTMX endpoint for searching patients to add to a wallet"""
    wallet = get_object_or_404(SharedWallet, id=wallet_id, wallet_type="retainership")
    search_query = request.GET.get("q", "")

    # Get current members to exclude
    current_member_ids = wallet.members.values_list("patient_id", flat=True)

    # Search patients
    patients = Patient.objects.filter(is_active=True).exclude(id__in=current_member_ids)

    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(patient_id__icontains=search_query)
            | Q(phone_number__icontains=search_query)
        ).order_by("first_name", "last_name")[:10]
    else:
        patients = patients.order_by("first_name", "last_name")[:10]

    context = {"patients": patients, "wallet": wallet}
    return render(request, "retainership/partials/patient_search_results.html", context)


@login_required
@login_required
@role_required(
    [ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_RECEPTIONIST, ROLE_HEALTH_RECORD_OFFICER]
)
def wallet_members_partial(request, wallet_id):
    """HTMX endpoint for viewing wallet members"""
    wallet = get_object_or_404(SharedWallet, id=wallet_id, wallet_type="retainership")
    members = wallet.members.select_related("patient").all()

    context = {
        "wallet": wallet,
        "members": members,
    }
    return render(request, "retainership/partials/wallet_members.html", context)
