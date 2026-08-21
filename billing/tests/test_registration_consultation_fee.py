"""Registration bills the consultation fee on the same invoice.

Run: python manage.py test billing.tests.test_registration_consultation_fee
"""
from decimal import Decimal

from django.test import TestCase

from billing.fee_utils import (
    CONSULTATION_FEE_SERVICE_NAME,
    REGISTRATION_FEE_SERVICE_NAME,
    create_consultation_fee,
    create_registration_fee,
    get_consultation_fee_service,
    get_registration_fee_service,
)
from patients.models import Patient


class RegistrationConsultationFeeTest(TestCase):
    def make_patient(self, patient_type="regular", patient_id="P100"):
        return Patient.objects.create(
            first_name="Reg", last_name="Fee", date_of_birth="1990-01-01",
            gender="M", patient_type=patient_type, patient_id=patient_id,
        )

    def test_one_invoice_carries_both_fees(self):
        patient = self.make_patient()
        invoice = create_registration_fee(patient)
        names = sorted(invoice.items.values_list("description", flat=True))
        self.assertEqual(
            names, sorted([REGISTRATION_FEE_SERVICE_NAME, CONSULTATION_FEE_SERVICE_NAME])
        )
        expected = (
            get_registration_fee_service().price + get_consultation_fee_service().price
        )
        self.assertEqual(invoice.total_amount, expected)

    def test_clinic_type_selects_its_consultation_fee(self):
        patient = self.make_patient(patient_id="P101")
        invoice = create_registration_fee(patient, clinic_type="sopd")
        self.assertTrue(
            invoice.items.filter(description="SOPD Consultation Fee").exists()
        )

    def test_waiting_list_does_not_bill_the_fee_twice(self):
        patient = self.make_patient(patient_id="P102")
        create_registration_fee(patient)
        self.assertIsNone(create_consultation_fee(patient, clinic_type="mopd"))

    def test_paying_the_invoice_still_blocks_a_second_charge(self):
        patient = self.make_patient(patient_id="P103")
        invoice = create_registration_fee(patient)
        invoice.amount_paid = invoice.total_amount
        invoice.save()
        self.assertIsNone(create_consultation_fee(patient))
        patient.refresh_from_db()
        self.assertTrue(patient.is_active)

    def test_dearer_clinic_bills_only_the_difference(self):
        patient = self.make_patient(patient_id="P106")
        create_registration_fee(patient)  # generic 1000 consultation fee
        top_up = create_consultation_fee(patient, clinic_type="sopd")
        self.assertIsNotNone(top_up)
        self.assertEqual(top_up.total_amount, Decimal("500.00"))
        # A second visit to the same (or a cheaper) clinic adds nothing.
        self.assertIsNone(create_consultation_fee(patient, clinic_type="sopd"))
        self.assertIsNone(create_consultation_fee(patient, clinic_type="mopd"))

    def test_cheaper_clinic_is_not_billed_or_refunded(self):
        patient = self.make_patient(patient_id="P107")
        create_registration_fee(patient, clinic_type="sopd")
        self.assertIsNone(create_consultation_fee(patient, clinic_type="mopd"))

    def test_nhia_pays_nothing_at_registration(self):
        patient = self.make_patient(patient_type="nhia", patient_id="P104")
        self.assertIsNone(create_registration_fee(patient))

    def test_walk_in_consultation_without_registration_still_bills(self):
        patient = self.make_patient(patient_id="P105")
        patient.is_active = True
        patient.save(update_fields=["is_active"])
        invoice = create_consultation_fee(patient, clinic_type="sopd")
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.total_amount, Decimal("1500.00"))
