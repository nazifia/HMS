import os
import django


def pytest_configure(config):
    # Ensure settings module is set early
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
    # Call django.setup() so apps are loaded before tests import models
    try:
        django.setup()
    except Exception:
        # Let pytest show errors during collection if setup fails
        pass
