from django.apps import AppConfig


class InpatientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inpatient'

    def ready(self):
        import inpatient.signals
