# tours/templatetags/tour_filters.py
from django import template
from urllib.parse import urlencode

from django.urls import NoReverseMatch, reverse
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
def get_choice_label(value, choices=None):
    """
    Returns the human-readable label for a choice value.
    Usage:
        {{ value|get_choice_label }}                → returns value itself
        {{ value|get_choice_label:MY_CHOICES }}     → returns label if found
    """
    if not value:
        return 'Unknown'
    if choices is None:
        return value  # or '' if you prefer empty string
    # Convert choices tuple/list to dict for fast lookup
    return dict(choices).get(value, value)

@register.simple_tag(takes_context=True)
def booking_url(context, tour_page):
    """
    Returns the correct booking URL with language prefix for Full/Land/Day tours.
    Usage: {% booking_url page %}
    """
    request = context.get('request')
    if not request:
        return '#'

    # Map model name to tour_type
    model_name = tour_page.specific_class.__name__
    tour_type_map = {
        'FullTourPage': 'full',
        'LandTourPage': 'land',
        'DayTourPage': 'day',
    }
    tour_type = tour_type_map.get(model_name)

    if not tour_type:
        return '#'

    try:
        # This automatically includes the current language prefix (e.g., /en/, /es/)
        return reverse('bookings:booking_start', kwargs={
            'tour_type': tour_type,
            'tour_id': tour_page.id
        })
    except NoReverseMatch:
        return '#'
