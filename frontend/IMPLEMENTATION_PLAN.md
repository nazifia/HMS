# HMS Mobile — Implementation Plan

How the Flutter client gets from "six modules native, the rest in a WebView" to
a complete mobile application, and the working rules that got it this far.

Written against the code as it stands: Django 4.2.26, DRF 3.15.1, Flutter with
`webview_flutter`, `http` and `flutter_secure_storage`.

---

## 1. Where things stand

The app opens on a module list. Native screens sit at the top; every other
Django page is reachable through a WebView driven by a generated route table
(972 entries from `tool/gen_routes.py`).

| Module | API | Native screens | API tests |
| --- | --- | --- | --- |
| Pharmacy | `/pharmacy/api/` | prescriptions, carts, inventory, transfers, dispensing log, procurement, packs, expenses, dispensary admin | 37 |
| Laboratory | `/laboratory/api/` | requests, result entry, verification | 17 |
| Appointments | `/appointments/api/` | day list, booking with live slots | 15 |
| Consultations | `/consultations/api/` | queue, consultation, clerking, referrals | 14 |
| Billing | `/billing/api/` | invoices, payments, cashier summary | 12 |
| Patients | `/patients/api/` | register, search, vitals, history, wallet | 11 |
| Inpatient | `/inpatient/api/` | ward board, bed map, admissions, transfer, discharge, charges, ward round | 22 |
| NHIA / desk office | `/nhia/api/` | authorization queue, issue, verify, cancel | 19 |
| Radiology | `/radiology/api/` | orders, reporting with uploads, verification, study viewer | 17 |
| Theatre | `/theatre/api/` | day list, booking, team, checklist, post-op, equipment | 19 |
| Specialty ×18 | `/api/specialty/` | one generic record API, schema-driven form | 13 |
| Accounts | `/api/accounts/` | login, staff lookup | 12 |
| Core | `/api/dashboard/` | home dashboard | 13 |

Everything else — reporting, HR — is server-rendered in the WebView and works
today. The plan below replaces that, in the order the wards and clinics would
feel it.

---

## 2. The pattern

Every module so far followed the same six steps. Deviating from it is what
creates drift between the web app and the mobile app, so treat it as the
default.

**1. Read the models first.** Look for methods that already encode the rules —
`can_be_approved()`, `can_complete_dispensing()`, `is_payment_verified()`,
`can_be_accepted_by()`. Where they exist, the API calls them and adds nothing.

**2. Find where the rules actually live.** If they are inside a view or a form
(`AppointmentForm.clean`, `create_cart_from_prescription`), extract them into
`<app>/services.py` and **rewire the existing view onto the extraction**. The
existing tests passing is what makes that safe. Never write a second copy for
the API — a mobile client that can double-book or dispense unpaid stock is
worse than no mobile client.

**3. Serializers carry decisions, not just fields.** Expose the server's own
answers — `can_dispense`, `payment_verified`, `blocked_reason`, `can_accept` —
so the app only offers actions the server would accept, and can say why when it
would not.

**4. Permissions.** `DjangoModelPermissions` for ordinary writes. Workflow
actions get `get_permissions()` exemption plus an explicit check, because DRF
maps every POST to `add_<model>` and that is usually the wrong question:
"may this doctor complete their own consultation" is not "may they add one".
Money and clinical sign-off get their own permission —
`billing.process_payment`, `patients.add_wallettransaction`,
`laboratory.enter_testresults`.

**5. Tests that fail if a rule breaks.** Not CRUD coverage. Each module's file
pins the refusals: overpayment, double-booking, results before payment,
accepting a referral routed elsewhere, editing a locked invoice.

**6. Flutter last**, once the API answers the real questions. Screens stay thin:
lists via `PagedList`, errors via `ApiException.message`, nothing recomputed
client-side that the server already decided.

Two rules that keep biting if forgotten:

- **Blank means "not recorded", not zero.** Vitals, clerking sections and lab
  parameters omit empty fields from the request rather than sending `""`.
- **Two gates sit in front of every API call** — `StrictAccessControlMiddleware`
  (HMS role permissions) and any module middleware (`PharmacyAccessMiddleware`).
  Both now answer API callers in JSON; a new module's endpoints must be reachable
  by the roles that will use them, which is worth checking before writing screens.

---

## 3. Phase 1 — Inpatient (done)

**Extracted into `inpatient/services.py`**, with the HTML views, the
`daily_admission_charges` command and the Celery task rewired onto it:
`admit_patient`, `discharge_patient`, `transfer_patient`,
`charge_admission_for_date`. The arithmetic stayed on `Admission`
(`get_duration`, `get_total_cost`, `get_outstanding_admission_cost`,
`get_total_wallet_impact`) — the service owns the workflow around it.

**Endpoints** under `/inpatient/api/`: `wards/` (live bed counts),
`beds/?ward=&free=true`, `admissions/` (POST admits) with `discharge/`,
`transfer/` and `charges/`, plus `rounds/`, `nursing-notes/`,
`clinical-records/` and `medications/` filtered by `?admission=`.

**Screens**: `lib/inpatient/wards.dart` (ward board → bed map),
`admissions.dart` (list, detail with charges, transfer, discharge) and
`ward_round.dart` (rounds and nursing notes, entry built for the bedside).

**What the 22 tests pin**: an occupied or out-of-service bed refuses an
admission and no invoice is written; a patient cannot be admitted twice;
discharge frees the bed, stamps the date and refuses a second time; a transfer
writes `BedTransfer` always and `WardTransfer` only when the ward changes, and
refuses an occupied target without moving the patient; the daily charge lands
once per date and never after discharge; discharge needs
`inpatient.discharge_patient`.

**Three live bugs came out of the extraction** (see §10).

---

## 4. Phase 2 — Radiology (done)

**Extracted into `radiology/services.py`**, with the HTML views and the
enhanced result pages rewired onto it: `assert_can_add_result`, `update_status`,
`save_result`, `verify_result`, `finalize_result`. `RadiologyOrder` gained
`is_payment_verified()`, the same shape as `TestRequest.is_payment_verified` —
the two modules answer the same question and now answer it the same way.

**Endpoints** under `/radiology/api/`: `tests/`, `categories/`, `orders/` +
`set-status/` and `enter-result/` (JSON or multipart), `results/` + `verify/`
and `finalize/`.

**Screens**: `lib/radiology/radiology.dart` (order list with status filters,
order detail with the report card, study viewer with pinch-to-zoom) and
`report_entry.dart`. `Api.postMultipart` carries file uploads — laboratory
inherits it for `TestResult.result_file`.

**What the 17 tests pin**: reporting is blocked until payment; a paid invoice
unlocks it; findings and impression are required; a second report edits the
first rather than duplicating (the FK is OneToOne); an uploaded study comes
back with a URL; verifying records who and when and completes the order; a
signed-off report cannot be edited; finalize requires verification first;
sign-off needs `radiology.change_radiologyresult`.

**Not built**: picking a file *from the phone*. The transport and the server
side are done and tested; attaching a study from the camera or gallery needs an
image-picker plugin and its platform permissions, which is a plugin away and
marked with a `ponytail:` note in `report_entry.dart`.

---

## 5. Phase 3 — Theatre (done)

**Extracted into `theatre/services.py`**, with `SurgeryForm` and
`SurgeryCreateView` rewired onto it: `theatre_conflicts` /
`assert_theatre_free` (double-booking, previously only inside the form),
`finalize_scheduling` (invoice, NHIA rule, authorization code — previously 130
lines inside `form_valid`), `schedule_surgery`, `update_status`,
`assign_team_member`, `save_checklist`, `add_post_op_note`,
`record_equipment_usage`, `theatre_day`.

**Endpoints** under `/theatre/api/`: `theatres/` + `today/?date=`,
`surgery-types/`, `equipment/`, `surgeries/` + `check-slot/`, `set-status/`,
`team/`, `checklist/` (GET and POST), `post-op-note/`, `post-op-notes/`,
`equipment/`.

**Screens**: `lib/theatre/theatre.dart` (the day's list with a date stepper,
the full surgery list, surgery detail with team, equipment and packs) and
`checklist.dart` — a real checklist with tick boxes and a count of what is
outstanding, not a text field.

**Packs**: not duplicated. `PackOrder.surgery` already exists, so the surgery
serializer exposes the linked orders and the pharmacy screens still own the
pack workflow.

**What the 19 tests pin**: a theatre cannot be double-booked but the same slot
in another theatre is fine; `check-slot` answers before the form is submitted;
an NHIA surgery is billed ₦0 and sits at *pending* until a code arrives, and
cannot start without one; a code for another patient is refused; a completed
surgery cannot be reopened; a team member is added once per role; the checklist
reports what is still outstanding and closes once the surgery is done; a
post-operative note is refused before the surgery starts; equipment usage is
capped by what the theatre holds.

---

## 6. Phase 4 — NHIA and desk office (done)

**Extracted into `nhia/services.py`**, with the desk-office pages rewired onto
it: `issue_code`, `authorize`, `pending_queryset`/`pending_counts`,
`cancel_code`, `expire_stale_codes`, `referral_estimated_cost`. Six modules
carry the same three fields (`requires_authorization`, `authorization_status`,
`authorization_code`), so `AUTHORIZABLE` names them once and one `authorize()`
serves all six instead of a view apiece.

**Endpoints** under `/nhia/api/`: `authorization-codes/` (list, issue,
`<id>/cancel/`, `verify/?code=&service_type=`), `nhia-patients/?search=`,
`pending/?kind=&patient=` (the merged queue with per-kind counts) and
`pending/<kind>/<id>/authorize/`.

**Screens**: `lib/nhia/authorization.dart` — the waiting queue with per-module
filters and an authorize action, the issued-code list with cancellation, and a
verify dialog for a code the patient is holding.

**What the 19 tests pin**: a non-NHIA patient cannot be given a code; a manual
code must be unique; a zero amount is refused; verify reports *why* a code
cannot be used (wrong service type, expired) and retires stale codes; only
active codes cancel; authorizing attaches the code and clears the queue;
authorizing twice or authorizing something that does not need it is refused;
amounts default to what the item is worth (referral estimate, lab tests
ordered); issuing needs `nhia.add_authorizationcode`.

**Behaviour change worth knowing**: a code covering ₦0 is now refused. The
pages previously defaulted the amount to `0.00`, so a code could be issued that
authorized nothing.

---

## 7. Phase 5 — Specialty record modules (done)

**The assessment came out in favour of the generic route.** All eighteen are
`<X>Record` + `<X>ClinicalNote`, and every record carries patient, a doctor,
a visit date, a block of specialty fields, diagnosis, treatment plan,
follow-up and authorization. So: no hand-rolled APIs, no eighteen serializers.

**Machinery**: `core/specialty_api.py` holds the registry (`SPECIALTY_MODULES`)
and derives each module's field list from the model — name, label, type,
required, help text, choices. `core/api/specialty_views.py` builds the
serializer from the model at request time.

**Endpoints** under `/api/specialty/`: `modules/`, `<kind>/schema/`,
`<kind>/records/`, `<kind>/records/<id>/`,
`<kind>/records/<id>/clinical-notes/`. Adding a nineteenth specialty is one
line in `SPECIALTY_MODULES`.

**Screens**: `lib/specialty/specialty.dart` (module list, record list per
module) and `record_form.dart` — one form that renders any of the eighteen from
the served schema, so labels live only in the model. `PatientListScreen` gained
a `picking` mode rather than a second patient chooser being written.

**Access**: the HTML pages restrict specialty modules to clinical cadres via
the middleware's namespace rule, which these endpoints do not share — so
`IsClinicalStaff` applies the same rule, and writing additionally needs the
module's `add_<model>` permission.

**What the 13 tests pin**: every registered module resolves and serves a usable
schema; labels and types come from the model (`nose_examination` → "Nose
examination", text; `follow_up_required` → boolean); an unknown module is a
404; records are written, patched, searched and kept apart by module; a
clerking note is written against a record and an empty one is refused; a
receptionist is refused outright and a nurse can read but not write.

**Divergence closed**: **thirteen** of the eighteen kept `authorization_code`
as a plain CharField — `oncology`, `anc`, `scbu`, `labor`, `icu`,
`family_planning`, `gynae_emergency`, `emergency`, `general_medicine`,
`pediatrics`, `surgery`, `cardiology`, `orthopedics` — so a code typed into any
of them was checked against nothing. All thirteen now carry the same FK to
`nhia.AuthorizationCode` plus `requires_authorization` and
`authorization_status` as `dental`, `ophthalmic`, `ent`, `neurology` and
`dermatology` already did (`<app>/migrations/*_authorization_code_fk.py`). Each
migration matches existing text to a real code where one exists and drops it
where it does not — an unmatched string was never an authorization — and
reverses cleanly. The record forms now offer only that patient's active codes,
via `core/authorization_fields.py`. A test walks every registered module and
fails if one ever goes back to free text.

---

## 8. Phase 6 — Dashboard (done)

**Endpoint**: one call, `/api/dashboard/` (`core/api/dashboard.py`). It returns
the tiles the caller is allowed to see — a tile is skipped unless the user holds
the same model permission the module's own endpoints require, so the home screen
never offers a screen the server would refuse. Five tiles today: clinic queue,
unpaid invoices (with the amount outstanding), lab results awaiting sign-off,
stock at or below reorder level, free beds. Adding a sixth is one row in
`TILES`.

**Screens**: `lib/dashboard.dart` is now the landing screen — each tile taps
straight into the screen that deals with it (`ClinicScreen`,
`InvoiceListScreen`, `TestRequestListScreen`, `InventoryScreen`,
`WardBoardScreen`), pull to refresh, and *All modules* still reaches the old
module list and the WebView routes.

**What the 2 tests pin** (`core/tests_dashboard.py`): a tile reports the real
figure (an occupied bed is not counted free, the outstanding amount is the
invoice's), and a user holding only `billing.view_invoice` is served that tile
and nothing else.

**Not built**: per-module summary endpoints beyond the ones that already exist
(`dispensing-logs/summary/`, `expenses/summary/`, `invoices/summary/`), and
charts. Counts are what a ward or clinic acts on; graphs are a reporting job and
the server already renders those pages.

---

## 9. Cross-cutting work

Independent of module order; slot in when the need first bites.

**File upload and viewing** (mostly done with Phase 2)
`Api.postMultipart` sends files, `/radiology/api/orders/<id>/enter-result/`
accepts them, and the study viewer reads `image_url` off the report. What is
left is choosing a file on the device — an image-picker plugin plus the Android
and iOS permission entries — and pointing the same transport at lab
`TestResult.result_file` and patient photos. `/media/` is public to the access
middleware, so the viewer needs no token today; that changes if media is moved
behind auth.

**Offline behaviour** (S to start, L to do properly)
The app assumes connectivity. Minimum useful step: cache the last successful
list response per screen and show it with a "stale" marker. Full offline
write-behind is a project of its own and should not be started casually — a
queued dispensing or payment that syncs later is a data-integrity problem, not a
UX feature.

**Push notifications** (M)
`InternalNotification` rows already exist (referrals accepted, wallet payments).
Surfacing them needs a device-token endpoint, a sender, and FCM setup.

**Session and token lifetime** (S)
Tokens never expire and are not rotated. Decide expiry, add a refresh or
re-login prompt, and handle 401 globally in `Api` by bouncing to the login
screen rather than showing an error.

**Printing and PDF** (S–M)
Receipts and results exist as server-rendered PDFs (ReportLab). Simplest path:
open the existing print URL in the WebView. Native PDF generation is not worth
it.

**Release engineering** (M)
Nothing has been built or run on a device yet — `flutter build apk` has never
been executed in this repo. Before any pilot: build for a real device, set
`HMS_BASE_URL` per environment, remove `usesCleartextTraffic` once the server is
HTTPS, add app icons and a launch screen, and decide distribution.

**CI** (S)
`flutter analyze`, `flutter test` and the Django API tests should run on every
push. All three are green today; keeping them that way is cheap now and
expensive later.

---

## 10. Debt and known issues

Fixed during this work, recorded so the reasoning is not lost:

- Activity logging spawned a daemon thread per request, each opening its own DB
  connection; they raced the request and lost writes ("database table is
  locked"). Replaced by one queued worker in `core/background_writer.py`.
- Access-control middleware answered API clients with HTML redirects, so a
  denied mobile request looked like a successful page. Both middlewares now
  answer JSON (`core/api_requests.py`).
- `TestResult.verified_date` was assigned and displayed but was never a field —
  the timestamp was discarded and reading it back raised `AttributeError`.
- A laboratory signal completed a request as soon as results existed, making the
  verification path's completion logic dead code. Completion now means sign-off
  (`sync_request_completion`), with `resync_test_request_status` to reconcile
  existing rows.
- `transfer_between_wallets` linked transfer records with `.latest("created_at")`;
  the clock is coarser than the writes, so same-amount transfers could link the
  wrong rows.
- Patient transfer never worked: the view was `@require_http_methods(["GET"])`,
  and its unreachable POST branch used field names no model or form has
  (`old_bed`, `new_bed`, `transfer_type`). Now `transfer_patient` in the service.
- Daily admission charges never ran: the double-charge guard filtered
  `WalletTransaction.objects.filter(wallet=...)` and the field is
  `patient_wallet`, so every admission raised `FieldError` and was skipped. The
  same wrong field appeared three more times in `inpatient/tasks.py`.
- **Radiology sign-off never recorded who signed.** `verify_result` set
  `result_status` and `verified_date` but not `verified_by`, so every verified
  report showed an empty radiologist. `radiology.services.verify_result` sets it.
- **Bulk authorization did nothing but raise errors.** The two bulk views
  created an `AuthorizationCode` without an `expiry_date` — a non-null column,
  so every call was an `IntegrityError` — and never attached the code to the
  consultation or referral, leaving both in the queue. Both now call
  `nhia.services.authorize`.
- **Admissions were billed two or three times.** Three separate paths charged
  the admission fee on create: the view, `inpatient.signals`, and
  `billing.signals.handle_admission_wallet_debit`. The service now owns the
  charge and both receivers stand down for admissions it created
  (`_charge_handled`), staying as the fallback for admissions made elsewhere.

Still open:

- **Django 4.2.26 is installed; `CLAUDE.md` documents Django 5.2.** One of the
  two is wrong and it affects every upgrade decision.
- **Legacy bulk-store transfer views** still set approval fields inline instead
  of using `MedicationTransfer.approve_transfer()`. Harmless today, a drift risk
  tomorrow.
- **No rate limiting on `/api/accounts/login/`**, which is now a public endpoint
  reachable from anywhere.
- **`Invoice.recalculate_from_items()` is only called by the API.** The HTML
  path computes totals its own way; worth converging.
- **Admission charges accrue twice over a long stay.** `billing.signals`
  debits the increase in `get_total_cost()` whenever an admission row is saved,
  and `daily_admission_charges` debits a day's charge per day. Both write
  `daily_admission_charge` rows; only the command is idempotent per date. One
  of the two should go, and the command is the one with a schedule behind it.
- **Nothing dashboard-side is cached.** The home screen refetches its five
  counts on every open; each is one `COUNT(*)`, which is fine now and worth
  watching once the tables are large.

---

## 11. Testing

Run the API suites together — several bugs only appeared in combination:

```bash
python manage.py test pharmacy laboratory patients billing appointments \
    consultations accounts core inpatient nhia desk_office radiology theatre
cd frontend && flutter analyze && flutter test
```

Conventions worth keeping:

- One test file per module's API, named for the workflow it protects.
- Assert the refusal *and* the absence of the side effect — no payment row, no
  stock movement, no second appointment.
- Use `@override_settings(STRICT_ACCESS_CONTROL=True)` so tests run against the
  same gate production uses.
- Give test users real roles (`Role.objects.get_or_create(name="pharmacist")`)
  rather than superuser shortcuts, or the permission tests prove nothing.

---

## 12. Suggested order

1. ~~**Inpatient**~~ — done
2. ~~**NHIA / desk office**~~ — done
3. ~~**Radiology**~~ — done
4. ~~**Theatre**~~ — done
5. ~~**Specialty modules**~~ — done, on the generic route
6. ~~**Dashboard**~~ — done, and the last phase: every module is native now

What is left is §9 — the cross-cutting work, in the order a pilot forces it:
token expiry and a global 401 bounce, release engineering (`flutter build apk`
has still never run in this repo), CI, then offline caching and push.
