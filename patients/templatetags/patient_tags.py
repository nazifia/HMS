from django import template

register = template.Library()

@register.filter
def get_patient_type_display(value):
    """Return display name for patient type"""
    choices = {
        'nhia': 'NHIA',
        'regular': 'Regular',
        'private': 'Private',
        'corporate': 'Corporate'
    }
    return choices.get(value, value.title())
