"""Per-hospital cache versioning for the dashboard pages.

The dashboard caches under keys built from user, date and chart range, so no
single key can be deleted when a row changes. Instead every hospital carries a
version number that its dashboard keys embed; bumping that number on write
orphans the hospital's entries, which then die on their own TTL.

Signals mean queryset-level writes (bulk_create, .update(), raw SQL) do not
bump anything; those pages stay stale until the 5-minute TTL runs out.

ponytail: if the version key itself is evicted the counter restarts at 0 and a
surviving entry from the previous version-0 window can be served again, for at
most the cache TTL. Store the version in a durable row if that ever matters.
"""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save

# Models whose rows feed the dashboard or system overview numbers.
WATCHED = (
    "patients.Patient",
    "patients.PatientWallet",
    "patients.WalletTransaction",
    "appointments.Appointment",
    "pharmacy.Prescription",
    "pharmacy.Medication",
    "pharmacy.MedicationCategory",
    "pharmacy.ActiveStoreInventory",
    "laboratory.TestRequest",
    "laboratory.Test",
    "laboratory.TestCategory",
    "billing.Invoice",
    "billing.Payment",
    "billing.Service",
    "billing.ServiceCategory",
    "consultations.Consultation",
    "consultations.ConsultingRoom",
    "consultations.Referral",
    "consultations.WaitingList",
    "inpatient.Ward",
    "inpatient.Bed",
    "inpatient.Admission",
    "accounts.CustomUser",
    "accounts.Department",
    "nhia.AuthorizationCode",
    "ophthalmic.OphthalmicRecord",
    "ent.EntRecord",
    "oncology.OncologyRecord",
    "scbu.ScbuRecord",
    "anc.AncRecord",
    "labor.LaborRecord",
    "icu.IcuRecord",
    "family_planning.Family_planningRecord",
    "gynae_emergency.Gynae_emergencyRecord",
)


def _version_key(hospital_id):
    return f"dashboard_version_{hospital_id or 0}"


def get_version(hospital_id):
    """Current cache generation for one hospital (0 when never bumped)."""
    return cache.get(_version_key(hospital_id)) or 0


def bump(hospital_id):
    """Retire every cached dashboard page belonging to this hospital."""
    key = _version_key(hospital_id)
    try:
        cache.incr(key)
    except ValueError:  # key absent or expired
        cache.set(key, 1, None)


def _invalidate(sender, instance, **kwargs):
    hospital_id = getattr(instance, "hospital_id", None)
    if hospital_id:
        bump(hospital_id)


def connect():
    for label in WATCHED:
        uid = f"dashboard_invalidate_{label}"
        post_save.connect(_invalidate, sender=label, dispatch_uid=uid, weak=False)
        post_delete.connect(_invalidate, sender=label, dispatch_uid=uid, weak=False)
