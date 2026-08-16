"""What a patient still owes, in one place.

The wallet screens (web and mobile) both need this figure, and it has to agree
between them: an admission's unpaid balance plus every unpaid or part-paid
invoice.
"""
from decimal import Decimal


def patient_outstanding(patient):
    """Returns {'admissions', 'invoices', 'total'} as Decimals."""
    from billing.models import Invoice
    from inpatient.models import Admission

    admissions = sum(
        (
            admission.get_outstanding_admission_cost()
            for admission in Admission.objects.filter(
                patient=patient, status="admitted"
            )
        ),
        Decimal("0.00"),
    )

    invoices = sum(
        (
            invoice.get_balance()
            for invoice in Invoice.objects.filter(
                patient=patient, status__in=["pending", "partially_paid"]
            )
        ),
        Decimal("0.00"),
    )

    return {
        "admissions": admissions,
        "invoices": invoices,
        "total": admissions + invoices,
    }
