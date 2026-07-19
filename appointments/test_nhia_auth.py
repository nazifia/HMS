"""NHIA authorization requirement on appointment booking.

Run: python manage.py test appointments.test_nhia_auth
"""
import datetime

from django.test import TestCase
from django.utils import timezone

from accounts.models import CustomUser
from appointments.forms import AppointmentForm
from appointments.models import DoctorSchedule
from nhia.models import AuthorizationCode, NHIAPatient
from patients.models import Patient


class NhiaAppointmentAuthTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = CustomUser.objects.create_user(
            phone_number='08000000009', username='nhiadoc', password='x',
            first_name='Ngozi', last_name='Doc',
        )
        profile = cls.doctor.profile
        profile.role = 'doctor'
        profile.save()
        # Next Monday, never "today", so the past-time rule can't interfere.
        today = timezone.localdate()
        cls.day = today + datetime.timedelta(days=(7 - today.weekday()) or 7)
        DoctorSchedule.objects.create(
            doctor=cls.doctor, weekday=cls.day.weekday(),
            start_time=datetime.time(9, 0), end_time=datetime.time(17, 0),
        )

    def setUp(self):
        self.patient = Patient.objects.create(
            first_name='Ada', last_name='Obi', date_of_birth='1990-01-01',
            gender='F', phone_number='+2348000000001',
        )

    def form_for(self, patient, code=''):
        return AppointmentForm(data={
            'patient': patient.pk,
            'doctor': self.doctor.pk,
            'appointment_date': self.day.isoformat(),
            'appointment_time': '10:00',
            'reason': 'checkup',
            'status': 'scheduled',
            'priority': 'normal',
            'authorization_code': code,
        })

    def make_code(self, code='AUTH-123', service_type='general', days=30):
        return AuthorizationCode.objects.create(
            code=code, patient=self.patient, service_type=service_type,
            amount=0,
            expiry_date=timezone.localdate() + datetime.timedelta(days=days),
        )

    def test_non_nhia_patient_needs_no_code(self):
        form = self.form_for(self.patient)
        form.is_valid()
        self.assertNotIn('authorization_code', form.errors)

    def test_nhia_patient_without_code_rejected(self):
        NHIAPatient.objects.create(patient=self.patient, nhia_reg_number='NHIA-1')
        form = self.form_for(self.patient)
        form.is_valid()
        self.assertIn('authorization_code', form.errors)

    def test_nhia_patient_with_valid_code_accepted(self):
        NHIAPatient.objects.create(patient=self.patient, nhia_reg_number='NHIA-1')
        auth = self.make_code()
        form = self.form_for(self.patient, code='AUTH-123')
        form.is_valid()
        self.assertNotIn('authorization_code', form.errors)
        self.assertEqual(form.cleaned_data.get('authorization_code_obj'), auth)

    def test_nhia_patient_with_expired_code_rejected(self):
        NHIAPatient.objects.create(patient=self.patient, nhia_reg_number='NHIA-1')
        self.make_code(code='AUTH-OLD', days=-1)
        form = self.form_for(self.patient, code='AUTH-OLD')
        form.is_valid()
        self.assertIn('authorization_code', form.errors)

    def test_wrong_service_type_rejected(self):
        NHIAPatient.objects.create(patient=self.patient, nhia_reg_number='NHIA-1')
        self.make_code(code='AUTH-LAB', service_type='laboratory')
        form = self.form_for(self.patient, code='AUTH-LAB')
        form.is_valid()
        self.assertIn('authorization_code', form.errors)

    def test_code_consumed_on_booking(self):
        NHIAPatient.objects.create(patient=self.patient, nhia_reg_number='NHIA-1')
        auth = self.make_code()
        form = self.form_for(self.patient, code='AUTH-123')
        self.assertTrue(form.is_valid(), form.errors)
        appointment = form.save()
        auth.refresh_from_db()
        self.assertEqual(auth.status, 'used')
        self.assertEqual(auth.used_for, f"Appointment #{appointment.pk}")
        # Re-saving the same appointment must not choke on the now-used code.
        edit = AppointmentForm(data=form.data, instance=appointment)
        self.assertTrue(edit.is_valid(), edit.errors)
