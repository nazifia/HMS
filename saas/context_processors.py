"""Expose the current tenant's letterhead details to every template.

Receipts and result sheets render {{ hospital_name }} etc.; on a tenant
request these come from the Hospital row, otherwise from settings.
"""
from django.conf import settings


def hospital_details(request):
    h = getattr(request, "hospital", None)
    if h:
        return {
            "hospital_name": h.name,
            "hospital_address": h.address,
            "hospital_phone": h.phone,
            "hospital_email": h.email,
        }
    return {
        "hospital_name": settings.HOSPITAL_NAME,
        "hospital_address": settings.HOSPITAL_ADDRESS,
        "hospital_phone": settings.HOSPITAL_PHONE,
        "hospital_email": settings.HOSPITAL_EMAIL,
    }
