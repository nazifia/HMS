from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def radiology_status_badge(status):
    """
    Return a Bootstrap badge for radiology order status
    Usage: {{ order.status|radiology_status_badge }}
    """
    status_classes = {
        "pending": "bg-warning",
        "awaiting_payment": "bg-info",
        "payment_confirmed": "bg-primary",
        "scheduled": "bg-info",
        "completed": "bg-success",
        "cancelled": "bg-danger",
    }

    status_labels = {
        "pending": "Pending",
        "awaiting_payment": "Awaiting Payment",
        "payment_confirmed": "Payment Confirmed",
        "scheduled": "Scheduled",
        "completed": "Completed",
        "cancelled": "Cancelled",
    }

    css_class = status_classes.get(status, "bg-secondary")
    label = status_labels.get(status, status.replace("_", " ").title())

    return mark_safe(f'<span class="badge {css_class}">{label}</span>')


@register.filter
def priority_badge(priority):
    """
    Return a Bootstrap badge for priority
    Usage: {{ order.priority|priority_badge }}
    """
    priority_classes = {
        "normal": "bg-secondary",
        "urgent": "bg-warning",
        "emergency": "bg-danger",
    }

    priority_labels = {
        "normal": "Normal",
        "urgent": "Urgent",
        "emergency": "Emergency",
    }

    css_class = priority_classes.get(priority, "bg-secondary")
    label = priority_labels.get(priority, priority.replace("_", " ").title())

    return mark_safe(f'<span class="badge {css_class}">{label}</span>')


@register.filter
def result_status_badge(is_abnormal):
    """
    Return a Bootstrap badge for radiology result status
    Usage: {{ result.is_abnormal|result_status_badge }}
    """
    if is_abnormal:
        return mark_safe('<span class="badge bg-danger">Abnormal</span>')
    else:
        return mark_safe('<span class="badge bg-success">Normal</span>')


@register.filter
def radiology_result_status_badge(status):
    """
    Return a Bootstrap badge for radiology result workflow status
    Usage: {{ result.result_status|radiology_result_status_badge }}
    """
    status_classes = {
        "draft": "bg-secondary",
        "submitted": "bg-info",
        "verified": "bg-primary",
        "finalized": "bg-success",
    }

    status_labels = {
        "draft": "Draft",
        "submitted": "Submitted",
        "verified": "Verified",
        "finalized": "Finalized",
    }

    css_class = status_classes.get(status, "bg-secondary")
    label = status_labels.get(status, status.replace("_", " ").title())

    return mark_safe(f'<span class="badge {css_class}">{label}</span>')


@register.filter
def status_badge_class(status):
    """Return just the Bootstrap class for a status (without HTML)"""
    status_classes = {
        "pending": "bg-warning",
        "awaiting_payment": "bg-info",
        "payment_confirmed": "bg-primary",
        "scheduled": "bg-info",
        "completed": "bg-success",
        "cancelled": "bg-danger",
    }
    return status_classes.get(status, "bg-secondary")


@register.filter
def priority_badge_class(priority):
    """Return just the Bootstrap class for a priority (without HTML)"""
    priority_classes = {
        "normal": "bg-secondary",
        "urgent": "bg-warning",
        "emergency": "bg-danger",
    }
    return priority_classes.get(priority, "bg-secondary")


@register.filter
def result_status_class(status):
    """Return just the Bootstrap class for a result workflow status (without HTML)"""
    status_classes = {
        "draft": "bg-secondary",
        "submitted": "bg-info",
        "verified": "bg-primary",
        "finalized": "bg-success",
    }
    return status_classes.get(status, "bg-secondary")
