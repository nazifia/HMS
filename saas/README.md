# SaaS / Multi-Tenant Engine

Shared-database, row-level tenancy. One `Hospital` = one tenant. Every
tenant-owned row carries a `hospital` FK and is auto-filtered per request.

## Pieces

| File | Role |
|------|------|
| `models.py` | `Hospital`, `Plan`, `Subscription`; `TenantModel` mixin, `TenantManager`, `enforce_limit()` |
| `current.py` | thread-local current hospital |
| `middleware.py` | `/t/<sub>/` path → hospital, sets current, gates lapsed subs to `/saas/billing` |
| `views.py` | `signup`, `billing`, Paystack `webhook` (HMAC-verified) |

## Routing

**Path-based**: `yourapp.com/t/<sub>/...` → tenant `<sub>`. Bare host (no `/t/`
prefix) has no tenant — that's marketing + `/saas/signup/` + the app shell.

The middleware strips `/t/<sub>` from `request.path_info` before URL resolving,
then pushes it onto Django's script prefix, so `reverse()` and `{% url %}` keep
emitting tenant-scoped links (`/t/<sub>/...`) with zero changes to `urls.py`.

One host, one cert — works on free PythonAnywhere and any plain host. No
wildcard DNS, no `*.yourdomain` in `ALLOWED_HOSTS`, no hosts-file edits locally.

**Why not subdomains** (`sub.yourapp.com`): PythonAnywhere serves no valid TLS
cert for nested subdomains (`sub.user.pythonanywhere.com`), and HSTS
`includeSubdomains` hard-blocks the certless host. Subdomain tenancy needs a
custom domain with wildcard TLS — switch back only then (and re-enable
`SECURE_HSTS_INCLUDE_SUBDOMAINS`).

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

## Manual activation fallback (free tier / no Paystack)

Hosts like PythonAnywhere free tier block outbound to `api.paystack.co`, so the
Paystack checkout call fails. When `PAYSTACK_SECRET_KEY` is unset the billing
page swaps the "Pay with Paystack" button for **Request activation**:

1. New signup → subscription `pending` → superuser approves in admin (no payment).
2. Lapsed tenant → billing → `Request activation` (`/saas/request-activation/`)
   flips the sub back to `pending` → superuser approves/activates.

Approval is the existing `SubscriptionAdmin` actions (superuser-only):
`Approve → start trial`, `Approve → activate (skip trial)`, `Reject`. No
outbound calls anywhere in this path. Set `PAYSTACK_SECRET_KEY` to switch the
button back to live Paystack checkout automatically.

`/saas/request-activation/` is in the middleware's lapsed-allowed list so a
lapsed tenant can reach it without being bounced to billing.

## Config

Set `PAYSTACK_SECRET_KEY` in `.env` for webhook verification AND checkout init.
Point Paystack webhooks at `https://<base>/saas/webhook/paystack/`. Leave it
unset to use the manual activation fallback above.

## Not built yet (add when needed)

- Per-tenant unique constraints (e.g. `patient_id` is still globally unique).
- Tenant-aware login routing (which `/t/<sub>/` a user lands on; session cookie is shared across all tenants on one host).
- Recurring Paystack subscriptions (checkout does a one-off charge; webhook also
  handles `subscription.*` events if you create plans with `paystack_plan_code`).
- Async/ASGI support (swap `current.py` thread-local for `contextvars`).
- Retrofitting the other ~35 apps' models (mechanical; follow the pattern above).
```
