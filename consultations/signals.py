"""Auto-provision outpatient clinic infrastructure for new hospitals.

Mirrors the one-time backfill in migration 0017 so tenants created after it
(via signup, admin, or shell) also get their MOPD/SOPD consulting rooms.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from saas.models import Hospital

CLINIC_DEPARTMENTS = ["MOPD", "SOPD", "POPD"]


def seed_clinic_rooms_for(hospital):
    """Create one consulting room per outpatient clinic for `hospital` (idempotent)."""
    from accounts.models import Department
    from .models import ConsultingRoom

    for dept_name in CLINIC_DEPARTMENTS:
        department = Department.all_objects.filter(
            hospital=hospital, name=dept_name
        ).first()
        if department is None:
            continue
        # room_number is globally unique, so embed the hospital id.
        ConsultingRoom.all_objects.get_or_create(
            room_number=f"{dept_name}-{hospital.id}",
            defaults={
                "floor": "Ground",
                "department": department,
                "hospital": hospital,
                "description": f"{dept_name} outpatient consulting room",
                "is_active": True,
            },
        )


@receiver(post_save, sender=Hospital, dispatch_uid="seed_clinic_rooms")
def create_clinic_rooms(sender, instance, created, **kwargs):
    if not created:
        return
    # Departments must exist before rooms can point at them. The signup view
    # also seeds departments; both calls are idempotent.
    from accounts.department_seed import seed_departments_for

    seed_departments_for(instance)
    seed_clinic_rooms_for(instance)
