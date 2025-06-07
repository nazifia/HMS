from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter
def report_status_badge(status):
    """
    Return a Bootstrap badge for report execution status
    Usage: {{ execution.status|report_status_badge }}
    """
    status_classes = {
        'success': 'bg-success',
        'failed': 'bg-danger',
        'processing': 'bg-warning',
    }
    
    status_labels = {
        'success': 'Success',
        'failed': 'Failed',
        'processing': 'Processing',
    }
    
    css_class = status_classes.get(status, 'bg-secondary')
    label = status_labels.get(status, status.replace('_', ' ').title())
    
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.filter
def format_execution_time(seconds):
    """
    Format execution time in seconds to a human-readable format
    Usage: {{ execution.execution_time|format_execution_time }}
    """
    if not seconds:
        return ''
    
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes} min {remaining_seconds} sec"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} hr {minutes} min"

@register.filter
def json_to_html(json_data):
    """
    Convert JSON data to HTML representation
    Usage: {{ execution.parameters_used|json_to_html }}
    """
    if not json_data:
        return ''
    
    try:
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
        
        html = '<table class="table table-sm">'
        html += '<thead><tr><th>Parameter</th><th>Value</th></tr></thead><tbody>'
        
        for key, value in data.items():
            html += f'<tr><td>{key}</td><td>{value}</td></tr>'
        
        html += '</tbody></table>'
        return mark_safe(html)
    except Exception:
        return str(json_data)

@register.filter
def chart_data_to_json(data):
    """
    Convert chart data to JSON for use in JavaScript
    Usage: {{ widget.get_content|chart_data_to_json }}
    """
    if not data:
        return '{}'
    
    try:
        if isinstance(data, str):
            return data
        else:
            return mark_safe(json.dumps(data))
    except Exception:
        return '{}'

@register.simple_tag
def get_widget_template(widget_type):
    """
    Return the appropriate template for a widget type
    Usage: {% get_widget_template widget.widget_type %}
    """
    templates = {
        'chart': 'reporting/widgets/chart.html',
        'table': 'reporting/widgets/table.html',
        'metric': 'reporting/widgets/metric.html',
        'list': 'reporting/widgets/list.html',
    }
    
    return templates.get(widget_type, 'reporting/widgets/default.html')
