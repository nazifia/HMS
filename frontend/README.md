# HMS Flutter frontend

Thin mobile client over the existing Django server. Every navigable Django URL
is one screen, so all ~970 pages (and the modals they contain) are reachable
without hand-writing a widget per template.

## Run

```bash
python frontend/tool/gen_routes.py            # refresh lib/routes.dart from urls.py
cd frontend
flutter run --dart-define=HMS_BASE_URL=http://10.0.2.2:8000
```

`10.0.2.2` is the Android emulator's alias for the host's `localhost`. On a
real device use the machine's LAN IP and add it to `ALLOWED_HOSTS`.

Regenerate `lib/routes.dart` whenever URLs change; it is generated, not edited.

`android:usesCleartextTraffic="true"` is set for plain-HTTP local development —
drop it once the server is on HTTPS.

## Layout

| File | Purpose |
| --- | --- |
| `lib/main.dart` | Module list, search, param prompt for `<id>` routes |
| `lib/login.dart` | Phone + password against `/api/accounts/login/` |
| `lib/api.dart` | Token client for the REST endpoints |
| `lib/paged_list.dart` | Infinite scroll over DRF pagination |
| `lib/page_screen.dart` | Renders any Django page |
| `lib/appointments/` | Native screens (day list, booking with live slots) |
| `lib/billing/` | Native screens (invoices, payments, cashier summary) |
| `lib/consultations/` | Native screens (queue, consultation, clerking, referrals) |
| `lib/laboratory/` | Native screens (requests, result entry, verification) |
| `lib/patients/` | Native screens (register, search, vitals, history, wallet) |
| `lib/pharmacy/` | Native screens (prescriptions, carts, inventory, transfers, log) |
| `lib/routes.dart` | Generated route table |
| `tool/gen_routes.py` | Generator |

## Native vs WebView

Pharmacy is native — prescriptions, dispensing carts, medications, dispensary
inventory, stock transfers, the dispensing log and procurement — served by
`/pharmacy/api/`. Everything else renders server-side in a WebView.
Sign-in returns a token (native calls) and a `sessionid` cookie that is pushed
into the WebView, so one login covers both. Both are kept in the platform
keystore, so the app reopens signed in; the sign-out button in the module list
clears them.

The full cart flow is native: create from a prescription, pick a dispensary,
edit quantities, substitute a medication, pay from the patient's wallet,
generate the invoice, then dispense in full or per item. The ⋮ menu on a cart
item holds quantity, substitution and removal. Cart rules live once in
`pharmacy/cart_services.py`, shared by the HTML views and the API.

Wallet payment warns and asks before overdrawing. Cash/card payments still
happen at the billing office; `can_dispense` / `dispense_blocked_reason` on the
cart say what it is waiting for.

Transfers cover both directions of stock movement — dispensary to dispensary
and bulk store to dispensary — with approve / reject / execute driven by the
model's own `can_*` guards, so the buttons only appear when the move is legal.

Procurement runs the whole order: draft → submit → approve/reject → receive
delivery (stock lands in the bulk store here, not at approval) → supplier
payment. Items can only be changed while the order is a draft, and each button
appears only when `can_be_approved` / `can_receive_delivery` / `can_be_paid`
says the server would allow it. Rules live once in
`pharmacy/purchase_services.py`.

Medical packs, pack orders, expenses, suppliers and dispensary administration
are native too. Writes on those go through `DjangoModelPermissions`, so reading
stays open to pharmacy staff while creating or editing needs the matching
`add_*` / `change_*` permission — holding `pharmacy.view` is not enough.

Nothing in pharmacy is server-rendered any more; the WebView is still there for
every other module.

Patients is native as well, on `/patients/api/`: register and search the
register, record vitals (BMI computed server-side), add medical history, and
run the wallet — balance, outstanding split between admissions and invoices,
transaction history, and adding funds with an optional "settle outstanding".
Funding asks for `patients.add_wallettransaction` specifically: being able to
edit a patient record is not the same right as moving money.

Laboratory is native on `/laboratory/api/`: raise requests, move them through
sample collection and processing, enter results parameter by parameter (each
flagged normal or abnormal against its reference range) and verify them.
Result entry is refused until payment is settled or NHIA authorisation is in
hand, and the screen says which. Verification asks for
`laboratory.enter_testresults`.

Consultations is native on `/consultations/api/`: the clinic queue (urgent
first, "call in" starts the consultation and links it to the queue entry),
the consultation itself (complaint, symptoms, diagnosis, timestamped notes) and
referrals in both directions. Routing is enforced server-side —
`can_be_accepted_by` decides who may accept a referral, and an NHIA referral
awaiting desk-office authorization cannot be accepted at all. The tile only
offers Accept when the server says this user could.

Clerking notes use the full Nigerian proforma. The 13 sections — their order,
labels and placeholders — are served by
`/consultations/api/clerking-notes/schema/` and rendered from that, so the app
cannot drift out of step with the web form. Notes are written incrementally: a
review visit may fill in only the management plan, and blank sections are
omitted from the request rather than overwriting what an earlier visit wrote.

Appointments is native on `/appointments/api/`: today's list, booking against
the slots the server says are free, status changes, doctor schedules and leave.
The booking rules — double-booking, shift hours, approved leave, past times and
the NHIA authorization code — live in `appointments/services.py` and are the
same ones the web booking form enforces, so the API is not a way around them.
Confirming or completing still requires the consultation fee to be settled.

The doctor picker uses `/api/accounts/staff/?role=doctor` — a read-only lookup
returning names, roles and departments of active staff. `/api/accounts/users/`
is admin-only, so booking screens cannot use it; this endpoint is whitelisted
from the module permission gate (reception and nurses hold no `users.view`) but
still requires a signed-in user.

Billing is native on `/billing/api/`: find an invoice, see its lines and
payment history, and take payment — cash and the rest, or straight from the
patient's wallet (the dialog shows the wallet balance and warns when it falls
short). Payments run through the same `BillingOfficePaymentProcessor` the
billing office pages use, so balance checks and the wallet debit are the shared
ones, and recording one needs `billing.process_payment`. The list header shows
what is owed across the current filter and what has been collected today.

A request is complete only when every test on it has a **verified** result —
entering a result moves it to processing, not completed. That rule lives in
`laboratory/services.py::sync_request_completion` and is the only place that
sets the status; the signals and both result-entry views call it.

To make another module native, add serializers + viewsets under
`<app>/api/`, then a screen under `lib/<app>/`.
