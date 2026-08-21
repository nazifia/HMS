"""Form fields that re-apply tenant scoping every time they are read.

A form field declared at class level is built once, at import time, when there
is no current hospital — so `Model.tenant_objects.filter(...)` there freezes an
unscoped queryset for the whole process. These fields keep the declared
queryset as a base and add `hospital=<current>` on every access (rendering the
choices, and validating the submitted id), so a picker never shows or accepts
another tenant's row.

Use for class-level declarations. Inside `__init__`, plain
`Model.tenant_objects` is already correct.
"""

from django import forms

from .current import get_current_hospital


def _scoped(queryset):
    hospital = get_current_hospital()
    if queryset is None or hospital is None:
        return queryset
    return queryset.filter(hospital=hospital)


class TenantChoiceField(forms.ModelChoiceField):
    def _get_queryset(self):
        return _scoped(self._queryset)

    queryset = property(_get_queryset, forms.ModelChoiceField._set_queryset)


class TenantMultipleChoiceField(forms.ModelMultipleChoiceField):
    def _get_queryset(self):
        return _scoped(self._queryset)

    queryset = property(_get_queryset, forms.ModelMultipleChoiceField._set_queryset)


def patch_related_formfields():
    """Make auto-generated ModelForm fields for tenant-scoped FKs re-scope.

    A ModelForm builds a field for every FK when the form *class* is created —
    at import time, with no current hospital — so the default ModelChoiceField
    would offer (and accept) every tenant's rows. Swapping the default form
    class fixes every ModelForm at once; a form that passes its own
    `form_class` is left alone.

    Called from SaasConfig.ready(). Django itself is patched in one other place
    already (core/django_patches.py); keep both in mind when upgrading Django.
    """
    from django.db.models import ForeignKey, ManyToManyField

    def patch(field_cls, tenant_field_cls):
        original = field_cls.formfield

        def formfield(self, **kwargs):
            model = self.remote_field.model
            if (
                "form_class" not in kwargs
                and not isinstance(model, str)
                and any(f.name == "hospital" for f in model._meta.local_fields)
            ):
                kwargs["form_class"] = tenant_field_cls
            return original(self, **kwargs)

        formfield.__doc__ = original.__doc__
        field_cls.formfield = formfield

    patch(ForeignKey, TenantChoiceField)
    patch(ManyToManyField, TenantMultipleChoiceField)
