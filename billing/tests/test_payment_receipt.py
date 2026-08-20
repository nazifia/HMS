"""One receipt view now serves every service that takes payment.

Guards the two things that can silently break: the line items a receipt is
built from, and the thermal (roll) variant of the same URL.
"""
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from billing.models import Invoice, InvoiceItem, Payment, Service
from patients.models import Patient


class PaymentReceiptTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone_number="9100", username="cashier", password="pw"
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename="print_paymentreceipt")
        )
        self.client.force_login(self.user)

        patient = Patient.objects.create(
            first_name="Rec", last_name="Eipt", date_of_birth="1990-01-01",
            gender="M", address="1 St", city="Town", state="ST", patient_id="P960",
        )
        service = Service.objects.create(name="Malaria Test", price=Decimal("500.00"))
        self.invoice = Invoice.objects.create(
            patient=patient,
            source_app="laboratory",
            invoice_number="RCPTEST1",
            invoice_date=timezone.now(),
            due_date=timezone.now().date(),
            subtotal=Decimal("500.00"),
            tax_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
        )
        InvoiceItem.objects.create(
            invoice=self.invoice, service=service, description="Malaria Test",
            quantity=1, unit_price=Decimal("500.00"), tax_percentage=Decimal("0.00"),
        )
        self.payment = Payment.objects.create(
            invoice=self.invoice, amount=Decimal("500.00"),
            payment_method="cash", payment_date=timezone.now(), received_by=self.user,
        )
        self.url = reverse("billing:payment_receipt", args=[self.payment.id])

    def test_a4_receipt_shows_service_line_and_amount(self):
        body = self.client.get(self.url).content.decode()
        self.assertIn("Malaria Test", body)
        self.assertIn("LAB-%d" % self.payment.id, body)
        self.assertIn("500.00", body)

    def test_thermal_receipt_carries_the_escpos_text_body(self):
        body = self.client.get(self.url, {"format": "thermal"}).content.decode()
        self.assertIn('id="receipt-text"', body)
        self.assertIn("PAYMENT RECEIPT", body)
        self.assertIn("Malaria Test", body)

    def test_staff_without_the_permission_cannot_print(self):
        nurse = CustomUser.objects.create_user(
            phone_number="9102", username="nurse", password="pw"
        )
        self.client.force_login(nurse)
        self.assertEqual(self.client.get(self.url).status_code, 403)


class ReceiptUrlAccessControlTest(TestCase):
    """Strict access control maps /billing/* to billing.view, which pharmacy,
    lab and front-desk staff do not hold - the receipt URL must be the
    exception, or printing breaks for everyone outside the billing office."""

    def test_receipt_url_asks_for_the_print_permission_not_billing_view(self):
        from accounts.strict_access_control import StrictAccessControlMiddleware

        middleware = StrictAccessControlMiddleware(lambda request: None)
        request = RequestFactory().get("/billing/payments/5/receipt/")
        self.assertEqual(
            middleware._get_required_permission(request), "billing.print_receipt"
        )
