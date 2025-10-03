from django import template
from django.forms import BoundField

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Add a CSS class to a Django form field
    Usage: {{ form.field|add_class:"form-control" }}
    """
    # Check if field is a proper form field (BoundField)
    if hasattr(field, 'as_widget') and isinstance(field, BoundField):
        return field.as_widget(attrs={"class": css_class})
    elif hasattr(field, 'as_widget'):
        # Try to render as widget if it has the method
        try:
            return field.as_widget(attrs={"class": css_class})
        except (AttributeError, TypeError):
            # If it fails, return the field as is
            return field
    else:
        # If it's not a form field (like a string), return it as is
        return field
