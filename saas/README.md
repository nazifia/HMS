# SaaS / Multi-Tenant Engine

Shared-database, row-level tenancy. One `Hospital` = one tenant. Every
tenant-owned row carries a `hospital` FK and is auto-filtered per request.

## Pieces

| File | Role |
|------|------|
| `models.py` | `Hospital`, `Plan`, `Subscription`; `TenantModel` mixin, `TenantManager`, `enforce_limit()` |
| `current.py` | thread-local current hospital |
| `middleware.py` | subdomain → hospital, sets current, gates lapsed subs to `/saas/billing` |
| `views.py` | `signup`, `billing`, Paystack `webhook` (HMAC-verified) |

## Routing

`hospitalname.yourapp.com` → tenant `hospitalname`. Base/`www`/`app` domains
have no tenant (marketing + `/saas/signup/`). Needs wildcard DNS in prod and
`*.yourdomain` in `ALLOWED_HOSTS`. Local: edit hosts file or use
`h1.localhost:8000` (note: 2-part hosts resolve to no tenant — use a real
3-part host like `h1.lvh.me`).

## Making a model tenant-scoped (rollout pattern)

`Patient` is the worked example. For every other tenant-owned model:

```python
from saas.models import TenantModel

class Thing(TenantModel):   # was models.Model
    ...
```

Then `makemigrations`. Gives it: `hospital` FK, tenant-scoped `objects`,
unscoped `all_objects`, auto-stamp on save.

- Query in a request → already scoped. `Thing.objects.all()` = this tenant only.
- Need cross-tenant (admin/ops/migrations) → `Thing.all_objects`.
- Enforce a plan cap before create → `enforce_limit(request.hospital, Thing, "max_patients")`.

### Backfill existing rows

`hospital` is nullable so the migration doesn't block. After deploy, assign a
hospital to legacy rows, e.g. `Thing.all_objects.filter(hospital__isnull=True).update(hospital=h)`,
then tighten to `null=False` if desired.

## Billing flow

1. Signup (`/saas/signup/`) → hospital + trial subscription + admin owner.
2. Trial lapses → middleware redirects tenant to `/saas/billing/`.
3. `Pay with Paystack` (`/saas/checkout/`) → server-side `transaction/initialize`
   (stdlib `urllib`, no `requests` dep) → redirect to Paystack hosted page.
4. Paystack fires webhook → `paystack_webhook` flips subscription to `active`.

Plans (`Starter`/`Clinic`/`Hospital`) are seeded by migration `0002_seed_plans`.

## Config

Set `PAYSTACK_SECRET_KEY` in `.env` for webhook verification AND checkout init.
Point Paystack webhooks at `https://<base>/saas/webhook/paystack/`.

## Not built yet (add when needed)

- Per-tenant unique constraints (e.g. `patient_id` is still globally unique).
- Tenant-aware login routing (which subdomain a user lands on).
- Recurring Paystack subscriptions (checkout does a one-off charge; webhook also
  handles `subscription.*` events if you create plans with `paystack_plan_code`).
- Async/ASGI support (swap `current.py` thread-local for `contextvars`).
- Retrofitting the other ~35 apps' models (mechanical; follow the pattern above).
```
