from django import template

register = template.Library()

@register.filter
def language_to_flag(lang_code):
    # Simple mapping for common languages; extend as needed
    mapping = {
        'en-us': 'us',
        'en-gb': 'gb',
        'es': 'es',
        'fr': 'fr',
        'de': 'de',
        'it': 'it',
        'pt-br': 'br',
        'pt-pt': 'pt',
        'ja': 'jp',
        'zh-hans': 'cn',  # Simplified Chinese
        'zh-hant': 'tw',  # Traditional Chinese (Taiwan)
        # Add more: 'ar': 'sa', etc.
    }
    return mapping.get(lang_code, 'us')  # Default to UK flag