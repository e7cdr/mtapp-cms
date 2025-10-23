from django import template
from django.utils import translation
from wagtail.models import Site, Locale
from tours.models import ToursIndexPage  # Keep if needed for .specific()

register = template.Library()

@register.simple_tag(takes_context=True)
def get_navbar_pages(context):
    """Retrieve top-level pages for the navigation bar, filtered by current locale."""
    request = context['request']
    language = translation.get_language()  # e.g., 'en' from URL prefix or middleware
    
    try:
        locale = Locale.objects.get(language_code=language)
    except Locale.DoesNotExist:
        locale = Locale.get_default()  # Fallback to default locale
    
    site = Site.find_for_request(request)
    # Get the root page translated to the current locale
    root = site.root_page.get_translation(locale)
    
    # Return direct children (top-level nav items) for this locale only
    return root.get_children().live().public().in_menu()

@register.simple_tag
def get_staff_pages():
    return ['ITem 4', 'Item 5', 'Item 6']


#TODO: Get tour pages and insert them in a dropdown
@register.simple_tag
def get_tour_pages():
    return ['ITem 7', 'Item 8', 'Item 9']