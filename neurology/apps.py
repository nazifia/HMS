from django.apps import AppConfig

class NeurologyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'neurology'
    verbose_name = 'Neurology Department'
    
    def ready(self):
        # Import signals or perform initialization if needed
        pass
