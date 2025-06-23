from django.apps import AppConfig


class TheatreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'theatre'
    verbose_name = 'Operation Theatre Management'
    app_label = 'theatre'  # Add explicit app_label

    def ready(self):
        import theatre.signals  # noqa