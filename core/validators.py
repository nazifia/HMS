"""Nigerian phone number validation (NCC numbering plan)."""

import re

from django import forms
from django.core.exceptions import ValidationError
from django.db import models

# NCC mobile format: 0XXXXXXXXXX (11 digits, prefixes 070x/071x/080x/081x/090x/091x)
# or international +234XXXXXXXXXX / 234XXXXXXXXXX.
NCC_PHONE_RE = re.compile(r"^(?:\+?234|0)([7-9][01]\d{8})$")


def normalize_nigerian_phone(value):
    """Strip separators and convert +234/234 prefix to local 0-prefixed form."""
    cleaned = re.sub(r"[\s\-().]", "", str(value or ""))
    match = NCC_PHONE_RE.match(cleaned)
    return "0" + match.group(1) if match else cleaned


def validate_nigerian_phone(value):
    cleaned = re.sub(r"[\s\-().]", "", str(value))
    if not NCC_PHONE_RE.match(cleaned):
        raise ValidationError(
            "Enter a valid Nigerian phone number (NCC format), e.g. "
            "08012345678, 07012345678, 09012345678 or +2348012345678."
        )


class NigerianPhoneFormField(forms.CharField):
    """Normalizes in to_python so max_length runs against the normalized value,
    letting users type '+234 806 123 4567' into a max_length=15 field."""

    def to_python(self, value):
        value = super().to_python(value)
        if value in (None, ""):
            return value
        return normalize_nigerian_phone(value)


class NigerianPhoneField(models.CharField):
    """CharField that validates NCC format and normalizes to 0-prefixed form
    (+2348012345678 -> 08012345678) during full_clean, so every ModelForm and
    admin save stores the uniform local format."""

    default_validators = [validate_nigerian_phone]

    def to_python(self, value):
        value = super().to_python(value)
        if value in (None, ""):
            return value
        return normalize_nigerian_phone(value)

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", NigerianPhoneFormField)
        return super().formfield(**kwargs)


if __name__ == "__main__":
    # ponytail: self-check, run with `python core/validators.py`
    good = ["08012345678", "07061234567", "09112345678", "+2348012345678",
            "2347061234567", "0801 234 5678", "0801-234-5678"]
    bad = ["8012345678", "0601234567", "080123456", "080123456789",
           "+1234567890", "abc", "08512345678"]
    for v in good:
        validate_nigerian_phone(v)
    for v in bad:
        try:
            validate_nigerian_phone(v)
            raise AssertionError(f"should have failed: {v}")
        except ValidationError:
            pass
    assert normalize_nigerian_phone("+2348012345678") == "08012345678"
    assert normalize_nigerian_phone("0801 234 5678") == "08012345678"
    print("ok")
