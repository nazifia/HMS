# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
# Import is optional to avoid errors when Celery is not installed
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not available, skip import
    celery_app = None
    __all__ = ()
