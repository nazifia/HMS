from django import template
from django.utils.html import format_html
import json

register = template.Library()


@register.filter(name="render_json_details")
def render_json_details(details):
    if isinstance(details, dict):
        return _render_dict(details)
    elif isinstance(details, list):
        html = "<ul>"
        for item in details:
            html += "<li>{}</li>".format(_render_value(item))
        html += "</ul>"
        return format_html(html)
    else:
        # For non-dict/list values (e.g., simple strings, numbers, booleans)
        return format_html(_render_value(details))


def _render_dict(data, level=0):
    html = ""
    for key, value in data.items():
        padding = "style='padding-left: {}px;'".format(level * 20)
        key_str = "<strong>{}:</strong>".format(key.replace("_", " ").title())

        if isinstance(value, dict):
            html += "<div {}><span class='key'>{}</span></div>".format(padding, key_str)
            html += _render_dict(value, level + 1)
        elif isinstance(value, list):
            html += "<div {}><span class='key'>{}</span>".format(padding, key_str)
            html += "<ul>"
            for item in value:
                html += "<li>{}</li>".format(_render_value(item))
            html += "</ul></div>"
        else:
            html += "<div {}><span class='key'>{}</span> {}</div>".format(
                padding, key_str, _render_value(value)
            )
    return format_html(html)


def _render_value(value):
    if value is None:
        return format_html(
            "<span style='background-color: #ffe0b2;'>[TYPE: None] <em>None</em></span>"
        )
    if isinstance(value, bool):
        return format_html(
            f"<span style='background-color: #c8e6c9;'>[TYPE: Bool] {'Yes' if value else 'No'}</span>"
        )
    if isinstance(value, str):
        if not value.strip():
            return format_html(
                "<span style='background-color: #ffccbc;'>[TYPE: String] <em>(Empty)</em></span>"
            )
        return format_html(
            f"<span style='background-color: #bbdefb;'>[TYPE: String] {value}</span>"
        )
    # For any other type, convert to string
    return format_html(
        f"<span style='background-color: #f8bbd0;'>[TYPE: Other] {str(value)}</span>"
    )


@register.filter(name="get_item")
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    # Handle JSONField or other dict-like objects
    try:
        return dictionary[key]
    except (KeyError, TypeError):
        return None


@register.filter(name="replace")
def replace_filter(value, args):
    """
    Replace occurrences of a substring with another substring.
    Usage: {{ value|replace:"old|new" }}
    """
    if not value:
        return value
    try:
        old, new = args.split("|")
        return str(value).replace(old, new)
    except ValueError:
        return value
