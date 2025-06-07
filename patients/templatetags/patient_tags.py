from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone

register = template.Library()

@register.filter
def gender_icon(gender):
    """
    Return a Font Awesome icon for gender
    Usage: {{ patient.gender|gender_icon }}
    """
    if gender == 'M':
        return mark_safe('<i class="fas fa-male text-primary"></i>')
    elif gender == 'F':
        return mark_safe('<i class="fas fa-female text-danger"></i>')
    else:
        return mark_safe('<i class="fas fa-user text-secondary"></i>')

@register.filter
def blood_group_badge(blood_group):
    """
    Return a Bootstrap badge for blood group
    Usage: {{ patient.blood_group|blood_group_badge }}
    """
    if not blood_group:
        return ''
    
    blood_group_classes = {
        'A+': 'bg-danger',
        'A-': 'bg-danger',
        'B+': 'bg-primary',
        'B-': 'bg-primary',
        'AB+': 'bg-warning',
        'AB-': 'bg-warning',
        'O+': 'bg-success',
        'O-': 'bg-success',
    }
    
    css_class = blood_group_classes.get(blood_group, 'bg-secondary')
    
    return mark_safe(f'<span class="badge {css_class}">{blood_group}</span>')

@register.filter
def calculate_age(date_of_birth):
    """
    Calculate age from date of birth
    Usage: {{ patient.date_of_birth|calculate_age }}
    """
    if not date_of_birth:
        return None
    
    today = timezone.now().date()
    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    return age

@register.filter
def format_phone(phone_number):
    """
    Format a phone number
    Usage: {{ patient.phone_number|format_phone }}
    """
    if not phone_number:
        return ''
    
    # Remove any non-digit characters
    digits = ''.join(filter(str.isdigit, phone_number))
    
    # Format based on length
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    else:
        return phone_number

@register.filter
def bmi_category(bmi):
    """
    Return BMI category based on BMI value
    Usage: {{ vitals.bmi|bmi_category }}
    """
    if not bmi:
        return ''
    
    try:
        bmi = float(bmi)
        if bmi < 18.5:
            return 'Underweight'
        elif bmi < 25:
            return 'Normal weight'
        elif bmi < 30:
            return 'Overweight'
        else:
            return 'Obese'
    except (ValueError, TypeError):
        return ''

@register.filter
def bmi_category_class(bmi):
    """
    Return CSS class for BMI category
    Usage: {{ vitals.bmi|bmi_category_class }}
    """
    if not bmi:
        return ''
    
    try:
        bmi = float(bmi)
        if bmi < 18.5:
            return 'text-warning'
        elif bmi < 25:
            return 'text-success'
        elif bmi < 30:
            return 'text-warning'
        else:
            return 'text-danger'
    except (ValueError, TypeError):
        return ''
