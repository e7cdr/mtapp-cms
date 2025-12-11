from datetime import date, timedelta
from decimal import Decimal
import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from bookings.models import AccommodationBooking
from bookings.tours_utils import calculate_demand_factor, get_30_day_used_slots, get_exchange_rate, get_remaining_capacity
from tours.models import DayTourPage, LandTourPage
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP  
import logging
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)

def calculate_accommodation_price(accommodation, cleaned_data):
    check_in = cleaned_data['check_in']
    check_out = cleaned_data['check_out']
    nights = (check_out - check_in).days
    adults = cleaned_data['adults']
    children = cleaned_data['children']

    # 1. BASE PRICE
    if accommodation.pricing_type == "Per_person":
        base_per_person = accommodation.price_adult or Decimal('0')  # ← NO FALLBACK
        child_price = accommodation.price_chd or Decimal('0')
        base_total = (adults * base_per_person + children * child_price) * nights

    elif accommodation.pricing_type == "Per_room":
        # Use double room rate for 2 adults, single for 1
        base_per_night = accommodation.price_dbl or accommodation.price_sgl or Decimal('0')
        if adults == 1 and accommodation.price_sgl:
            base_per_night = accommodation.price_sgl
        base_total = base_per_night * nights

    else:  # Combined
        base_per_person = accommodation.price_adult or Decimal('0')
        base_total = adults * base_per_person * nights

    if base_total <= 0:
        return Decimal('0.00')  # Safety

    # 2. SEASONAL FACTOR
    seasonal_multiplier = Decimal(str(accommodation.seasonal_factor or '1.0'))
    price_after_seasonal = base_total * seasonal_multiplier

    # 3. DEMAND FACTOR
    demand_multiplier = get_demand_multiplier(accommodation, check_in)
    final_price = price_after_seasonal * demand_multiplier

    # 4. DISCOUNT
    if getattr(accommodation, 'is_on_discount', False):
        final_price *= Decimal('0.85')

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

def render_pricing(request, tour_type, tour_id):
    logger.debug(f"render_pricing called with POST: {request.POST}")
    # Prioritize currency from POST data
    currency = request.POST.get('currency', request.session.get('currency', 'USD')).upper()
    request.session['currency'] = currency  # Update session currency
    logger.debug(f"Selected currency: {currency}")

    configurations = compute_pricing(tour_type, tour_id, request.POST, request.session)
    model_map = {'full': "FullTourPage", 'land': LandTourPage, 'day': DayTourPage}
    tour = get_object_or_404(model_map.get(tour_type.lower()), pk=tour_id)
    form_errors = []
    if not configurations:
        form_errors.append("No valid pricing options generated.")
        logger.warning("No configurations generated in render_pricing")

    try:
        child_ages_input = request.POST.get('child_ages', '[]')
        child_ages = json.loads(child_ages_input) if child_ages_input else []
        child_ages = [int(age) for age in child_ages if isinstance(age, (int, str)) and str(age).isdigit() and 0 <= int(age) <= tour.child_age_max]
    except (json.JSONDecodeError, ValueError, TypeError):
        child_ages = []

    # Safe int parses for adults/children (handle empty string)
    number_of_adults_str = request.POST.get('number_of_adults', '1')
    number_of_adults = int(number_of_adults_str) if number_of_adults_str and number_of_adults_str.strip() != '' else 1

    number_of_children_str = request.POST.get('number_of_children', '0')
    number_of_children = int(number_of_children_str) if number_of_children_str and number_of_children_str.strip() != '' else 0

    infants = sum(1 for age in child_ages if age < tour.child_age_min) if child_ages else 0

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
        'child_age_max': int(getattr(tour, 'child_age_max', 12)),  # Fixed typo: child_age_axn -> child_age_max
        'children_exceed_room_limit': False,
        'max_children_per_room': getattr(tour, 'max_children_per_room', 1),
        'currency': currency,
        'number_of_adults': number_of_adults,
        'number_of_infants': infants,
        'child_ages': child_ages,
        'number_of_children': number_of_children
        
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

def compute_pricing(tour_type, tour_id, form_data, session):
    logger.debug(f"compute_pricing inputs: form_data={form_data}, tour_type={tour_type}, tour_id={tour_id}")
    model_map = {'full': "FullTourPage", 'land': LandTourPage, 'day': DayTourPage}
    model = model_map.get(tour_type.lower())
    if not model:
        logger.error(f"Invalid tour type: {tour_type}")
        return []

    tour = get_object_or_404(model.objects.specific(), pk=tour_id)  # Ensures polymorphic fields
    logger.debug(f"Fetched tour: {tour.title}, type={tour_type}, id={tour_id}")

    form_errors = []
    number_of_adults_input = form_data.get('number_of_adults', 1)
    if number_of_adults_input == '':
        number_of_adults = 1
    else:
        try:
            number_of_adults = int(number_of_adults_input)
            if number_of_adults < 0:
                form_errors.append("Number of adults cannot be negative.")
                number_of_adults = 1
        except (ValueError, TypeError):
            form_errors.append("Please provide a valid number of adults.")
            number_of_adults = 1

    number_of_children_input = form_data.get('number_of_children', 0)
    if number_of_children_input == '':
        number_of_children = 0
    else:
        try:
            number_of_children = int(number_of_children_input)
            if number_of_children < 0:
                form_errors.append("Number of children cannot be negative.")
                number_of_children = 0
        except (ValueError, TypeError):
            form_errors.append("Please provide a valid number of children.")
            number_of_children = 0

    payment_type = form_data.get('payment_type', 'regular')
    travel_date = form_data.get('travel_date')
    currency = form_data.get('currency', session.get('currency', 'USD')).upper()
    session['currency'] = currency

    # Demand factor from capacity (fallback if no date)
    if travel_date:
        try:
            travel_date = date.fromisoformat(travel_date)
            capacity = get_remaining_capacity(tour_id, travel_date, tour.__class__, tour.duration_days)
            if 'total_remaining' in capacity:
                demand_factor = calculate_demand_factor(capacity['total_remaining'], sum(d['total_daily'] for d in capacity['per_day']))
            else:
                demand_factor = Decimal('0')
                logger.warning("No capacity data—default demand_factor=0")
        except ValueError:
            demand_factor = Decimal('0')
            logger.warning(f"Invalid travel_date '{travel_date}'—default demand_factor=0")
    else:
        demand_factor = Decimal('0')
        logger.debug("No travel_date—default demand_factor=0")
    price_adjustment = Decimal('1') + Decimal('0.2') * demand_factor
    logger.debug(f"Received number_of_adults: {number_of_adults}, number_of_children: {number_of_children}, payment_type: {payment_type}, travel_date: {travel_date}, currency: {currency}")

    if form_errors:
        logger.warning(f"Form errors: {form_errors}")
        return []

    # Child ages parsing
    child_ages_input = form_data.get('child_ages', '[]')
    if child_ages_input == '':
        child_ages = []
    else:
        if isinstance(child_ages_input, list):
            child_ages = child_ages_input
        else:
            try:
                child_ages = json.loads(child_ages_input)
                if not isinstance(child_ages, list):
                    logger.warning(f"Invalid child_ages: {child_ages_input}, expected a list")
                    child_ages = []
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid child_ages JSON: {child_ages_input}, error: {str(e)}")
                child_ages = []
    try:
        child_ages = [int(age) for age in child_ages if 0 <= int(age) <= tour.child_age_max][:number_of_children]
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid child ages values: {child_ages}, error: {str(e)}")
        child_ages = []


    child_age_min = tour.child_age_min
    child_age_max = tour.child_age_max
    infants = sum(1 for age in child_ages if age < child_age_min)
    children = number_of_children if not child_ages else len(child_ages) - infants
    if number_of_children > 0 and len(child_ages) != number_of_children:
        logger.warning(f"Child ages count ({len(child_ages)}) does not match number_of_children ({number_of_children})")
        return []

    if not child_ages and number_of_children > 0:
        child_ages = [child_age_min] * number_of_children
        children = number_of_children
        infants = 0
    max_children_per_room = getattr(tour, 'max_children_per_room', 1) or 1  # FIXED: or 1 handles None
    logger.debug(f"Parsed: infants={infants}, children={children}, max_children_per_room={max_children_per_room}")
    # Seasonal factor from model
    try:
        seasonal_factor = Decimal(str(tour.seasonal_factor or '1.0'))  # FIXED: Null default to 1.0
        if seasonal_factor <= 0:
            logger.warning(f"Invalid seasonal_factor in tour {tour_id}: {seasonal_factor}, using default 1.0")
            seasonal_factor = Decimal('1.0')
    except (InvalidOperation, ValueError, TypeError):
        logger.warning(f"Invalid seasonal_factor in tour {tour_id}: {tour.seasonal_factor}, using default 1.0")
        seasonal_factor = Decimal('1.0')
    logger.debug(f"Seasonal factor from tour: {seasonal_factor}")

    # Demand factor from 30-day capacity (global—scale model demand_factor)
    demand_info = get_30_day_used_slots(tour_id, tour.__class__)
    full_percent = demand_info['full_percent']
    model_demand_factor = Decimal(str(getattr(tour, 'demand_factor', '0') or '0'))  # FIXED: Null default to 0
    demand_factor = model_demand_factor * full_percent  # e.g., 0.2 * 0.5 = 0.1 (10% adjustment)
    logger.debug(f"30-day used_slots={demand_info['used_slots']}, full_percent={full_percent}, model_demand_factor={model_demand_factor}, demand_factor={demand_factor}")
    price_adjustment = Decimal('1') + demand_factor  # 1 + 0.1 = 1.1 (10%)
    logger.debug(f"Demand factor from tour: {demand_factor}, Price adjustment: {price_adjustment}")

    # Use global get_exchange_rate
    exchange_rate = get_exchange_rate(currency)
    if exchange_rate <= Decimal('0'):
        logger.error(f"Invalid exchange rate for {currency}: {exchange_rate}, falling back to USD")
        currency = 'USD'
        session['currency'] = currency
        exchange_rate = Decimal('1.0')
    logger.debug(f"Exchange rate for {currency}: {exchange_rate}")

    # Pricing for FullTour - FIXED: Add null defaults & try/except
    if tour_type.lower() == 'full':
        try:
            if payment_type == 'cash' and all(getattr(tour, f'price_{field}_cash') not in (None, '') for field in ['sgl', 'dbl', 'tpl', 'chd', 'inf']):
                price_sgl = Decimal(str(tour.price_sgl_cash or '0'))
                price_dbl = Decimal(str(tour.price_dbl_cash or '0'))
                price_tpl = Decimal(str(tour.price_tpl_cash or '0'))
                price_chd = Decimal(str(tour.price_chd_cash or '0'))
                price_inf = Decimal(str(tour.price_inf_cash or '0'))
                price_adult = price_sgl
                logger.debug(f"Using cash pricing for FullTour: sgl={price_sgl}, dbl={price_dbl}, tpl={price_tpl}, chd={price_chd}, inf={price_inf}")
            else:
                price_sgl = Decimal(str(tour.price_sgl_regular or '0'))
                price_dbl = Decimal(str(tour.price_dbl_regular or '0'))
                price_tpl = Decimal(str(tour.price_tpl_regular or '0'))
                price_chd = Decimal(str(tour.price_chd_regular or '0'))
                price_inf = Decimal(str(tour.price_inf_regular or '0'))
                price_adult = price_sgl
                logger.debug(f"Using regular pricing for FullTour: sgl={price_sgl}, dbl={price_dbl}, tpl={price_tpl}, chd={price_chd}, inf={price_inf}")
        except (InvalidOperation, ValueError, TypeError) as e:
            logger.error(f"Decimal conversion failed for full tour {tour_id}: {e} - Prices: sgl={tour.price_sgl_regular}, etc.")
            price_sgl = price_dbl = price_tpl = price_chd = price_inf = price_adult = Decimal('0')

    elif tour_type.lower() == 'land':
        try:
            price_sgl = Decimal(str(tour.price_sgl or '0'))
            price_dbl = Decimal(str(tour.price_dbl or '0'))
            price_tpl = Decimal(str(tour.price_tpl or '0'))
            price_chd = Decimal(str(tour.price_chd or '0'))
            price_inf = Decimal(str(tour.price_inf or '0'))

            # FIXED: Set price_adult based on pricing_type
            if tour.pricing_type == 'Per_room':
                price_adult = price_sgl  # Use room SGL as adult base (your original logic)
            else:  # Per_person
                price_adult = Decimal(str(tour.price_adult or '0'))  # Use dedicated adult price

            logger.debug(f"Using pricing for LandTour: sgl={price_sgl}, adult={price_adult}, chd={price_chd}, inf={price_inf}")
        except (InvalidOperation, ValueError, TypeError) as e:
            logger.error(f"Decimal conversion failed for land tour {tour_id}: {e}")
            price_sgl = price_dbl = price_tpl = price_chd = price_inf = price_adult = Decimal('0')

    else:  # 'day'
        try:
            if tour_type.lower() != 'day':
                logger.warning(f"Invalid pricing_type '{tour.pricing_type}' for {tour_type} tour {tour_id}; skipping configs")
                return []  # Or raise ValueError for strict
            price_adult = Decimal(str(tour.price_adult or '0'))
            price_chd = Decimal(str(tour.price_child or '0'))  # Note: price_child? Confirm field name
            price_inf = Decimal(str(tour.price_inf or '0'))
            logger.debug(f"Using pricing for DayTour: adult={price_adult}, child={price_chd}, inf={price_inf}")
        except (InvalidOperation, ValueError, TypeError) as e:
            logger.error(f"Decimal conversion failed for day tour {tour_id}: {e} - Prices: adult={tour.price_adult}, etc.")
            price_adult = price_chd = price_inf = Decimal('0')

    configurations = []
    children_exceed_room_limit = False

    if number_of_adults == 0 and (children + infants > 0):
        logger.warning("No adults with children/infants")
        return []

    pricing_type = getattr(tour, 'pricing_type', 'Per_person')

    # ──────────────────────────────────────────────────────
    # 1. PER PERSON (Day tours + Land/Full with Per_person)
    # ──────────────────────────────────────────────────────
    if tour_type.lower() == 'day' or pricing_type == 'Per_person':
        total_price = number_of_adults * price_adult + children * price_chd + infants * price_inf
        total_price *= seasonal_factor * price_adjustment * exchange_rate
        rounded_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        configurations = [{
            'singles': 0, 'doubles': 0, 'triples': 0,
            'total_rooms': 0,
            'children': children,
            'infants': infants,
            'child_ages': child_ages,
            'total_price': float(rounded_price),
            'currency': currency,
            'cheapest': True,
            'pricing_type': 'Per Person'
        }]
        return configurations

    # ──────────────────────────────────────────────────────
    # 2. PER ROOM & COMBINED — same room loop, different math
    # ──────────────────────────────────────────────────────
    seen = set()
    configurations = []
    children_exceed_room_limit = False

    for singles in range(number_of_adults + 1):
        rem = number_of_adults - singles
        for doubles in range((rem // 2) + 1):
            rem2 = rem - doubles * 2
            for triples in range((rem2 // 3) + 1):
                if rem2 - triples * 3 != 0:
                    continue

                total_rooms = singles + doubles + triples
                if total_rooms == 0:
                    continue

                # Check max children per room rule
                if (children + infants) > total_rooms * max_children_per_room:
                    children_exceed_room_limit = True
                    continue

                # ───── PRICE CALCULATION ─────
                if pricing_type == 'Per_room':
                    base_price = (
                        singles * price_sgl +
                        doubles * price_dbl +
                        triples * price_tpl
                    )
                    total_price = base_price + children * price_chd + infants * price_inf

                elif pricing_type == 'Combined':
                    # Get the correct tier for this number of adults
                    tier = get_pricing_tier(tour, number_of_adults)

                    # Adult base price
                    adult_base = number_of_adults * tier['price_adult']

                    # Room sharing supplements/discounts (per person!)
                    supplement = (
                        singles * tier['sgl_supplement'] +
                        (doubles * 2) * (-tier['dbl_discount']) +   # 2 people in double
                        (triples * 3) * (-tier['tpl_discount'])    # 3 people in triple
                    )

                    adults_total = adult_base + supplement

                    # CHILD PRICE — % of adult base
                    child_price = tier['price_adult'] * tier['child_percent']

                    # INFANT PRICE — FULLY FLEXIBLE
                    infant_price_type = tier['infant_price_type']
                    if infant_price_type == 'free':
                        infant_price = Decimal('0')
                    elif infant_price_type == 'percent':
                        infant_price = tier['price_adult'] * tier['infant_percent_of_adult']
                    elif infant_price_type == 'fixed':
                        infant_price = tier['infant_fixed_amount']
                    else:
                        infant_price = Decimal('0')  # safety

                    # FINAL PRICE BEFORE ADJUSTMENTS
                    total_price = adults_total + (children * child_price) + (infants * infant_price)

                else:
                    continue  # unknown pricing type

                # Apply seasonal, demand, and currency factors
                total_price *= seasonal_factor * price_adjustment * exchange_rate
                rounded_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                # Avoid duplicate room combos
                key = (singles, doubles, triples)
                if key in seen:
                    continue
                seen.add(key)

                configurations.append({
                    'singles': singles,
                    'doubles': doubles,
                    'triples': triples,
                    'total_rooms': total_rooms,
                    'children': children,
                    'infants': infants,
                    'child_ages': child_ages,
                    'total_price': float(rounded_price),
                    'currency': currency,
                    'cheapest': False,
                    'pricing_type': 'Combined',
                })

    # Sort and mark cheapest
    if configurations:
        configurations.sort(key=lambda x: x['total_price'])
        configurations[0]['cheapest'] = True
    else:
        # ONLY if children exceed room limit → show clear message
        if children_exceed_room_limit:
            configurations = [{
                'error': f'Too many children/infants. Maximum {max_children_per_room} per room allowed. You might need to add more adults',
                'total_price': None,  # ← None = frontend shows message, not $0.00
                'blocked': True
            }]
        else:
            configurations = [{
                'error': 'No pricing options available for the selected criteria.',
                'total_price': None
            }]

    return configurations
