
from django.apps import AppConfig

class DeskOfficeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'desk_office'

    def ready(self):
        import desk_office.signals
