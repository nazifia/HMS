"""One call behind the app's home screen: what needs attention right now.

A tile is only returned if the user holds the same model permission the
module's own endpoints require, so the dashboard never advertises a screen the
server would refuse to open.
"""
from django.db.models import F, Sum
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


def _clinic_queue():
    from consultations.services import waiting_queue

    return waiting_queue().count(), 'waiting or in progress'


def _unpaid_invoices():
    from billing.models import Invoice

    unpaid = Invoice.objects.filter(status__in=['pending', 'partially_paid'])
    totals = unpaid.aggregate(total=Sum('total_amount'), paid=Sum('amount_paid'))
    owed = (totals['total'] or 0) - (totals['paid'] or 0)
    return unpaid.count(), f'{owed:,.2f} outstanding'


def _lab_verification():
    from laboratory.models import TestResult

    count = TestResult.objects.filter(verified_by__isnull=True).count()
    return count, 'awaiting sign-off'


def _low_stock():
    from pharmacy.models import ActiveStoreInventory

    count = ActiveStoreInventory.objects.filter(
        stock_quantity__lte=F('reorder_level')
    ).count()
    return count, 'at or below reorder level'


def _free_beds():
    from inpatient.models import Bed

    count = Bed.objects.filter(is_occupied=False, is_active=True).count()
    return count, 'available now'


# key, label, required permission, counter
TILES = [
    ('clinic_queue', 'Clinic queue', 'consultations.view_waitinglist', _clinic_queue),
    ('unpaid_invoices', 'Unpaid invoices', 'billing.view_invoice', _unpaid_invoices),
    ('lab_verification', 'Results to verify', 'laboratory.view_testresult', _lab_verification),
    ('low_stock', 'Low stock', 'pharmacy.view_activestoreinventory', _low_stock),
    ('free_beds', 'Beds free', 'inpatient.view_bed', _free_beds),
]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard(request):
    tiles = []
    for key, label, perm, counter in TILES:
        if not request.user.has_perm(perm):
            continue
        count, note = counter()
        tiles.append({'key': key, 'label': label, 'count': count, 'note': note})
    return Response({'tiles': tiles})
