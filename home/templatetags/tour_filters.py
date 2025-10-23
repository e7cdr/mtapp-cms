# tours/templatetags/tour_filters.py
from django import template
from urllib.parse import urlencode
from streams.blocks import GLOBAL_ICON_CHOICES


register = template.Library()


@register.filter
def get_duration(tour):
    """
    Returns the appropriate duration for the tour based on its type.
    - FullTour/LandTour: duration_days
    - DayTour: duration_hours
    """
    if tour.tour_type_val == 'day':
        return getattr(tour, 'duration_hours', 0)
    return getattr(tour, 'duration_days', 0)

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def strip(value):
    try:
        return str(value).strip()
    except (AttributeError, TypeError):
        return value
    
@register.filter
def add_page_param(request_get, page):
    if not request_get:
        return f'page={page}'
    
    params = request_get.copy()
    params['page'] = page
    # NEW: Filter out empty params
    filtered_params = {k: v for k, v in params.items() if v}  # Skip if value is empty string
    return urlencode(filtered_params)


@register.filter
def get_choice_label(value):
    # Find the label for the given choice value
    for choice_value, choice_label in GLOBAL_ICON_CHOICES:
        if choice_value == value:
            return choice_label
    return value  # Fallback to the value if no label is found

@register.filter
def label_from_choice(value, choices):
    """
    Returns the label for a given choice value from a list of tuples.
    """
    for choice_value, label in choices:
        if choice_value == value:
            return label
    return value  # Fallback to value if no match