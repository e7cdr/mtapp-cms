import json
from django import template
from datetime import datetime, timedelta

register = template.Library()

@register.filter
def add_days(value, days):
    try:
        # Convert string date to datetime
        date = datetime.strptime(value, '%Y-%m-%d')
        # Add the specified number of days
        new_date = date + timedelta(days=int(days))
        # Return formatted date
        return new_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # Return original value if conversion fails
        return value
    
@register.filter
def json_script(value, element_id):
    return json.dumps(value, ensure_ascii=False)


@register.filter
def select_infants(ages, child_age_min):
    """Filter ages to return only those below child_age_min."""
    return [age for age in ages if age < int(child_age_min)]

@register.filter
def json_loads(value):
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

@register.filter
def infants_count(child_ages, child_age_min):
    try:
        return sum(1 for age in child_ages if age < int(child_age_min))
    except (TypeError, ValueError):
        return 0

@register.filter
def select_children(ages, child_age_min):
    return ", ".join(str(age) for age in ages if age >= child_age_min)

@register.filter
def multiply(value, arg):
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0  # Return 0 instead of value to avoid incorrect counts
    
    
@register.filter
def to_json(value):
    """
    Convert a Python object to a JSON string.
    """
    return json.dumps(value)


@register.simple_tag(takes_context=True)
def query_transform(context, request, key, value):
    """
    Returns current URL with only one change: set key=value
    Removes the key completely if value is empty/None
    """
    getvars = request.GET.copy()

    if value:
        getvars[key] = value
    else:
        getvars.pop(key, None)

    # Clean pagination params if you want (optional but recommended)
    getvars.pop('proposals_page', None)
    getvars.pop('bookings_page', None)
    getvars.pop('page', None)

    if not getvars:
        return request.path

    return f"{request.path}?{getvars.urlencode()}"