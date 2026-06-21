import hashlib
import hmac
import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
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
    password = request.POST.get("password", "")
    plan_id = request.POST.get("plan_id")

    if not (name and username and password and plan_id):
        return HttpResponseBadRequest("Missing required fields.")

    subdomain = slugify(request.POST.get("subdomain") or name)[:63]
    if not subdomain or Hospital.objects.filter(subdomain=subdomain).exists():
        return HttpResponseBadRequest("Subdomain unavailable.")
    if User.objects.filter(username=username).exists():
        return HttpResponseBadRequest("Username taken.")

    plan = Plan.objects.filter(pk=plan_id, is_active=True).first()
    if not plan:
        return HttpResponseBadRequest("Invalid plan.")

    owner = User.objects.create_user(username=username, password=password)
    hospital = Hospital.objects.create(name=name, subdomain=subdomain, owner=owner)
    owner.hospital = hospital
    owner.save(update_fields=["hospital"])
    Subscription.objects.create(
        hospital=hospital,
        plan=plan,
        status="trialing",
        current_period_end=timezone.now() + timedelta(days=plan.trial_days),
    )
    # Each tenant gets its own department set.
    from accounts.department_seed import seed_departments_for

    seed_departments_for(hospital)
    return render(request, "saas/signup_done.html", {"hospital": hospital})


def billing(request):
    """Shown when a tenant's subscription is lapsed or to manage the plan."""
    return render(request, "saas/billing.html", {"hospital": getattr(request, "hospital", None)})


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
