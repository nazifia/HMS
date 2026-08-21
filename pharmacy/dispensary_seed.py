"""Per-hospital dispensary seeding.

A new tenant with no dispensary has nowhere to hold stock: the dashboard's
stock-entry picker is empty and dispensing has no source. Every hospital gets
one to start with; more are added from the dispensary list.
"""

from .models import Dispensary

DEFAULT_DISPENSARY = "Main Pharmacy"


def seed_dispensary_for(hospital):
    """Create the default dispensary for `hospital` (idempotent).

    The post_save signal on Dispensary creates its ActiveStore, so the
    dispensary can take stock immediately.
    """
    dispensary, _ = Dispensary.all_objects.get_or_create(
        hospital=hospital,
        name=DEFAULT_DISPENSARY,
        defaults={"description": "Main medication dispensing point"},
    )
    return dispensary
