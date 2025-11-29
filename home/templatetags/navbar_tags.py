from django import template
from django.conf import settings
from django.utils import translation
from wagtail.models import Site, Locale
from tours.models import ToursIndexPage  # Keep if needed for .specific()
from wagtail.models import Page

register = template.Library()

@register.simple_tag(takes_context=True)
def get_navbar_pages(context):
    """
    Returns top-level menu pages for the current locale, already specific().
    """
    request = context.get('request')
    if not request:
        return Page.objects.none()

    site = Site.find_for_request(request)
    locale = Locale.get_active()               # wagtail_localize helper (or fallback below)

    # Fallback if wagtail_localize not active
    if not locale:
        language = translation.get_language() or settings.LANGUAGE_CODE
        locale = Locale.objects.get(language_code=language.split('-')[0])

    root = site.root_page.localized  # automatically the translation in active locale
    return root.get_children().live().public().in_menu().specific()
