from django import template

register = template.Library()


@register.filter(name='add_class')
def add_class(field, css_class):
    """Add CSS class to form field"""
    if hasattr(field, 'as_widget'):
        field = field.as_widget()
    
    if hasattr(field, 'as_widget'):
        field = field.as_widget()
    
    # For Django form fields
    if hasattr(field, 'field'):
        widget = field.field.widget
        widget.attrs = widget.attrs or {}
        existing_classes = widget.attrs.get('class', '')
        if css_class not in existing_classes:
            widget.attrs['class'] = f"{existing_classes} {css_class}"
        else:
            widget.attrs['class'] = existing_classes
        return str(field)
    
    # Try to get widget directly
    if hasattr(field, 'widget'):
        widget = field.widget
        widget.attrs = widget.attrs or {}
        existing_classes = widget.attrs.get('class', '')
        if css_class not in existing_classes:
            widget.attrs['class'] = f"{existing_classes} {css_class}"
        else:
            widget.attrs['class'] = existing_classes
        return str(field)
    
    # Fallback - try to render and add class
    try:
        field_html = str(field)
        if 'class=' in field_html:
            if css_class and css_class not in field_html:
                # Add the CSS class
                field_html = field_html.replace('class="', f'class="{css_class} ')
            return field_html
    except:
        return str(field)


@register.filter(name='add_placeholder')
def add_placeholder(field, placeholder):
    """Add placeholder to form field"""
    if hasattr(field, 'field'):
        widget = field.field.widget
        widget.attrs = widget.attrs or {}
        widget.attrs['placeholder'] = placeholder
        return str(field)
    elif hasattr(field, 'widget'):
        widget = field.widget
        widget.attrs = widget.attrs or {}
        widget.attrs['placeholder'] = placeholder
        return str(field)
    else:
        try:
            field_html = str(field)
            if 'placeholder=' not in field_html and placeholder:
                # Add placeholder to the field
                field_html = field_html.replace('<input', f'<input placeholder="{placeholder}"')
            return field_html
        except:
            return str(field)


@register.filter(name='id_for_label')
def id_for_label(field):
    """Get the ID for label"""
    if hasattr(field, 'id_for_label'):
        return field.id_for_label()
    elif hasattr(field, 'auto_id'):
        return field.auto_id
    else:
        return str(field).split('"')[1] if '"' in str(field) else 'field'
