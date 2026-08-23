import hashlib
import hmac
import json
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django import forms

from .middleware import ACT_AS_KEY
from .models import Hospital, Plan, Subscription

User = get_user_model()


@transaction.atomic
def signup(request):
    """Create a hospital + owner user + trial subscription on the default plan."""
    if request.method != "POST":
        plans = Plan.objects.filter(is_active=True)
        return render(request, "saas/signup.html", {"plans": plans})

    name = request.POST.get("hospital_name", "").strip()
    username = request.POST.get("username", "").strip()
    phone_number = request.POST.get("phone_number", "").strip()
    password = request.POST.get("password", "")
    plan_id = request.POST.get("plan_id")

    if not (name and username and phone_number and password and plan_id):
        return HttpResponseBadRequest("Missing required fields.")

    subdomain = slugify(request.POST.get("subdomain") or name)[:63]
    if not subdomain or Hospital.objects.filter(subdomain=subdomain).exists():
        return HttpResponseBadRequest("Subdomain unavailable.")
    if User.objects.filter(phone_number=phone_number).exists():
        return HttpResponseBadRequest("Phone number already registered.")

    plan = Plan.objects.filter(pk=plan_id, is_active=True).first()
    if not plan:
        return HttpResponseBadRequest("Invalid plan.")
    try:
        validate_password(password)
    except ValidationError as exc:
        return HttpResponseBadRequest(" ".join(exc.messages))

    # Owner is the tenant admin: staff + 'admin' profile role, scoped to the
    # hospital (NOT a superuser — superusers are platform-level/cross-tenant).
    # is_staff is this app's "tenant admin" flag (user management, activity
    # views gate on it); TenantMiddleware keeps such users out of /admin/.
    # Hospital first: the owner's username is unique per hospital, so the row
    # needs its tenant set before the INSERT.
    hospital = Hospital.objects.create(name=name, subdomain=subdomain)
    owner = User.objects.create_user(
        phone_number=phone_number,
        username=username,
        password=password,
        is_staff=True,
        hospital=hospital,
    )
    hospital.owner = owner
    hospital.save(update_fields=["owner"])
    # Profile is auto-created by signal; mark it admin so the owner can manage.
    profile = getattr(owner, "profile", None)
    if profile is not None:
        profile.role = "admin"
        profile.save(update_fields=["role"])
    # Pending until a platform superuser approves. Trial clock starts on
    # approval (see Subscription.approve), so seed the period end at now.
    Subscription.objects.create(
        hospital=hospital,
        plan=plan,
        status="pending",
        current_period_end=timezone.now(),
    )
    # Each tenant gets its own department set, lab test catalog, specialties
    # and a dispensary (without one there is nowhere to hold stock).
    from accounts.department_seed import seed_departments_for
    from doctors.specialty_seed import seed_specialties_for
    from laboratory.lab_catalog_seed import seed_lab_catalog_for
    from pharmacy.dispensary_seed import seed_dispensary_for

    seed_departments_for(hospital)
    seed_lab_catalog_for(hospital)
    seed_specialties_for(hospital)
    seed_dispensary_for(hospital)
    # Log the owner straight in — they just proved the password. Backend is
    # explicit because several are configured.
    login(request, owner, backend="accounts.backends.PhoneNumberBackend")
    return render(request, "saas/signup_done.html", {"hospital": hospital})


def billing(request):
    """Shown when a tenant's subscription is lapsed or to manage the plan."""
    hospital = getattr(request, "hospital", None)
    sub = getattr(hospital, "subscription", None) if hospital else None
    return render(
        request,
        "saas/billing.html",
        {
            "hospital": hospital,
            "subscription": sub,
            "plans": Plan.objects.filter(is_active=True),
            # No Paystack key (e.g. PythonAnywhere free tier blocks outbound to
            # api.paystack.co) → fall back to manual superuser activation.
            "paystack_enabled": bool(getattr(settings, "PAYSTACK_SECRET_KEY", "")),
        },
    )


@require_POST
def request_activation(request):
    """Free-tier fallback: tenant asks a platform superuser to activate/renew.

    Puts a lapsed (or never-approved) subscription back into 'pending' so it
    surfaces in the admin approval queue. Superuser then approves/activates via
    the existing SubscriptionAdmin actions. No Paystack call.
    """
    hospital = getattr(request, "hospital", None)
    sub = getattr(hospital, "subscription", None) if hospital else None
    if sub is None:
        messages.error(request, "No subscription to activate. Contact support.")
    elif sub.status == "pending":
        messages.info(request, "Already awaiting approval. We'll review it shortly.")
    elif sub.is_current():
        messages.info(request, "Your subscription is already active.")
    else:
        sub.status = "pending"
        sub.save(update_fields=["status"])
        messages.success(request, "Request sent. Our team will review and activate your account.")
    return redirect(reverse("saas:billing"))


@require_POST
def checkout(request):
    """Kick off a Paystack payment for the current tenant's plan.

    Initializes a transaction server-side and redirects to Paystack's hosted
    page. The webhook (paystack_webhook) flips the subscription to active once
    payment lands. ponytail: stdlib urllib, no requests dependency.
    """
    hospital = getattr(request, "hospital", None)
    sub = getattr(hospital, "subscription", None) if hospital else None
    secret = getattr(settings, "PAYSTACK_SECRET_KEY", "")
    if not (hospital and sub and secret):
        messages.error(request, "Online payment is not configured. Contact support.")
        return redirect(reverse("saas:billing"))

    owner = hospital.owner
    email = (getattr(owner, "email", "") or f"{hospital.subdomain}@example.com")
    payload = json.dumps({
        "email": email,
        "amount": int(sub.plan.price * 100),  # kobo
        "callback_url": request.build_absolute_uri(reverse("saas:billing")),
        "metadata": {"hospital_id": hospital.id, "subdomain": hospital.subdomain},
    }).encode()
    req = urllib.request.Request(
        "https://api.paystack.co/transaction/initialize",
        data=payload,
        headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
        url = body.get("data", {}).get("authorization_url")
    except Exception:
        url = None
    if not url:
        messages.error(request, "Could not start payment. Try again later.")
        return redirect(reverse("saas:billing"))
    return redirect(url)


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Update subscription state from Paystack events. Verifies HMAC signature."""
    secret = getattr(settings, "PAYSTACK_SECRET_KEY", "")
    signature = request.headers.get("x-paystack-signature", "")
    expected = hmac.new(secret.encode(), request.body, hashlib.sha512).hexdigest()
    if not secret or not hmac.compare_digest(expected, signature):
        return HttpResponse(status=401)

    event = json.loads(request.body or "{}")
    etype = event.get("event", "")
    data = event.get("data", {})
    sub_code = data.get("subscription_code") or data.get("subscription", {}).get("subscription_code", "")

    sub = Subscription.objects.filter(paystack_subscription_code=sub_code).first() if sub_code else None
    if sub is None:
        return JsonResponse({"ok": True, "ignored": True})

    if etype in ("charge.success", "subscription.create", "invoice.update"):
        sub.status = "active"
        period = data.get("next_payment_date") or data.get("paid_at")
        if period:
            sub.current_period_end = timezone.datetime.fromisoformat(period.replace("Z", "+00:00"))
    elif etype in ("subscription.disable", "subscription.not_renew"):
        sub.status = "canceled"
    elif etype == "invoice.payment_failed":
        sub.status = "past_due"
    sub.save()
    return JsonResponse({"ok": True})


BRANDING_FIELDS = ("logo", "address", "phone", "email")


class BrandingForm(forms.ModelForm):
    """The letterhead block: logo plus the address/phone/email printed under it.

    `only` trims the form to a single field so each Save button writes just
    that one — a blank box elsewhere on the page can't wipe a stored value.
    """

    phone = forms.CharField(
        required=False,
        max_length=30,
        validators=[RegexValidator(r"^[0-9+()\-\s]{7,30}$", "Use digits and + - ( ) only, 7-30 characters.")],
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Hospital
        fields = list(BRANDING_FIELDS)
        widgets = {
            "logo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, only=None, **kwargs):
        super().__init__(*args, **kwargs)
        if only:
            for name in [f for f in self.fields if f != only]:
                del self.fields[name]


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def branding(request):
    """Let a tenant admin set the letterhead heading every receipt/printout."""
    hospital = getattr(request, "hospital", None)
    if hospital is None:
        messages.error(request, "No tenant in context. Open this page from your hospital subdomain.")
        return render(request, "saas/branding.html", {"hospital": None})

    if request.method == "POST":
        only = request.POST.get("only")
        if only not in BRANDING_FIELDS:
            return HttpResponseBadRequest("Unknown branding field.")
        form = BrandingForm(request.POST, request.FILES, instance=hospital, only=only)
        if form.is_valid():
            form.save()
            messages.success(request, f"{form.fields[only].label or only} updated.")
        else:
            # ponytail: report the error and re-render blank rather than
            # threading a part-bound form through the per-field template loop.
            messages.error(request, form.errors.get(only, form.errors).as_text().lstrip("* "))
        return redirect(reverse("saas:branding"))

    return render(request, "saas/branding.html", {"hospital": hospital, "form": BrandingForm(instance=hospital)})


@user_passes_test(lambda u: u.is_superuser)
def hospitals(request):
    """Tenant picker for platform superusers: one link per hospital.

    A superuser has no hospital of their own, so the bare host shows them every
    tenant's rows mixed together. Entering a tenant through /t/<sub>/ pins the
    request to that hospital, which is what "log in to a hospital" means here.
    """
    rows = (
        Hospital.objects.select_related("subscription__plan")
        .order_by("-is_active", "name")
    )
    current = getattr(request, "hospital", None)
    return render(
        request,
        "saas/hospitals.html",
        {"hospitals": rows, "current_id": current.id if current else None},
    )


@require_POST
@user_passes_test(lambda u: u.is_superuser)
def act_as(request):
    """Enter a hospital from the picker (blank subdomain leaves them all).

    Entering both sends the superuser to /t/<sub>/, which scopes the request by
    URL, and remembers the choice in the session so un-prefixed paths — links
    built without the tenant prefix, /dashboard/ typed by hand — scope to the
    same hospital instead of falling open across every tenant.
    """
    sub = request.POST.get("subdomain", "").strip().lower()
    if not sub:
        request.session.pop(ACT_AS_KEY, None)
        return redirect("/dashboard/")
    hospital = Hospital.objects.filter(subdomain=sub, is_active=True).first()
    if hospital is None:
        messages.error(request, "No such hospital.")
        return redirect("/saas/hospitals/")
    request.session[ACT_AS_KEY] = hospital.id
    return redirect(f"/t/{hospital.subdomain}/dashboard/")
