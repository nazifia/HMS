"""Inpatient workflow shared by the HTML views, the management command and the API.

The arithmetic already lives on `Admission` (`get_duration`, `get_total_cost`,
`get_outstanding_admission_cost`, `get_total_wallet_impact`); this module holds
the workflow around it — which bed may be taken, what admitting charges, what
discharging frees, and the once-per-day rule for daily charges.
"""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from patients.models import PatientWallet, WalletTransaction

from .models import Admission, Bed, BedTransfer, WardTransfer


class InpatientActionError(Exception):
    """An inpatient action that is not allowed right now."""


def assert_bed_available(bed):
    """Raise unless this bed can take a patient."""
    if bed is None:
        raise InpatientActionError("Select a bed.")
    if not bed.is_active:
        raise InpatientActionError(
            f"Bed {bed.bed_number} in {bed.ward.name} is out of service."
        )
    if bed.is_occupied:
        raise InpatientActionError(
            f"Bed {bed.bed_number} in {bed.ward.name} is already occupied."
        )


def resolve_authorization_code(patient, code):
    """Validate an NHIA authorization code offered for an admission."""
    if code is None:
        return None
    if not code.is_valid():
        raise InpatientActionError("The provided authorization code is not valid.")
    if code.patient_id != patient.id:
        raise InpatientActionError(
            "The provided authorization code is not for this patient."
        )
    return code


def admit_patient(patient, bed, attending_doctor, diagnosis,
                  reason_for_admission, user, admission_notes="",
                  admission_date=None, admission_service=None,
                  authorization_code=None):
    """Admit a patient: take the bed, raise the invoice, charge the wallet.

    Returns (admission, invoice). `invoice` is None when no admission service
    was given — some deployments have no Admission Fee service configured.
    """
    from billing.models import Invoice, InvoiceItem

    assert_bed_available(bed)
    authorization_code = resolve_authorization_code(patient, authorization_code)

    if patient.admissions.filter(status="admitted").exists():
        raise InpatientActionError(
            f"{patient.get_full_name()} is already admitted. Discharge the "
            f"existing admission first."
        )

    with transaction.atomic():
        admission = Admission(
            patient=patient,
            bed=bed,
            attending_doctor=attending_doctor,
            diagnosis=diagnosis,
            reason_for_admission=reason_for_admission,
            admission_notes=admission_notes,
            admission_date=admission_date or timezone.now(),
            authorization_code=authorization_code,
            status="admitted",
            created_by=user,
        )
        # Tells the post_save fallback in signals.py to stand down: the charge
        # below is the one that knows about the chosen service, NHIA cover and
        # the authorization code. Without this the patient is billed twice.
        admission._charge_handled = True
        admission.save()
        # Admission.save() flips the bed, but only for the row it holds.
        bed.refresh_from_db(fields=["is_occupied"])

        if admission_service is None:
            return admission, None

        paid_by_nhia = authorization_code is not None
        invoice = Invoice.objects.create(
            patient=patient,
            invoice_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7),
            notes=admission_notes,
            subtotal=admission_service.price,
            tax_amount=0,
            discount_amount=0,
            total_amount=admission_service.price,
            amount_paid=admission_service.price if paid_by_nhia else Decimal("0.00"),
            payment_method="insurance" if paid_by_nhia else None,
            payment_date=timezone.now() if paid_by_nhia else None,
            status="paid" if paid_by_nhia else "pending",
            admission=admission,
            source_app="inpatient",
            created_by=user,
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            service=admission_service,
            quantity=1,
            unit_price=admission_service.price,
            total_amount=admission_service.price,
        )

        if paid_by_nhia:
            authorization_code.mark_as_used(f"Admission #{admission.id}")
        elif admission_service.price > 0:
            wallet, _ = PatientWallet.objects.get_or_create(
                patient=patient,
                defaults={"balance": Decimal("0.00"), "is_active": True},
            )
            # Negative balances are allowed: care is not withheld over a wallet.
            wallet.debit(
                amount=admission_service.price,
                description=(
                    f"Admission fee for {patient.get_full_name()} - "
                    f"{bed.ward.name}"
                ),
                transaction_type="admission_fee",
                user=user,
                invoice=invoice,
                admission=admission,
            )

    return admission, invoice


def discharge_patient(admission, user=None, status="discharged",
                      discharge_date=None, discharge_notes=""):
    """End an admission and free its bed."""
    if admission.status != "admitted":
        raise InpatientActionError(
            f"This admission is already {admission.get_status_display().lower()}."
        )
    if status not in ("discharged", "transferred", "deceased"):
        raise InpatientActionError("Invalid discharge status.")

    with transaction.atomic():
        admission.status = status
        admission.discharge_date = discharge_date or timezone.now()
        if discharge_notes:
            admission.discharge_notes = discharge_notes
        # Admission.save() releases the bed when the status leaves 'admitted'.
        admission.save()

    return admission


def transfer_patient(admission, to_bed, user=None, notes=""):
    """Move an admission to another bed, writing the history rows.

    A move that crosses wards writes both a WardTransfer and a BedTransfer —
    the ward change is what the ward board cares about, the bed change is what
    the nurses do.
    """
    if admission.status != "admitted":
        raise InpatientActionError("Only an active admission can be transferred.")
    if admission.bed_id == to_bed.id:
        raise InpatientActionError("The patient is already in that bed.")

    assert_bed_available(to_bed)
    from_bed = admission.bed

    with transaction.atomic():
        if from_bed is not None:
            if from_bed.ward_id != to_bed.ward_id:
                WardTransfer.objects.create(
                    admission=admission,
                    from_ward=from_bed.ward,
                    to_ward=to_bed.ward,
                    notes=notes,
                )
            BedTransfer.objects.create(
                admission=admission,
                from_bed=from_bed,
                to_bed=to_bed,
                notes=notes,
            )
            Bed.objects.filter(pk=from_bed.pk).update(is_occupied=False)

        Bed.objects.filter(pk=to_bed.pk).update(is_occupied=True)
        admission.bed = to_bed
        admission.save()

    return admission


def charge_admission_for_date(admission, charge_date=None, user=None,
                              dry_run=False):
    """Apply one day's bed charge to the patient's wallet.

    Idempotent per (admission, date) — running the daily job twice must not
    charge twice. Returns (amount, reason); amount is None when nothing was
    charged and reason says why.
    """
    charge_date = charge_date or timezone.now().date()

    if admission.patient.is_nhia_patient():
        return None, "NHIA patient - exempt from admission charges"

    admitted_on = admission.admission_date.date()
    discharged_on = (
        admission.discharge_date.date() if admission.discharge_date else None
    )
    if charge_date < admitted_on:
        return None, "Charge date is before admission"
    if discharged_on and charge_date > discharged_on:
        return None, "Charge date is after discharge"

    if not admission.bed or not admission.bed.ward:
        return None, "No bed assigned"

    daily_charge = admission.bed.ward.charge_per_day
    if daily_charge <= 0:
        return None, "No daily charge configured for this ward"

    wallet, _ = PatientWallet.objects.get_or_create(
        patient=admission.patient,
        defaults={"balance": Decimal("0.00"), "is_active": True},
    )

    already_charged = WalletTransaction.objects.filter(
        admission=admission,
        transaction_type="daily_admission_charge",
        created_at__date=charge_date,
    ).exists()
    if already_charged:
        return None, "Already charged for this date"

    if dry_run:
        return daily_charge, "Would charge"

    wallet.debit(
        amount=daily_charge,
        description=(
            f"Daily admission charge for {charge_date} - "
            f"{admission.bed.ward.name}"
        ),
        transaction_type="daily_admission_charge",
        user=user or admission.attending_doctor,
        admission=admission,
    )
    return daily_charge, "Charged"
