from django.contrib.contenttypes.models import ContentType
from .models import AuditLog
from django.utils import timezone

def log_audit_action(user, action, instance, description=None):
    # Compose a details string for the log
    details = description or str(instance)
    AuditLog.objects.create(
        user=user,
        action=action,
        details=details,
        timestamp=timezone.now()
    )
