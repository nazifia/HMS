from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .current import get_current_hospital


class Plan(models.Model):
    """A subscription tier offered to hospitals."""

    INTERVAL_CHOICES = (("monthly", "Monthly"), ("yearly", "Yearly"))

    name = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default="monthly")
    # 0 = unlimited
    max_users = models.PositiveIntegerField(default=0)
    max_patients = models.PositiveIntegerField(default=0)
    trial_days = models.PositiveIntegerField(default=14)
    paystack_plan_code = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (₦{self.price}/{self.interval})"


class Hospital(models.Model):
    """The tenant. Every tenant-scoped row points here."""

    name = models.CharField(max_length=200)
    subdomain = models.SlugField(max_length=63, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_hospitals",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def plan(self):
        sub = getattr(self, "subscription", None)
        return sub.plan if sub else None


class Subscription(models.Model):
    STATUS_CHOICES = (
        ("trialing", "Trialing"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
    )

    hospital = models.OneToOneField(
        Hospital, on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="trialing")
    current_period_end = models.DateTimeField()
    paystack_subscription_code = models.CharField(max_length=100, blank=True)
    paystack_customer_code = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.hospital} — {self.plan.name} ({self.status})"

    def is_current(self):
        return (
            self.status in ("trialing", "active")
            and self.current_period_end >= timezone.now()
        )


# --- Tenant scoping engine -------------------------------------------------

class TenantManager(models.Manager):
    """Auto-filters every query to the current request's hospital.

    ponytail: no current hospital (migrations, shell, mgmt commands, superuser
    on base domain) => returns ALL rows unfiltered. That's the escape hatch for
    admin/ops. App views always run behind TenantMiddleware, so they get scoped.
    Use `Model.all_objects` to bypass deliberately.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        hospital = get_current_hospital()
        if hospital is not None:
            return qs.filter(hospital=hospital)
        return qs


class TenantModel(models.Model):
    """Mixin: gives a model a hospital FK + auto-scoping + auto-stamp on save."""

    # ponytail: nullable so it can be added to existing tables without a data
    # backfill blocking the migration. Backfill, then tighten to null=False.
    # ponytail: related_name='+' disables the Hospital reverse accessor so the
    # generic FK doesn't clash when two apps define same-named models. Query via
    # Thing.objects (already tenant-scoped), not hospital.thing_set.
    hospital = models.ForeignKey(
        Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )

    objects = TenantManager()
    all_objects = models.Manager()  # unscoped escape hatch

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.hospital_id is None:
            current = get_current_hospital()
            if current is not None:
                self.hospital = current
        super().save(*args, **kwargs)


def enforce_limit(hospital, model, count_attr):
    """Raise if adding one more row would exceed the plan cap (0 = unlimited).

    `count_attr` is the Plan field, e.g. 'max_patients'. Call before creating.
    """
    plan = hospital.plan if hospital else None
    if not plan:
        return
    cap = getattr(plan, count_attr, 0)
    if cap and model.all_objects.filter(hospital=hospital).count() >= cap:
        raise ValidationError(
            f"Plan '{plan.name}' limit reached for {model.__name__} ({cap})."
        )
