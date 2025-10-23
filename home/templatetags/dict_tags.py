from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, [])

@register.filter
def multiply(value, arg):
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0  # Return 0 instead of value to avoid incorrect counts
    
@register.filter
def select_special_tours(items):
    special_tours = []
    for dest, tours in items:
        for tour in tours:
            if tour.is_on_discount or tour.is_special_offer:
                special_tours.append(tour)
    return special_tours

@register.filter
def select_all_inclusive_tours(items):
    all_inclusive_tours = []
    for dest, tours in items:
        for tour in tours:
            if tour.tour_type_val == 'full' and tour.is_all_inclusive:
                all_inclusive_tours.append(tour)
    return all_inclusive_tours