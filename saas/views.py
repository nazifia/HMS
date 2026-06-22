import hashlib
import hmac
import json
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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
    if User.objects.filter(username=username).exists():
        return HttpResponseBadRequest("Username taken.")
    if User.objects.filter(phone_number=phone_number).exists():
        return HttpResponseBadRequest("Phone number already registered.")

    plan = Plan.objects.filter(pk=plan_id, is_active=True).first()
    if not plan:
        return HttpResponseBadRequest("Invalid plan.")

    # Owner is the tenant admin: staff + 'admin' profile role, scoped to the
    # hospital (NOT a superuser — superusers are platform-level/cross-tenant).
    owner = User.objects.create_user(
        phone_number=phone_number, username=username, password=password, is_staff=True
    )
    hospital = Hospital.objects.create(name=name, subdomain=subdomain, owner=owner)
    owner.hospital = hospital
    owner.save(update_fields=["hospital"])
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
    # Each tenant gets its own department set.
    from accounts.department_seed import seed_departments_for

    seed_departments_for(hospital)
    return render(request, "saas/signup_done.html", {"hospital": hospital})


def billing(request):
    """Shown when a tenant's subscription is lapsed or to manage the plan."""
    hospital = getattr(request, "hospital", None)
    sub = getattr(hospital, "subscription", None) if hospital else None
    return render(
        request,
        "saas/billing.html",
        {"hospital": hospital, "subscription": sub, "plans": Plan.objects.filter(is_active=True)},
    )


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
