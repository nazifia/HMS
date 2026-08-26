"""Self-check for the tenant engine. Run: python manage.py test saas"""
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect
from django.test import Client, TestCase
from django.utils import timezone

from patients.models import Patient, Vitals

from .current import clear_current_hospital, set_current_hospital
from .models import Hospital, Plan, Subscription, enforce_limit


def _make_patient():
    return Patient.objects.create(
        first_name="A", last_name="B", date_of_birth=date(1990, 1, 1),
        gender="M", address="x", city="y", state="z",
    )


class TenantEngineTests(TestCase):
    def setUp(self):
        self.h1 = Hospital.objects.create(name="H1", subdomain="h1")
        self.h2 = Hospital.objects.create(name="H2", subdomain="h2")
        self.addCleanup(clear_current_hospital)

    def test_scoping_and_autostamp(self):
        set_current_hospital(self.h1)
        p = _make_patient()
        self.assertEqual(p.hospital, self.h1)          # auto-stamped
        self.assertEqual(Patient.objects.count(), 1)   # h1 sees its row

        set_current_hospital(self.h2)
        self.assertEqual(Patient.objects.count(), 0)   # h2 isolated
        self.assertEqual(Patient.all_objects.count(), 1)  # escape hatch sees all

    def test_plan_limit(self):
        plan = Plan.objects.create(name="Tiny", max_patients=1)
        Subscription.objects.create(
            hospital=self.h1, plan=plan, status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        set_current_hospital(self.h1)
        enforce_limit(self.h1, Patient, "max_patients")  # 0 used, cap 1 -> ok
        _make_patient()
        with self.assertRaises(ValidationError):       # 1 used, cap 1 -> blocked
            enforce_limit(self.h1, Patient, "max_patients")


class ManualActivationTests(TestCase):
    """Free-tier fallback: lapsed tenant requests activation -> back to pending."""

    def setUp(self):
        self.h = Hospital.objects.create(name="H", subdomain="h")
        self.plan = Plan.objects.create(name="P", price=0)
        self.sub = Subscription.objects.create(
            hospital=self.h, plan=self.plan, status="active",
            current_period_end=timezone.now() - timedelta(days=1),  # lapsed
        )
        self.addCleanup(clear_current_hospital)

    def test_lapsed_request_routes_to_pending(self):
        # Path-based tenant URL; lapsed sub must still reach the activation view
        # (not get bounced to billing by the gate), then flip to pending.
        resp = Client().post("/t/h/saas/request-activation/")
        self.assertEqual(resp.status_code, 302)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "pending")


class TenantIsolationTests(TestCase):
    """Session cookies are host-wide: a logged-in user must stay in their own
    hospital whatever /t/<sub> prefix (or none) they type."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.test import RequestFactory

        self.rf = RequestFactory()
        self.h1 = Hospital.objects.create(name="H1", subdomain="h1")
        self.h2 = Hospital.objects.create(name="H2", subdomain="h2")
        plan = Plan.objects.create(name="Free", price=0)
        for h in (self.h1, self.h2):
            Subscription.objects.create(
                hospital=h, plan=plan, status="active",
                current_period_end=timezone.now() + timedelta(days=30),
            )
        User = get_user_model()
        self.staff1 = User.objects.create_user(
            phone_number="08010000001", username="s1", password="pw", hospital=self.h1
        )
        self.ops = User.objects.create_user(
            phone_number="08010000002", username="ops", password="pw"
        )
        self.addCleanup(clear_current_hospital)

    def _run(self, path, user):
        """Push a request through TenantMiddleware; report (status, scoped-to)."""
        from saas.current import get_current_hospital
        from saas.middleware import TenantMiddleware

        seen = {}

        def view(request):
            seen["hospital"] = get_current_hospital()
            return HttpResponse("ok")

        request = self.rf.get(path)
        request.user = user
        response = TenantMiddleware(view)(request)
        return response, seen.get("hospital")

    def test_other_tenants_prefix_is_forbidden(self):
        response, scoped = self._run("/t/h2/patients/", self.staff1)
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(scoped)  # view never ran

    def test_bare_host_scopes_to_own_hospital(self):
        # Without binding, TenantManager falls open here and returns every
        # hospital's rows.
        response, scoped = self._run("/patients/", self.staff1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(scoped, self.h1)

    def test_own_prefix_allowed(self):
        response, scoped = self._run("/t/h1/patients/", self.staff1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(scoped, self.h1)

    def test_platform_user_unscoped(self):
        response, scoped = self._run("/patients/", self.ops)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(scoped)

    def test_lapsed_tenant_cannot_bypass_gate_via_bare_host(self):
        sub = self.h1.subscription
        sub.current_period_end = timezone.now() - timedelta(days=1)
        sub.save(update_fields=["current_period_end"])
        response, _ = self._run("/patients/", self.staff1)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/saas/billing/", response["Location"])

    def test_script_prefix_does_not_leak_between_requests(self):
        from django.urls import get_script_prefix

        from saas.middleware import TenantMiddleware

        seen = []

        def view(request):
            seen.append(get_script_prefix())
            return HttpResponse("ok")

        before = get_script_prefix()
        for path in ("/t/h1/patients/", "/t/h1/patients/"):
            request = self.rf.get(path)
            request.user = self.staff1
            TenantMiddleware(view)(request)
        self.assertEqual(seen, ["/t/h1/", "/t/h1/"])  # not /t/h1/t/h1/
        self.assertEqual(get_script_prefix(), before)

    def test_redirect_keeps_tenant_prefix(self):
        from saas.middleware import TenantMiddleware

        request = self.rf.get("/t/h1/patients/")
        request.user = self.staff1
        response = TenantMiddleware(lambda r: redirect("/accounts/login/"))(request)
        self.assertEqual(response["Location"], "/t/h1/accounts/login/")


class CrossTenantIdTests(TestCase):
    """Generated ids are unique platform-wide; generators must look past the
    current tenant or the INSERT blows up on the unique constraint."""

    def setUp(self):
        self.h1 = Hospital.objects.create(name="H1", subdomain="h1")
        self.h2 = Hospital.objects.create(name="H2", subdomain="h2")
        self.addCleanup(clear_current_hospital)

    def test_invoice_numbers_do_not_collide_across_tenants(self):
        from billing.models import Invoice

        set_current_hospital(self.h1)
        p1 = _make_patient()
        due = timezone.now().date() + timedelta(days=7)
        i1 = Invoice.objects.create(patient=p1, subtotal=100, tax_amount=0, total_amount=100, due_date=due)
        set_current_hospital(self.h2)
        p2 = _make_patient()
        i2 = Invoice.objects.create(patient=p2, subtotal=100, tax_amount=0, total_amount=100, due_date=due)
        self.assertNotEqual(i1.invoice_number, i2.invoice_number)


class OfflineWriteTenantTests(TestCase):
    """Nightly commands / signals run with no current hospital: rows must still
    land in a tenant, or they are invisible to every tenant-scoped query."""

    def setUp(self):
        self.h = Hospital.objects.create(name="H", subdomain="h")
        self.addCleanup(clear_current_hospital)

    def test_child_row_inherits_tenant_from_parent(self):
        from patients.models import PatientWallet, WalletTransaction

        set_current_hospital(self.h)
        patient = _make_patient()
        wallet, _ = PatientWallet.objects.get_or_create(patient=patient)
        clear_current_hospital()  # e.g. a management command

        txn = WalletTransaction.objects.create(
            patient_wallet=wallet, patient=patient, transaction_type="debit",
            amount=100, balance_after=0, description="daily charge",
        )
        self.assertEqual(txn.hospital_id, self.h.id)
        set_current_hospital(self.h)
        self.assertEqual(WalletTransaction.objects.count(), 1)  # tenant sees it


class PerHospitalUniquenessTests(TestCase):
    """Names that used to be globally unique now only have to be unique inside
    one hospital, so two tenants can run identical setups."""

    def setUp(self):
        self.h1 = Hospital.objects.create(name="H1", subdomain="h1")
        self.h2 = Hospital.objects.create(name="H2", subdomain="h2")
        self.addCleanup(clear_current_hospital)

    def test_same_dispensary_and_room_names_in_two_hospitals(self):
        from consultations.models import ConsultingRoom
        from pharmacy.models import BulkStore, Dispensary

        for hospital in (self.h1, self.h2):
            set_current_hospital(hospital)
            Dispensary.objects.create(name="Main Dispensary")
            BulkStore.objects.create(name="Central Store", location="x", capacity=1)
            ConsultingRoom.objects.create(room_number="1", floor="1")
        self.assertEqual(Dispensary.all_objects.filter(name="Main Dispensary").count(), 2)
        self.assertEqual(ConsultingRoom.all_objects.filter(room_number="1").count(), 2)

    def test_duplicate_name_inside_one_hospital_still_rejected(self):
        from django.db import IntegrityError, transaction

        from pharmacy.models import Dispensary

        set_current_hospital(self.h1)
        Dispensary.objects.create(name="Main Dispensary")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Dispensary.objects.create(name="Main Dispensary")

    def test_same_username_in_two_hospitals(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        u1 = User.objects.create_user(
            phone_number="08020000001", username="admin", password="pw", hospital=self.h1
        )
        u2 = User.objects.create_user(
            phone_number="08020000002", username="admin", password="pw", hospital=self.h2
        )
        self.assertNotEqual(u1.pk, u2.pk)

    def test_authorization_codes_may_repeat_across_hospitals(self):
        from nhia.models import AuthorizationCode

        for hospital in (self.h1, self.h2):
            set_current_hospital(hospital)
            AuthorizationCode.objects.create(
                code="AUTH-1", patient=_make_patient(), amount=100,
                expiry_date=timezone.now().date() + timedelta(days=30),
            )
        self.assertEqual(AuthorizationCode.all_objects.filter(code="AUTH-1").count(), 2)


class SignupTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(name="Free", price=0, trial_days=60)
        self.addCleanup(clear_current_hospital)

    def _post(self, **overrides):
        data = {
            "hospital_name": "Acme Clinic",
            "subdomain": "acme",
            "username": "owner",
            "phone_number": "08030000001",
            "password": "S0me-Strong-Pass",
            "plan_id": self.plan.id,
        }
        data.update(overrides)
        return Client().post("/saas/signup/", data)

    def test_weak_password_rejected(self):
        response = self._post(password="1234")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Hospital.objects.filter(subdomain="acme").exists())

    def test_owner_is_created_scoped_and_logged_in(self):
        response = self._post()
        self.assertEqual(response.status_code, 200)
        hospital = Hospital.objects.get(subdomain="acme")
        self.assertEqual(hospital.owner.username, "owner")
        self.assertEqual(hospital.owner.hospital_id, hospital.id)
        self.assertIn("_auth_user_id", response.client.session)

    def test_signup_seeds_a_dispensary_with_an_active_store(self):
        # Without one the tenant has nowhere to hold stock.
        from pharmacy.models import Dispensary

        self._post()
        hospital = Hospital.objects.get(subdomain="acme")
        dispensary = Dispensary.all_objects.get(hospital=hospital)
        self.assertIsNotNone(getattr(dispensary, "active_store", None))
        self.assertEqual(dispensary.active_store.hospital_id, hospital.id)

    def test_same_username_allowed_in_a_second_hospital(self):
        self._post()
        response = self._post(
            hospital_name="Beta Clinic", subdomain="beta", phone_number="08030000002"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Hospital.objects.count(), 2)


class PlanCapTests(TestCase):
    def setUp(self):
        self.h = Hospital.objects.create(name="H", subdomain="h")
        plan = Plan.objects.create(name="Tiny", max_patients=1, max_users=1)
        Subscription.objects.create(
            hospital=self.h, plan=plan, status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        self.addCleanup(clear_current_hospital)

    def test_user_cap_counts_existing_staff(self):
        from django.contrib.auth import get_user_model

        from .models import enforce_limit

        User = get_user_model()
        enforce_limit(self.h, User, "max_users")  # 0 used, cap 1 -> ok
        User.objects.create_user(
            phone_number="08040000001", username="s1", password="pw", hospital=self.h
        )
        with self.assertRaises(ValidationError):
            enforce_limit(self.h, User, "max_users")


class HospitalLogoTests(TestCase):
    """The letterhead context processor must expose the uploaded logo's URL."""

    def _ctx(self, hospital):
        from types import SimpleNamespace

        from .context_processors import hospital_details

        return hospital_details(SimpleNamespace(hospital=hospital))

    def test_logo_url_exposed_and_blank_when_unset(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        # 1x1 GIF - smallest thing ImageField will accept.
        gif = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
            b"\x00\x02\x02D\x01\x00;"
        )
        h = Hospital.objects.create(name="Logo Clinic", subdomain="logoclinic")
        self.assertEqual(self._ctx(h)["hospital_logo"], "")
        self.assertEqual(self._ctx(None)["hospital_logo"], "")

        h.logo.save("mark.gif", SimpleUploadedFile("mark.gif", gif), save=True)
        self.addCleanup(h.logo.delete)
        self.assertIn("hospital_logos/", self._ctx(h)["hospital_logo"])


class BrandingUploadTests(TestCase):
    """The in-app upload page must store the logo on the *request's* tenant."""

    GIF = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
        b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
        b"\x00\x02\x02D\x01\x00;"
    )

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.h = Hospital.objects.create(name="Brand Clinic", subdomain="brand")
        plan = Plan.objects.create(name="Free", price=0)
        Subscription.objects.create(
            hospital=self.h, plan=plan, status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        self.admin = get_user_model().objects.create_user(
            phone_number="08050000001", username="brandadmin", password="pw",
            is_staff=True, hospital=self.h,
        )
        self.addCleanup(clear_current_hospital)

    def _upload(self, client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return client.post(
            "/t/brand/saas/branding/",
            {"only": "logo",
             "logo": SimpleUploadedFile("mark.gif", self.GIF, content_type="image/gif")},
        )

    def test_admin_upload_saves_logo(self):
        c = Client()
        c.force_login(self.admin)
        self.assertEqual(self._upload(c).status_code, 302)
        self.h.refresh_from_db()
        self.addCleanup(self.h.logo.delete)
        self.assertIn("hospital_logos/", self.h.logo.name)

    def _save(self, client, field, value):
        return client.post("/t/brand/saas/branding/", {"only": field, field: value})

    def test_admin_saves_letterhead_details(self):
        c = Client()
        c.force_login(self.admin)
        for field, value in (
            ("address", "12 Ring Road, Ibadan"),
            ("phone", "08012345678"),
            ("email", "info@brand.test"),
        ):
            self.assertEqual(self._save(c, field, value).status_code, 302)
        self.h.refresh_from_db()
        self.assertEqual(self.h.address, "12 Ring Road, Ibadan")
        self.assertEqual(self.h.phone, "08012345678")
        self.assertEqual(self.h.email, "info@brand.test")

    def test_saving_one_field_leaves_the_others(self):
        """Per-field saves: an untouched box must not be wiped."""
        Hospital.objects.filter(pk=self.h.pk).update(phone="08012345678", email="a@b.test")
        c = Client()
        c.force_login(self.admin)
        self.assertEqual(self._save(c, "address", "New Road").status_code, 302)
        self.h.refresh_from_db()
        self.assertEqual(self.h.address, "New Road")
        self.assertEqual(self.h.phone, "08012345678")
        self.assertEqual(self.h.email, "a@b.test")

    def test_bad_phone_rejected(self):
        c = Client()
        c.force_login(self.admin)
        self._save(c, "phone", "call me")
        self.h.refresh_from_db()
        self.assertEqual(self.h.phone, "")

    def test_unknown_field_rejected(self):
        c = Client()
        c.force_login(self.admin)
        resp = self._save(c, "subdomain", "hijacked")
        self.assertEqual(resp.status_code, 400)
        self.h.refresh_from_db()
        self.assertEqual(self.h.subdomain, "brand")

    def test_non_admin_cannot_upload(self):
        from django.contrib.auth import get_user_model

        nurse = get_user_model().objects.create_user(
            phone_number="08050000002", username="nurse", password="pw", hospital=self.h,
        )
        c = Client()
        c.force_login(nurse)
        self.assertEqual(self._upload(c).status_code, 302)  # bounced to login
        self.h.refresh_from_db()
        self.assertFalse(self.h.logo)


class HospitalAdminAddressTests(TestCase):
    """A platform superuser must be able to edit the letterhead in /admin/."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.h = Hospital.objects.create(name="Addr Clinic", subdomain="addr")
        self.su = get_user_model().objects.create_superuser(
            phone_number="08060000001", username="platform", password="pw",
        )
        self.addCleanup(clear_current_hospital)

    def test_superuser_updates_address(self):
        c = Client()
        c.force_login(self.su)
        url = f"/admin/saas/hospital/{self.h.pk}/change/"
        self.assertEqual(c.get(url).status_code, 200)
        resp = c.post(url, {
            "name": self.h.name,
            "subdomain": self.h.subdomain,
            "is_active": "on",
            "address": "12 Ring Road, Ibadan",
            "phone": "08012345678",
            "email": "info@addr.test",
        })
        self.assertEqual(resp.status_code, 302)
        self.h.refresh_from_db()
        self.assertEqual(self.h.address, "12 Ring Road, Ibadan")


class ImportTimeQuerysetScopingTests(TestCase):
    """Querysets built at import time must still be scoped per request.

    A form field declared in a class body, or a DRF viewset's class-level
    `queryset`, is evaluated once at import, when no hospital is current — so
    the plain manager freezes an unscoped queryset for the whole process.
    """

    def setUp(self):
        self.h1 = Hospital.objects.create(name="H1", subdomain="h1")
        self.h2 = Hospital.objects.create(name="H2", subdomain="h2")
        self.addCleanup(clear_current_hospital)
        set_current_hospital(self.h2)
        self.other = _make_patient()  # belongs to h2
        set_current_hospital(self.h1)
        self.mine = _make_patient()

    def test_field_hides_other_tenants_rows(self):
        from laboratory.forms import TestRequestForm

        choices = TestRequestForm().fields["patient"].queryset
        self.assertEqual(list(choices), [self.mine])

    def test_field_rejects_another_tenants_id(self):
        from laboratory.forms import TestRequestForm

        field = TestRequestForm().fields["patient"]
        self.assertEqual(field.clean(str(self.mine.pk)), self.mine)
        with self.assertRaises(ValidationError):
            field.clean(str(self.other.pk))

    def test_api_viewset_mixin_scopes_a_frozen_queryset(self):
        from rest_framework import viewsets

        from .api import TenantScopedQuerysetMixin

        class _ViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
            queryset = Patient.all_objects.all()  # as if built at import time

        self.assertEqual(list(_ViewSet().get_queryset()), [self.mine])

    def test_modelform_fk_field_is_scoped(self):
        """A ModelForm's auto-built FK field is created at import time too."""
        from django import forms

        class _Form(forms.ModelForm):
            class Meta:
                model = Vitals
                fields = ["patient"]

        self.assertEqual(list(_Form().fields["patient"].queryset), [self.mine])


class SuperuserRoamingTests(TestCase):
    """A platform superuser may enter any hospital via /t/<sub>/."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.test import RequestFactory

        self.rf = RequestFactory()
        self.h1 = Hospital.objects.create(name="H1", subdomain="h1")
        self.h2 = Hospital.objects.create(name="H2", subdomain="h2")
        plan = Plan.objects.create(name="Free", price=0)
        for h in (self.h1, self.h2):
            Subscription.objects.create(
                hospital=h, plan=plan, status="active",
                current_period_end=timezone.now() + timedelta(days=30),
            )
        User = get_user_model()
        self.root = User.objects.create_superuser(
            phone_number="08020000001", username="root", password="pw"
        )
        # A superuser whose row carries a hospital must still roam.
        self.stamped = User.objects.create_superuser(
            phone_number="08020000002", username="root2", password="pw",
            hospital=self.h1,
        )
        self.staff = User.objects.create_user(
            phone_number="08020000003", username="s1", password="pw", hospital=self.h1
        )
        self.addCleanup(clear_current_hospital)

    def _run(self, path, user, session=None):
        from saas.current import get_current_hospital
        from saas.middleware import TenantMiddleware

        seen = {}

        def view(request):
            seen["hospital"] = get_current_hospital()
            return HttpResponse("ok")

        request = self.rf.get(path)
        request.user = user
        if session is not None:
            request.session = session
        return TenantMiddleware(view)(request), seen.get("hospital")

    def test_superuser_enters_any_tenant(self):
        for sub, hospital in (("h1", self.h1), ("h2", self.h2)):
            response, scoped = self._run(f"/t/{sub}/patients/", self.root)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(scoped, hospital)

    def test_stamped_superuser_still_roams(self):
        response, scoped = self._run("/t/h2/patients/", self.stamped)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(scoped, self.h2)

    def test_lapsed_subscription_does_not_block_superuser(self):
        sub = self.h2.subscription
        sub.current_period_end = timezone.now() - timedelta(days=1)
        sub.save(update_fields=["current_period_end"])
        response, scoped = self._run("/t/h2/patients/", self.root)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(scoped, self.h2)
        # ...while ordinary staff of that hospital still hit the paywall.
        blocked, _ = self._run("/t/h2/patients/", self.staff)
        self.assertEqual(blocked.status_code, 403)  # wrong hospital for this user

    def test_superuser_is_not_stamped_with_a_tenant(self):
        from django.contrib.auth import get_user_model

        set_current_hospital(self.h1)
        root = get_user_model().objects.create_superuser(
            phone_number="08020000004", username="root3", password="pw"
        )
        self.assertIsNone(root.hospital_id)

    def test_picker_is_superuser_only(self):
        client = Client()
        client.force_login(self.staff)
        self.assertEqual(client.get("/saas/hospitals/").status_code, 302)
        client.force_login(self.root)
        response = client.get("/saas/hospitals/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/t/h2/")

    def test_picker_marks_the_hospital_being_viewed(self):
        client = Client()
        client.force_login(self.root)
        response = client.get("/t/h2/saas/hospitals/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_id"], self.h2.id)
        self.assertContains(response, "current")


    def test_login_sends_a_superuser_to_the_picker(self):
        client = Client()
        for user in (self.root, self.stamped):
            response = client.post(
                "/accounts/login/",
                {"username": user.phone_number, "password": "pw"},
            )
            self.assertRedirects(response, "/saas/hospitals/", fetch_redirect_response=False)
            client.logout()

    def test_login_page_bounces_a_signed_in_superuser_to_the_picker(self):
        client = Client()
        client.force_login(self.root)
        response = client.get("/accounts/login/")
        self.assertRedirects(response, "/saas/hospitals/", fetch_redirect_response=False)

    def test_login_still_sends_tenant_staff_to_the_dashboard(self):
        client = Client()
        response = client.post(
            "/accounts/login/", {"username": self.staff.phone_number, "password": "pw"}
        )
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)


class SuperuserActAsTests(SuperuserRoamingTests):
    """The picked hospital sticks to un-prefixed paths too."""

    def test_picking_a_hospital_scopes_the_bare_host(self):
        from saas.middleware import ACT_AS_KEY

        client = Client()
        client.force_login(self.root)
        response = client.post("/saas/act-as/", {"subdomain": "h2"})
        self.assertRedirects(response, "/t/h2/dashboard/", fetch_redirect_response=False)
        self.assertEqual(client.session[ACT_AS_KEY], self.h2.id)

        _, scoped = self._run("/patients/", self.root, {ACT_AS_KEY: self.h2.id})
        self.assertEqual(scoped, self.h2)

    def test_a_url_prefix_beats_the_session(self):
        from saas.middleware import ACT_AS_KEY

        _, scoped = self._run("/t/h1/patients/", self.root, {ACT_AS_KEY: self.h2.id})
        self.assertEqual(scoped, self.h1)

    def test_platform_view_clears_the_choice(self):
        from saas.middleware import ACT_AS_KEY

        client = Client()
        client.force_login(self.root)
        client.post("/saas/act-as/", {"subdomain": "h2"})
        response = client.post("/saas/act-as/", {"subdomain": ""})
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        self.assertNotIn(ACT_AS_KEY, client.session)

    def test_act_as_is_superuser_only_and_post_only(self):
        client = Client()
        client.force_login(self.staff)
        self.assertEqual(client.post("/saas/act-as/", {"subdomain": "h2"}).status_code, 302)
        client.force_login(self.root)
        self.assertEqual(client.get("/saas/act-as/").status_code, 405)

    def test_unknown_hospital_is_rejected(self):
        from saas.middleware import ACT_AS_KEY

        client = Client()
        client.force_login(self.root)
        response = client.post("/saas/act-as/", {"subdomain": "nope"})
        self.assertRedirects(response, "/saas/hospitals/", fetch_redirect_response=False)
        self.assertNotIn(ACT_AS_KEY, client.session)
