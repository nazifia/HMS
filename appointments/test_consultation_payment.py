"""Consultation fee must be paid before an appointment can be completed.

Run: python manage.py test appointments.test_consultation_payment
"""
import datetime

from django.test import TestCase
from django.utils import timezone

from accounts.models import CustomUser
from appointments.models import Appointment
from billing.fee_utils import create_consultation_fee
from patients.models import Patient


class ConsultationPaymentGateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = CustomUser.objects.create_user(
            phone_number='08000000010', username='paydoc', password='x',
            first_name='Pay', last_name='Doc',
        )
        cls.patient = Patient.objects.create(
            first_name='Bola', last_name='Ade', date_of_birth='1990-01-01',
            gender='F', phone_number='+2348000000002', patient_type='regular',
        )

    def make_appointment(self):
        return Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.now() + datetime.timedelta(days=1),
            reason='checkup', status='confirmed',
        )

    def test_unpaid_fee_blocks_completion(self):
        appointment = self.make_appointment()
        invoice = create_consultation_fee(self.patient)
        invoice.appointment = appointment
        invoice.save(update_fields=['appointment'])
        self.assertFalse(appointment.consultation_payment_verified())

    def test_paid_fee_allows_completion(self):
        appointment = self.make_appointment()
        invoice = create_consultation_fee(self.patient)
        invoice.appointment = appointment
        invoice.amount_paid = invoice.total_amount  # Invoice.save() derives status
        invoice.save()
        self.assertTrue(appointment.consultation_payment_verified())

    def test_unlinked_patient_invoice_still_found(self):
        appointment = self.make_appointment()
        create_consultation_fee(self.patient)  # not linked to appointment
        self.assertFalse(appointment.consultation_payment_verified())

    def test_unpaid_fee_blocks_confirmation_via_ajax(self):
        from django.test import Client
        appointment = self.make_appointment()
        appointment.status = 'scheduled'
        appointment.save(update_fields=['status'])
        invoice = create_consultation_fee(self.patient)
        invoice.appointment = appointment
        invoice.save(update_fields=['appointment'])
        client = Client()
        client.force_login(CustomUser.objects.create_superuser(
            phone_number='08000000011', username='payadmin', password='x',
        ))
        response = client.post(
            f'/appointments/update-appointment-status/{appointment.id}/',
            {'status': 'confirmed'},
        )
        self.assertEqual(response.status_code, 400)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'scheduled')

    def test_non_regular_patient_exempt(self):
        self.patient.patient_type = 'nhia'
        self.patient.save(update_fields=['patient_type'])
        appointment = self.make_appointment()
        self.assertTrue(appointment.consultation_payment_verified())
