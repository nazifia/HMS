from django.apps import AppConfig


class SaasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "saas"
    verbose_name = "SaaS / Multi-Tenant"

    def ready(self):
        from .fields import patch_related_formfields

        patch_related_formfields()
