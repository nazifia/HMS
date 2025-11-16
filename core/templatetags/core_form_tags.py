from django import template
from django.forms import BoundField

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Add a CSS class to a Django form field, merging with existing classes
    Usage: {{ form.field|add_class:"form-control" }}
    """
    # Check if field is a proper form field (BoundField)
    if hasattr(field, 'as_widget') and isinstance(field, BoundField):
        # Get existing widget attributes
        existing_attrs = field.field.widget.attrs.copy() if hasattr(field, 'field') and hasattr(field.field, 'widget') else {}
        
        # Merge CSS classes
        existing_class = existing_attrs.get('class', '')
        if existing_class:
            # Don't duplicate classes
            new_classes = set(existing_class.split() + css_class.split())
            merged_class = ' '.join(sorted(new_classes))
        else:
            merged_class = css_class
            
        existing_attrs['class'] = merged_class
        return field.as_widget(attrs=existing_attrs)
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
