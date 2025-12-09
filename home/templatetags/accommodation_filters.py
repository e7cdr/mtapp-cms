
from django import template

register = template.Library()
@register.filter
def model_name(obj):
    return obj.__class__.__name__.replace('Page', '').lower()

@register.filter
def get_choice_label(value, choices):
    return dict(choices).get(value, value)

@register.filter
def sub(value, arg):
    """Subtract arg from value. Works with int/float/Decimal."""
    try:
        return value - arg
    except (ValueError, TypeError):
        return value  # fallback silently

@register.filter
def add(value, arg):
    """Same as built-in, but handles Decimal safely"""
    try:
        return value + arg
    except (ValueError, TypeError):
        return value