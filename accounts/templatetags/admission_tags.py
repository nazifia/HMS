from django import template

register = template.Library()

@register.filter
def admitted_count(admissions):
    return len([a for a in admissions if getattr(a, 'status', None) == 'admitted'])

@register.filter
def discharged_count(admissions):
    return len([a for a in admissions if getattr(a, 'status', None) == 'discharged'])
