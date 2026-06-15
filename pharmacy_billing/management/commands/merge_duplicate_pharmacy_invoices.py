"""
Find and merge duplicate pharmacy invoices.

A prescription is only ever meant to have a single open billing track (plus
extra invoices for genuine partial dispensing). Bugs in the cart workflow could
leave a prescription with two *paid* invoices for the same medications -- e.g. a
cart is paid, then cancelled, and a new cart re-bills the full amount. That is a
real double charge.

This command collapses such duplicates down to one canonical invoice per
prescription and refunds any wallet-paid duplicate back to the patient wallet.
Non-wallet duplicate payments (card/cash/insurance) cannot be auto-refunded and
are only reported, so an accountant can action them manually.

Runs in DRY-RUN by default. Pass --apply to make changes.

    python manage.py merge_duplicate_pharmacy_invoices            # preview
    python manage.py merge_duplicate_pharmacy_invoices --apply    # execute
    python manage.py merge_duplicate_pharmacy_invoices --prescription 26 --apply
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from pharmacy_billing.models import Invoice
from patients.models import PatientWallet


# Cart statuses that mean the cart is a live billing track (not abandoned).
NON_CANCELLED_CART_STATUSES = {
    "active",
    "invoiced",
    "paid",
    "partially_dispensed",
    "completed",
}


class Command(BaseCommand):
    help = "Find and merge duplicate pharmacy invoices for a prescription."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag the command only previews (dry-run).",
        )
        parser.add_argument(
            "--prescription",
            type=int,
            default=None,
            help="Only process this prescription id.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        only_presc = options["prescription"]

        mode = "APPLY" if apply else "DRY-RUN"
        self.stdout.write(self.style.MIGRATE_HEADING(f"[{mode}] Duplicate pharmacy invoice merge"))

        groups = (
            Invoice.objects.filter(prescription__isnull=False)
            .values("prescription")
            .annotate(c=Count("id"))
            .filter(c__gt=1)
        )
        if only_presc is not None:
            groups = groups.filter(prescription=only_presc)

        presc_ids = [g["prescription"] for g in groups]
        if not presc_ids:
            self.stdout.write(self.style.SUCCESS("No prescriptions with duplicate invoices found."))
            return

        self.stdout.write(f"Found {len(presc_ids)} prescription(s) with duplicate invoices: {presc_ids}")

        total_refunded = Decimal("0.00")
        manual_followups = []

        for presc_id in presc_ids:
            invoices = list(
                Invoice.objects.filter(prescription_id=presc_id).order_by("invoice_date", "id")
            )
            canonical = self._pick_canonical(invoices)
            duplicates = [inv for inv in invoices if inv.id != canonical.id]

            self.stdout.write("")
            self.stdout.write(self.style.HTTP_INFO(f"Prescription {presc_id}:"))
            self.stdout.write(f"  KEEP   invoice {canonical.id} (status={canonical.status}, total={canonical.total_amount})")

            for dup in duplicates:
                refund, follow = self._process_duplicate(presc_id, dup, apply)
                total_refunded += refund
                if follow:
                    manual_followups.append(follow)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Total wallet refunds: ₦{total_refunded}"))
        if manual_followups:
            self.stdout.write(self.style.WARNING("Manual follow-up required (non-wallet duplicate payments):"))
            for f in manual_followups:
                self.stdout.write(self.style.WARNING(f"  - {f}"))
        if not apply:
            self.stdout.write(self.style.WARNING("DRY-RUN: no changes saved. Re-run with --apply to commit."))

    def _pick_canonical(self, invoices):
        """Canonical = invoice tied to a live (non-cancelled) cart; prefer paid;
        tie-break on newest. Falls back to the newest invoice if none qualify."""
        def cart_status(inv):
            cart = inv.prescription_cart.order_by("-id").first()
            return cart.status if cart else None

        live = [inv for inv in invoices if cart_status(inv) in NON_CANCELLED_CART_STATUSES]
        pool = live or invoices
        paid_live = [inv for inv in pool if inv.status == "paid"]
        candidates = paid_live or pool
        # invoices already ordered by invoice_date, id ascending -> last = newest
        return candidates[-1]

    def _process_duplicate(self, presc_id, dup, apply):
        """Cancel a duplicate invoice; refund wallet payments. Returns (refunded, followup_note)."""
        wallet_paid = dup.payments.filter(payment_method="wallet")
        other_paid = dup.payments.exclude(payment_method="wallet")
        wallet_total = sum((p.amount for p in wallet_paid), Decimal("0.00"))
        other_total = sum((p.amount for p in other_paid), Decimal("0.00"))

        self.stdout.write(
            f"  MERGE  invoice {dup.id} (status={dup.status}, total={dup.total_amount}, "
            f"wallet_paid=₦{wallet_total}, other_paid=₦{other_total})"
        )

        refunded = Decimal("0.00")
        followup = None

        if wallet_total > 0:
            self.stdout.write(f"         -> refund ₦{wallet_total} to patient wallet")
        if other_total > 0:
            followup = (
                f"Prescription {presc_id}, invoice {dup.id}: ₦{other_total} paid via "
                f"{', '.join(sorted(set(p.payment_method for p in other_paid)))} "
                f"needs a manual refund (cannot auto-refund to wallet)."
            )
            self.stdout.write(self.style.WARNING(f"         -> {followup}"))
        self.stdout.write(f"         -> mark invoice {dup.id} as cancelled")

        if apply:
            # All-or-nothing: refund, cancel and cart detach commit together.
            # Note: WalletTransaction.invoice expects a billing.Invoice, not a
            # pharmacy_billing.Invoice, so the pharmacy invoice id is recorded in
            # the description instead of the FK.
            with transaction.atomic():
                if wallet_total > 0:
                    wallet, _ = PatientWallet.objects.get_or_create(patient=dup.patient)
                    wallet.credit(
                        amount=wallet_total,
                        description=f"Refund of duplicate pharmacy invoice #{dup.id} (prescription #{presc_id})",
                        transaction_type="refund",
                    )
                    refunded = wallet_total
                dup.status = "cancelled"
                dup.save(update_fields=["status"])
                # Detach any cart still pointing at the cancelled invoice.
                dup.prescription_cart.update(status="cancelled")

        return refunded, followup
