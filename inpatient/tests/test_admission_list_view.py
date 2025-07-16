from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from accounts.models import CustomUser
from patients.models import Patient
from inpatient.models import Ward, Bed, Admission
from billing.models import ServiceCategory, Service

class AdmissionListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            first_name='Test',
            last_name='User',
            phone_number='1234567890',
            is_superuser=True,
            is_staff=True
        )
        self.client.login(username='testuser', password='password123')

        self.patient1 = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='M',
            address='123 Main St',
            city='Anytown',
            state='CA',
            country='USA',
            patient_id='PAT001'
        )
        self.patient2 = Patient.objects.create(
            first_name='Jane',
            last_name='Doe',
            date_of_birth='1992-02-02',
            gender='F',
            address='456 Oak Ave',
            city='Othertown',
            state='NY',
            country='USA',
            patient_id='PAT002'
        )

        self.ward = Ward.objects.create(
            name='General Ward',
            ward_type='general',
            floor='1',
            capacity=10,
            charge_per_day=100
        )
        self.bed1 = Bed.objects.create(ward=self.ward, bed_number='101', is_occupied=True)
        self.bed2 = Bed.objects.create(ward=self.ward, bed_number='102', is_occupied=False)

        self.service_category = ServiceCategory.objects.create(name='Admission Services')
        self.admission_service = Service.objects.create(
            name='Admission Fee',
            category=self.service_category,
            price=Decimal('100.00')
        )

        self.admission1 = Admission.objects.create(
            patient=self.patient1,
            admission_date=timezone.now(),
            bed=self.bed1,
            diagnosis='Fever',
            status='admitted',
            attending_doctor=self.user,
            reason_for_admission='High fever'
        )
        self.admission2 = Admission.objects.create(
            patient=self.patient2,
            admission_date=timezone.now() - timedelta(days=5),
            discharge_date=timezone.now() - timedelta(days=1),
            bed=self.bed2,
            diagnosis='Flu',
            status='discharged',
            attending_doctor=self.user,
            reason_for_admission='Severe flu'
        )

    def test_admission_list_shows_only_admitted_by_default(self):
        response = self.client.get(reverse('inpatient:admissions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient1.get_full_name())
        self.assertNotContains(response, self.patient2.get_full_name())

    def test_admission_list_shows_discharged_when_filtered(self):
        response = self.client.get(reverse('inpatient:admissions') + '?status=discharged')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient2.get_full_name())
        self.assertNotContains(response, self.patient1.get_full_name())

    def test_admission_list_shows_all_when_no_status_filter_and_all_admissions_are_admitted(self):
        # Create another admitted patient
        patient3 = Patient.objects.create(
            first_name='Peter',
            last_name='Pan',
            date_of_birth='1985-05-05',
            gender='M',
            address='789 Neverland',
            city='Fantasy',
            state='CA',
            country='USA',
            patient_id='PAT003'
        )
        bed3 = Bed.objects.create(ward=self.ward, bed_number='103', is_occupied=True)
        admission3 = Admission.objects.create(
            patient=patient3,
            admission_date=timezone.now(),
            bed=bed3,
            diagnosis='Cold',
            status='admitted',
            attending_doctor=self.user,
            reason_for_admission='Common cold'
        )

        response = self.client.get(reverse('inpatient:admissions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient1.get_full_name())
        self.assertContains(response, patient3.get_full_name())
        self.assertNotContains(response, self.patient2.get_full_name()) # Still should not contain discharged patient

    def test_admission_list_shows_all_when_no_status_filter_and_some_admissions_are_discharged(self):
        # This test is to ensure that the default behavior is to *exclude* discharged patients
        # unless explicitly filtered for.
        response = self.client.get(reverse('inpatient:admissions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient1.get_full_name())
        self.assertNotContains(response, self.patient2.get_full_name())

    def test_admission_list_shows_all_statuses_when_status_filter_is_empty(self):
        # This test ensures that if the status filter is explicitly empty, it behaves like all() (which it should not, based on the requirement)
        # The requirement is to *remove* discharged patients from the default view.
        # So, if status is empty, it should still only show 'admitted'.
        response = self.client.get(reverse('inpatient:admissions') + '?status=')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient1.get_full_name())
        self.assertNotContains(response, self.patient2.get_full_name())

