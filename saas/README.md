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

## Config

Set `PAYSTACK_SECRET_KEY` in `.env` for webhook verification. Point Paystack
webhooks at `https://<base>/saas/webhook/paystack/`.

## Not built yet (add when needed)

- Per-tenant unique constraints (e.g. `patient_id` is still globally unique).
- Tenant-aware login routing (which subdomain a user lands on).
- Paystack checkout initiation UI (only the webhook + trial signup exist).
- Async/ASGI support (swap `current.py` thread-local for `contextvars`).
- Retrofitting the other ~35 apps' models (mechanical; follow the pattern above).
```
