from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone

register = template.Library()

@register.filter
def admission_status_badge(status):
    """
    Return a Bootstrap badge for admission status
    Usage: {{ admission.status|admission_status_badge }}
    """
    status_classes = {
        'admitted': 'bg-success',
        'discharged': 'bg-info',
        'transferred': 'bg-warning',
        'deceased': 'bg-danger',
    }
    
    status_labels = {
        'admitted': 'Admitted',
        'discharged': 'Discharged',
        'transferred': 'Transferred',
        'deceased': 'Deceased',
    }
    
    css_class = status_classes.get(status, 'bg-secondary')
    label = status_labels.get(status, status.replace('_', ' ').title())
    
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.filter
def bed_status_badge(bed):
    """
    Return a Bootstrap badge for bed status
    Usage: {{ bed|bed_status_badge }}
    """
    if not bed.is_active:
        return mark_safe('<span class="badge bg-secondary">Maintenance</span>')
    elif bed.is_occupied:
        return mark_safe('<span class="badge bg-danger">Occupied</span>')
    else:
        return mark_safe('<span class="badge bg-success">Available</span>')

@register.filter
def ward_occupancy_percentage(ward):
    """
    Calculate ward occupancy percentage
    Usage: {{ ward|ward_occupancy_percentage }}
    """
    if ward.capacity == 0:
        return 0
    
    occupied = ward.get_occupied_beds_count()
    return (occupied / ward.capacity) * 100

@register.filter
def ward_occupancy_class(percentage):
    """
    Return CSS class based on ward occupancy percentage
    Usage: {{ ward|ward_occupancy_percentage|ward_occupancy_class }}
    """
    if percentage < 50:
        return 'bg-success'
    elif percentage < 80:
        return 'bg-warning'
    else:
        return 'bg-danger'

@register.filter
def admission_duration(admission):
    """
    Calculate admission duration in days
    Usage: {{ admission|admission_duration }}
    """
    if admission.discharge_date:
        delta = admission.discharge_date - admission.admission_date
    else:
        delta = timezone.now() - admission.admission_date
    
    return delta.days

@register.simple_tag
def calculate_admission_cost(admission):
    """
    Calculate the total cost of an admission
    Usage: {% calculate_admission_cost admission %}
    """
    if not admission or not admission.bed or not admission.bed.ward:
        return 0
    
    duration = admission.get_duration()
    if duration < 1:
        duration = 1  # Minimum 1 day charge
    
    daily_charge = admission.bed.ward.charge_per_day
    return daily_charge * duration
