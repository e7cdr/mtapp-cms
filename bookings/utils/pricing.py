from datetime import timedelta
from decimal import Decimal
import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from bookings.models import AccommodationBooking
from bookings.tours_utils import get_exchange_rate
from tours.models import DayTourPage, FullTourPage, LandTourPage
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP  
import logging
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)

# def calculate_accommodation_price(accommodation, cleaned_data):
#     check_in = cleaned_data['check_in']
#     check_out = cleaned_data['check_out']
#     nights = (check_out - check_in).days
#     adults = cleaned_data['adults']
#     children = cleaned_data['children']

#     # 1. BASE PRICE
#     if accommodation.pricing_type == "Per_person":
#         base_per_person = accommodation.price_adult or Decimal('0')  # ← NO FALLBACK
#         child_price = accommodation.price_chd or Decimal('0')
#         base_total = (adults * base_per_person + children * child_price) * nights

#     elif accommodation.pricing_type == "Per_room":
#         # Use double room rate for 2 adults, single for 1
#         base_per_night = accommodation.price_dbl or accommodation.price_sgl or Decimal('0')
#         if adults == 1 and accommodation.price_sgl:
#             base_per_night = accommodation.price_sgl
#         base_total = base_per_night * nights

#     else:  # Combined
#         base_per_person = accommodation.price_adult or Decimal('0')
#         base_total = adults * base_per_person * nights

#     if base_total <= 0:
#         return Decimal('0.00')  # Safety

#     # 2. SEASONAL FACTOR
#     seasonal_multiplier = Decimal(str(accommodation.seasonal_factor or '1.0'))
#     price_after_seasonal = base_total * seasonal_multiplier

#     # 3. DEMAND FACTOR
#     demand_multiplier = get_demand_multiplier(accommodation, check_in)
#     final_price = price_after_seasonal * demand_multiplier

#     # 4. DISCOUNT
#     if getattr(accommodation, 'is_on_discount', False):
#         final_price *= Decimal('0.85')

#     return final_price.quantize(Decimal('0.01'))

def calculate_accommodation_price(accommodation, cleaned_data):
    logger.debug("=== calculate_accommodation_price START ===")
    logger.debug(f"cleaned_data keys: {list(cleaned_data.keys())}")
    logger.debug(f"child_ages raw: {cleaned_data.get('child_ages')!r}")
    logger.debug(f"accommodation: {accommodation}")
    logger.debug(f"pricing_type: {accommodation.pricing_type if accommodation else 'None'}")

    check_in = cleaned_data['check_in']
    check_out = cleaned_data['check_out']
    nights = (check_out - check_in).days
    adults = cleaned_data['adults']
    child_ages = cleaned_data.get('child_ages', [])

    logger.debug(f"nights: {nights}, adults: {adults}, child_ages: {child_ages} (type: {type(child_ages)})")

    # Use existing model fields
    child_min_age = getattr(accommodation, 'child_age_min', 7)
    child_max_age = getattr(accommodation, 'child_age_max', 12)
    logger.debug(f"child_min_age: {child_min_age}, child_max_age: {child_max_age}")

    # Split children into paying children and infants
    paying_children = 0
    infants = 0
    if isinstance(child_ages, list):
        for age in child_ages:
            logger.debug(f"Processing child age: {age}")
            if child_min_age <= age <= child_max_age:
                paying_children += 1
            elif age < child_min_age:
                infants += 1
    else:
        logger.warning(f"child_ages is not a list: {type(child_ages)} = {child_ages}")

    logger.debug(f"paying_children: {paying_children}, infants: {infants}")

    # Base prices
    price_adult = accommodation.price_adult or Decimal('0')
    price_child = accommodation.price_chd or Decimal('0')
    price_infant = accommodation.price_inf or Decimal('0')

    logger.debug(f"price_adult: {price_adult}, price_child: {price_child}, price_infant: {price_infant}")

    if accommodation.pricing_type == "Per_person":
        base_total = (
            adults * price_adult +
            paying_children * price_child +
            infants * price_infant
        ) * nights
    elif accommodation.pricing_type == "Per_room":
        base_per_night = accommodation.price_dbl or accommodation.price_sgl or Decimal('0')
        if adults == 1 and accommodation.price_sgl:
            base_per_night = accommodation.price_sgl
        base_total = base_per_night * nights
        base_total += (paying_children * price_child + infants * price_infant) * nights
    else:
        base_total = adults * price_adult * nights
        base_total += (paying_children * price_child + infants * price_infant) * nights

    logger.debug(f"base_total before factors: {base_total}")

    if base_total <= 0:
        logger.debug("base_total <= 0, returning 0.00")
        return Decimal('0.00')

    seasonal_multiplier = Decimal(str(getattr(accommodation, 'seasonal_factor', '1.0')))
    price_after_seasonal = base_total * seasonal_multiplier

    demand_multiplier = get_demand_multiplier(accommodation, check_in)
    final_price = price_after_seasonal * demand_multiplier

    logger.debug(f"seasonal: {seasonal_multiplier}, demand: {demand_multiplier}, final: {final_price}")

    return final_price.quantize(Decimal('0.01'))
def get_demand_multiplier(accommodation, check_in_date):
    """
    Returns  - demand_factor = 0.20 → max +20%
     - Looks at bookings in next 30 days from check_in_date
     - Increases price linearly based on occupancy
    """
    if accommodation.demand_factor <= 0:
        return Decimal('1.0')

    max_factor = Decimal(str(accommodation.demand_factor))  # e.g. 0.20
    max_capacity = accommodation.max_capacity or 20

    # Count current bookings overlapping with this period
    start_range = check_in_date
    end_range = check_in_date + timedelta(days=30)

    overlapping_bookings = AccommodationBooking.objects.filter(
        accommodation=accommodation,
        check_in__lte=end_range,
        check_out__gte=start_range,
        status__in=['PENDING_PAYMENT', 'PAID']
    )

    booked_slots = 0
    for b in overlapping_bookings:
        booked_slots += b.adults + b.children

    occupancy_rate = booked_slots / max_capacity if max_capacity > 0 else 0
    occupancy_rate = min(occupancy_rate, 1.0)  # cap at 100%

    # Linear increase: 0% → max_factor
    demand_multiplier = Decimal('1.0') + (max_factor * Decimal(str(occupancy_rate)))
    return demand_multiplier

def compute_pricing(tour_type, tour_id, form_data, session):
    model_map = {
        'full': FullTourPage,
        'land': LandTourPage,
        'day': DayTourPage,
    }
    model = model_map.get(tour_type.lower())
    if not model:
        logger.error(f"Invalid tour type: {tour_type}")
        return []

    tour = get_object_or_404(model, pk=tour_id)

    # === Extract and validate inputs safely ===
    try:
        number_of_adults = max(1, int(form_data.get('number_of_adults', 1) or 1))
        number_of_children = max(0, int(form_data.get('number_of_children', 0) or 0))
    except (ValueError, TypeError):
        number_of_adults = 1
        number_of_children = 0

    currency = form_data.get('currency', session.get('currency', 'USD')).upper()
    session['currency'] = currency

    # === Parse child ages ===
    try:
        child_ages = json.loads(form_data.get('child_ages', '[]'))
        child_ages = [int(a) for a in child_ages if isinstance(a, (int, str)) and str(a).isdigit()]
    except (json.JSONDecodeError, ValueError):
        child_ages = []

    child_age_min = getattr(tour, 'child_age_min', 7)
    infants = sum(1 for age in child_ages if age < child_age_min)
    children = len(child_ages) - infants

    max_children_per_room = getattr(tour, 'max_children_per_room', 1) or 1
    # === Factors ===
    seasonal_factor = Decimal(str(getattr(tour, 'seasonal_factor', 1.0) or '1.0'))
    exchange_rate = get_exchange_rate(currency)

    # Demand adjustment (simplified — use your existing logic if needed)
    price_adjustment = Decimal('1.0')  # You can plug in demand logic here

    # === Load prices safely ===
    try:
        price_adult = Decimal(str(getattr(tour, 'price_adult', 0) or '0'))
        price_chd = Decimal(str(getattr(tour, 'price_chd', 0) or '0'))
        price_inf = Decimal(str(getattr(tour, 'price_inf', 0) or '0'))
        price_sgl = Decimal(str(getattr(tour, 'price_sgl', 0) or '0'))
        price_dbl = Decimal(str(getattr(tour, 'price_dbl', 0) or '0'))
        price_tpl = Decimal(str(getattr(tour, 'price_tpl', 0) or '0'))
    except (InvalidOperation, ValueError):
        return [{'error': 'Invalid price configuration.', 'total_price': None}]

    pricing_type_raw = getattr(tour, 'pricing_type', None)
    if not pricing_type_raw or pricing_type_raw.strip() == '':
        logger.warning(f"Tour {tour_id} has no pricing_type set! Forcing 'Per_person' for DayTour")
        pricing_type = 'Per_person'
    else:
        pricing_type = pricing_type_raw.strip()

    # =============================================
    # 1. PER PERSON PRICING — Used by Day Tours + any tour with 'Per_person'
    # =============================================
    if pricing_type == 'Per_person':
        total_price = (
            number_of_adults * price_adult +
            children * price_chd +
            infants * price_inf
        )
        total_price *= seasonal_factor * price_adjustment * exchange_rate
        rounded_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return [{
            'singles': 0, 'doubles': 0, 'triples': 0,
            'total_rooms': 0,
            'children': children,
            'infants': infants,
            'child_ages': child_ages,
            'total_price': float(rounded_price),
            'currency': currency,
            'cheapest': True,
            'pricing_type': 'Per_person',
            'note': 'Flat rate per person'
        }]

    # =============================================
    # SMART & CURATED ROOM CONFIGURATIONS (Best Practice)
    # =============================================
    configurations = []

    # Helper to add config
    def add_config(s, d, t):
        total_rooms = s + d + t
        if total_rooms == 0:
            return
        if (children + infants) > total_rooms * max_children_per_room:
            return

        beds = s * 1 + d * 2 + t * 3
        if beds < number_of_adults:
            return

        # Calculate price
        if pricing_type == 'Per_room':
            base = s * price_sgl + d * price_dbl + t * price_tpl
        else:
            base = s * price_sgl + d * price_dbl + t * price_tpl

        total_price = (base + children * price_chd + infants * price_inf
                      ) * seasonal_factor * price_adjustment * exchange_rate
        rounded = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        configurations.append({
            'singles': s,
            'doubles': d,
            'triples': t,
            'total_rooms': total_rooms,
            'children': children,
            'infants': infants,
            'child_ages': child_ages,
            'total_price': float(rounded),
            'currency': currency,
            'cheapest': False,
            'pricing_type': pricing_type,
            'note': get_note(s, d, t)  # We'll add this
        })

    def get_note(s, d, t):
        parts = []
        if t: parts.append(f"{t} Triple" + ("s" if t > 1 else ""))
        if d: parts.append(f"{d} Double" + ("s" if d > 1 else ""))
        if s: parts.append(f"{s} Single" + ("s" if s > 1 else ""))
        note = " + ".join(parts)
        if s + d + t == number_of_adults // 2 + (number_of_adults % 2):  # rough perfect fit
            note += " (recommended)"
        return note

    # 1. Best: Use as many triples as possible
    for t in range(min(number_of_adults // 3 + 1, number_of_adults // 2 + 1)):
        remaining = number_of_adults - t * 3
        if remaining < 0: continue
        d = remaining // 2
        s = remaining % 2
        add_config(s, d, t)

    # 2. Best sharing with doubles
    d = number_of_adults // 2
    s = number_of_adults % 2
    add_config(s, d, 0)

    # 3. One extra room variations
    if number_of_adults >= 2:
        add_config(number_of_adults - 2, 1, 0)  # 1 double + rest singles
        if number_of_adults >= 3:
            add_config(number_of_adults - 3, 0, 1)  # 1 triple + rest singles

    # 4. All singles (privacy option)
    add_config(number_of_adults, 0, 0)

    # 5. Mixed with one extra double
    if number_of_adults >= 2:
        add_config(number_of_adults - 2, 2, 0)  # 2 doubles (one empty bed)
    for c in configurations:
        beds = c['singles'] + c['doubles'] * 2 + c['triples'] * 3
        extra_beds = beds - number_of_adults
        if extra_beds <= 1 and c['total_rooms'] <= number_of_adults // 2 + 2:
            c['recommended'] = True
    # Remove duplicates and sort
    seen = set()
    unique_configs = []
    for c in configurations:
        key = (c['singles'], c['doubles'], c['triples'])
        if key not in seen:
            seen.add(key)
            unique_configs.append(c)

    unique_configs.sort(key=lambda x: x['total_price'])
    if unique_configs:
        unique_configs[0]['cheapest'] = True

    logger.debug(f"Generated {len(unique_configs)} curated configurations")
    # Filter out options with too many rooms (too much waste)
    filtered = []
    for c in configurations:
        if c['total_rooms'] <= number_of_adults // 2 + 3:  # Allow small overflow
            filtered.append(c)

    configurations = filtered
    return unique_configs if unique_configs else [{'error': 'No valid configuration'}]

def render_pricing(request, tour_type, tour_id):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        logger.warning(f"Non-AJAX request to render_pricing: {request.method} from {request.META.get('HTTP_REFERER')}")
        return HttpResponse("AJAX required", status=400)

    logger.debug(f"AJAX pricing request: {request.POST}")
    logger.debug(f"render_pricing called with POST: {request.POST}")

    # Prioritize currency from POST data
    currency = request.POST.get('currency', request.session.get('currency', 'USD')).upper()
    request.session['currency'] = currency  # Update session currency
    logger.debug(f"Selected currency: {currency}")

    configurations = compute_pricing(tour_type, tour_id, request.POST, request.session)

    model_map = {'full': FullTourPage, 'land': LandTourPage, 'day': DayTourPage}
    tour = get_object_or_404(model_map.get(tour_type.lower()), pk=tour_id)

    form_errors = []
    if not configurations:
        form_errors.append("No valid pricing options generated.")
        logger.warning("No configurations generated in render_pricing")

    # === Adults from POST (safe) ===
    number_of_adults_str = request.POST.get('number_of_adults', '1')
    number_of_adults = int(number_of_adults_str) if number_of_adults_str and number_of_adults_str.strip() != '' else 1

    # === Children & Infants from compute_pricing (correct count based on ages) ===
    if configurations:
        config = configurations[0]  # For Per_person there's only one config
        number_of_infants = config.get('infants', 0)
        number_of_children = config.get('children', 0)
        child_ages_for_template = config.get('child_ages', [])
    else:
        number_of_infants = 0
        number_of_children = 0
        child_ages_for_template = []

    exchange_rate = get_exchange_rate(currency)
    logger.debug(f"Using currency: {currency}, exchange_rate: {exchange_rate}")

    configurations_json = json.dumps(configurations, ensure_ascii=False)
    try:
        json.loads(configurations_json)
        logger.debug("configurations_json is valid JSON")
    except json.JSONDecodeError as e:
        logger.error(f"configurations_json is invalid JSON: {e}")
        form_errors.append("Error generating pricing data.")
        configurations = []

    context = {
        'configurations': configurations,
        'form_errors': form_errors,
        'tour': tour,
        'configurations_json': configurations_json,
        'child_age_min': getattr(tour, 'child_age_min', 7),
        'child_age_max': int(getattr(tour, 'child_age_max', 12)),
        'children_exceed_room_limit': False,
        'max_children_per_room': getattr(tour, 'max_children_per_room', 1),
        'currency': currency,
        'number_of_adults': number_of_adults,
        'number_of_infants': number_of_infants,
        'number_of_children': number_of_children,
        'child_ages': child_ages_for_template,
    }
    context['room_based_pricing'] = tour.pricing_type in ['Per_room', 'Combined']
    context['is_room_based'] = tour.pricing_type in ('Per_room', 'Combined')

    response_content = render_to_string('bookings/partials/pricing_options.html', context, request=request)
    logger.debug(f"Rendered pricing_options.html with context: {context}")
    return HttpResponse(response_content, content_type='text/html')

def get_pricing_tier(tour, number_of_adults):
    """
    Return the correct pricing tier for Combined pricing based on number of adults.
    Falls back gracefully to old flat pricing if StreamField is empty.
    """
    from decimal import Decimal

    # If no tiers defined → fall back to old flat fields (backward compatible!)
    if not hasattr(tour, 'combined_pricing_tiers') or not tour.combined_pricing_tiers:
        logger.debug("No combined_pricing_tiers found → using legacy flat pricing")
        adult_price = Decimal(str(getattr(tour, 'price_adult', '0') or '0'))
        sgl_supp = Decimal(str(getattr(tour, 'price_sgl', '0') or '0')) - adult_price
        dbl_disc = adult_price - Decimal(str(getattr(tour, 'price_dbl', '0') or '0'))
        tpl_disc = adult_price - Decimal(str(getattr(tour, 'price_tpl', '0') or '0'))
        
        return {
            'price_adult': adult_price,
            'sgl_supplement': sgl_supp,
            'dbl_discount': dbl_disc,
            'tpl_discount': tpl_disc,
        }

    for block in tour.combined_pricing_tiers:
        tier = block.value
        min_pax = tier.get('min_pax', 1)
        max_pax = tier.get('max_pax') or 99999
        
        if min_pax <= number_of_adults <= max_pax:
            return {
                'price_adult': Decimal(str(tier['price_adult'])),
                'sgl_supplement': Decimal(str(tier['price_sgl_supplement'] or '0')),
                'dbl_discount': Decimal(str(tier['price_dbl_discount'] or '0')),
                'tpl_discount': Decimal(str(tier['price_tpl_discount'] or '0')),
                'child_percent': Decimal(str(tier['child_price_percent'] or '60')) / 100,

                # INFANT LOGIC — FULLY FLEXIBLE
                'infant_price_type': tier.get('infant_price_type', 'free'),
                'infant_percent_of_adult': Decimal(str(tier.get('infant_percent_of_adult') or '10')) / 100,
                'infant_fixed_amount': Decimal(str(tier.get('infant_fixed_amount') or '0')),
            }

    # Fallback: use last tier if no match
    last = tour.combined_pricing_tiers[-1].value
    return {
        'price_adult': Decimal(str(tier['price_adult'])),
        'sgl_supplement': Decimal(str(tier['price_sgl_supplement'] or '0')),
        'dbl_discount': Decimal(str(tier['price_dbl_discount'] or '0')),
        'tpl_discount': Decimal(str(tier['price_tpl_discount'] or '0')),
        'child_percent': Decimal(str(tier['child_price_percent'] or '60')) / 100,

        # INFANT LOGIC — FULLY FLEXIBLE
        'infant_price_type': tier.get('infant_price_type', 'free'),
        'infant_percent_of_adult': Decimal(str(tier.get('infant_percent_of_adult') or '10')) / 100,
        'infant_fixed_amount': Decimal(str(tier.get('infant_fixed_amount') or '0')),
    }


