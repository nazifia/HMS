from django.apps import AppConfig


class DoctorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'doctors'
    verbose_name = 'Doctor Management'

    def ready(self):
        from . import signals
