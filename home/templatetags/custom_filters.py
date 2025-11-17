import json
import datetime
from django import template
from wagtail.models import Page
from django.utils.html import escape
from django.utils.formats import number_format
from django.utils.translation import get_language

register = template.Library()

@register.filter
def times(number):
    """
    Converts an integer to a range object for template iteration.
    Example: {{ 3|times }} -> range(3) for {% for i in 3|times %}
    """
    try:
        return range(int(number))
    except (ValueError, TypeError):
        return range(0)
    
@register.filter
def add_days(value, days):
    try:
        # Convert string date to datetime
        date = datetime.strptime(value, '%Y-%m-%d')
        # Add the specified number of days
        new_date = date + datetime.timedelta(days=int(days))
        # Return formatted date
        return new_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # Return original value if conversion fails
        return value
    
@register.filter
def parse_json(value):
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

@register.filter
def index(sequence, position):
    try:
        return sequence[int(position)]
    except (IndexError, ValueError, TypeError):
        return ''
    
@register.filter
def currency_format(value, currency_code):
    """
    Format a number with the appropriate currency symbol based on the currency code.
    Args:
        value: The numeric value to format (e.g., 2558.42).
        currency_code: The ISO 4217 currency code (e.g., USD, EUR, GBP).
    Returns:
        A string with the formatted value and currency symbol (e.g., $2558.42, €2558.42).
    """
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'CAD': 'C$',
        'AUD': 'A$',
        'JPY': '¥',
        # Add more currencies as needed
    }
    symbol = currency_symbols.get(currency_code, currency_code)  # Fallback to code if symbol not found
    formatted_value = number_format(value, decimal_pos=2, force_grouping=True)
    return f"{symbol}{formatted_value}"

@register.filter
def json_escape(value):
    """
    Escapes a JSON string for safe use in HTML data attributes.
    """
    if not value:
        return '[]'
    try:
        # Ensure the input is a valid JSON string or Python object
        parsed = json.loads(value) if isinstance(value, str) else value
        # Dump to JSON and escape for HTML attribute
        json_str = json.dumps(parsed, ensure_ascii=False)
        return escape(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"JSON escape error: {e}, value: {value}")
        return '[]'
    
@register.filter
def parse_date(value):
    try:
        return datetime(value.replace('Z', '+00:00')).date()
    except (ValueError, TypeError):
        return None
    
# @register.filter
# def split(value, delimiter):
#     try:
#         return value.split(delimiter)
#     except (AttributeError, TypeError):
#         return [value] if value else []
    
@register.filter
def split(value, delimiter):
    return value.split(delimiter)
    
@register.filter
def range_filter(value, start=None):
    """
    Generate a range of numbers. If start is provided, range from start to value (inclusive).
    If only value is provided, range from 0 to value-1.
    """
    end = int(value)
    if start is not None:
        start = int(start)
        return [i for i in range(start, end + 1)]
    return [i for i in range(end)]

@register.filter
def range(value):
    return range(value)


@register.simple_tag
def locale_slugurl(slug):
    """Get URL by slug in current locale."""
    language = get_language()  # e.g., 'en'
    try:
        page = Page.objects.filter(slug=slug, locale__language_code=language).live().public().first()
        if page:
            return page.url  # Relative URL, like '/en/sitemap-page/'
        return '#'  # Fallback if not found
    except:
        return '#'
