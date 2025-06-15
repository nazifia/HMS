from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Template filter to lookup a value in a dictionary"""
    return dictionary.get(key, [])
