from django import template


register = template.Library()

@register.filter
def verbose_name(obj, field_name):
    """
    Usage: {{ tour|verbose_name:"collect_price" }}
    """
    try:
        return obj._meta.get_field(field_name).verbose_name.title()
    except:
        return field_name.replace('_', ' ').title()

@register.filter
def verbose_name_plural(obj):
    return obj._meta.verbose_name_plural.title()