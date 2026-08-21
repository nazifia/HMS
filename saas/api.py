"""DRF helpers for tenant scoping.

A viewset's class-level `queryset` is built once, at import time, when there is
no current hospital — so `Model.objects.all()` there freezes an unscoped
queryset and `GenericAPIView.get_queryset()` only clones it. This mixin
re-applies the tenant filter on every request.

Viewsets that build their queryset inside their own `get_queryset()` are
already scoped (the manager runs per request) and do not need it.
"""

from .current import get_current_hospital


class TenantScopedQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        hospital = get_current_hospital()
        if hospital is None:
            return queryset
        return queryset.filter(hospital=hospital)
