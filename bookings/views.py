import os
import json
import logging
import requests
from io import BytesIO
from decimal import Decimal
from datetime import datetime, timedelta
from django.urls import reverse
from django.conf import settings
from reportlab.lib import colors
from django.utils import timezone
from reportlab.lib.units import mm
from django.contrib import messages
import urllib
from partners.models import Partner
from reportlab.lib.pagesizes import A4
from django.core.mail import send_mail
from bookings.forms import ProposalForm
from django.core.paginator import Paginator
from django.contrib.messages import get_messages
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from tours.models import FullTour, LandTour, DayTour
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from home.templatetags.custom_filters import parse_date
from django.shortcuts import get_object_or_404, render, redirect
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from bookings.models import ExchangeRate, Proposal, Booking, ProposalConfirmationToken
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageTemplate, Frame, HRFlowable, KeepTogether

logger = logging.getLogger(__name__)


def compute_pricing(tour_type, tour_id, form_data, session):
    """
    Compute pricing configurations for a tour based on form data.
    Uses seasonal_factor, demand_factor, and infant pricing from the tour model.
    Returns a list of configuration dictionaries.
    """
    logger.debug(f"compute_pricing inputs: form_data={form_data}, tour_type={tour_type}, tour_id={tour_id}")
    model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
    model = model_map.get(tour_type.lower())
    if not model:
        logger.error(f"Invalid tour type: {tour_type}")
        return []

    tour = get_object_or_404(model, pk=tour_id)
    logger.debug(f"Fetched tour: {tour.title}, type={tour_type}, id={tour_id}")

    form_errors = []
    number_of_adults_input = form_data.get('number_of_adults', 1)
    try:
        number_of_adults = int(number_of_adults_input)
        if number_of_adults < 0:
            form_errors.append("Number of adults cannot be negative.")
            number_of_adults = 1
    except (ValueError, TypeError):
        form_errors.append("Please provide a valid number of adults.")
        number_of_adults = 1

    number_of_children_input = form_data.get('number_of_children', 0)
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
    logger.debug(f"Received number_of_adults: {number_of_adults}, number_of_children: {number_of_children}, payment_type: {payment_type}, travel_date: {travel_date}, currency: {currency}")

    if form_errors:
        logger.warning(f"Form errors: {form_errors}")
        return []

    # Child ages parsing
    child_ages_input = form_data.get('child_ages', '[]')
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
    if len(child_ages) != number_of_children:
        logger.warning(f"Child ages count ({len(child_ages)}) does not match number_of_children ({number_of_children})")
        return []
    if not child_ages and number_of_children > 0:
        child_ages = [child_age_min] * number_of_children
        children = number_of_children
        infants = 0
    max_children_per_room = getattr(tour, 'max_children_per_room', 1)
    logger.debug(f"Parsed: infants={infants}, children={children}, max_children_per_room={max_children_per_room}")

    # Seasonal factor from model
    try:
        seasonal_factor = Decimal(str(tour.seasonal_factor))
        if seasonal_factor <= 0:
            logger.warning(f"Invalid seasonal_factor in tour {tour_id}: {seasonal_factor}, using default 1.0")
            seasonal_factor = Decimal('1.0')
    except (ValueError, TypeError):
        logger.warning(f"Invalid seasonal_factor in tour {tour_id}: {tour.seasonal_factor}, using default 1.0")
        seasonal_factor = Decimal('1.0')
    logger.debug(f"Seasonal factor from tour: {seasonal_factor}")

    # Demand factor from model
    try:
        demand_factor = Decimal(str(tour.demand_factor))
        if demand_factor < 0:
            logger.warning(f"Invalid demand_factor in tour {tour_id}: {demand_factor}, using default 0")
            demand_factor = Decimal('0')
    except (ValueError, TypeError):
        logger.warning(f"Invalid demand_factor in tour {tour_id}: {tour.demand_factor}, using default 0")
        demand_factor = Decimal('0')
    price_adjustment = Decimal('1') + Decimal('0.2') * demand_factor
    logger.debug(f"Demand factor from tour: {demand_factor}, Price adjustment: {price_adjustment}")

    # Use global get_exchange_rate
    exchange_rate = get_exchange_rate(currency)
    if exchange_rate <= Decimal('0'):
        logger.error(f"Invalid exchange rate for {currency}: {exchange_rate}, falling back to USD")
        currency = 'USD'
        session['currency'] = currency
        exchange_rate = Decimal('1.0')
    logger.debug(f"Exchange rate for {currency}: {exchange_rate}")

    # Pricing for FullTour
    if tour_type.lower() == 'full':
        if payment_type == 'cash' and all(getattr(tour, f'price_{field}_cash') is not None for field in ['sgl', 'dbl', 'tpl', 'chd', 'inf']):
            price_sgl = Decimal(str(tour.price_sgl_cash))
            price_dbl = Decimal(str(tour.price_dbl_cash))
            price_tpl = Decimal(str(tour.price_tpl_cash))
            price_chd = Decimal(str(tour.price_chd_cash))
            price_inf = Decimal(str(tour.price_inf_cash))
            logger.debug(f"Using cash pricing for FullTour: sgl={price_sgl}, dbl={price_dbl}, tpl={price_tpl}, chd={price_chd}, inf={price_inf}")
        else:
            price_sgl = Decimal(str(tour.price_sgl_regular))
            price_dbl = Decimal(str(tour.price_dbl_regular))
            price_tpl = Decimal(str(tour.price_tpl_regular))
            price_chd = Decimal(str(tour.price_chd_regular))
            price_inf = Decimal(str(tour.price_inf_regular))
            logger.debug(f"Using regular pricing for FullTour: sgl={price_sgl}, dbl={price_dbl}, tpl={price_tpl}, chd={price_chd}, inf={price_inf}")
    elif tour_type.lower() == 'land':
        price_sgl = Decimal(str(tour.price_sgl))
        price_dbl = Decimal(str(tour.price_dbl))
        price_tpl = Decimal(str(tour.price_tpl))
        price_chd = Decimal(str(tour.price_chd))
        price_inf = Decimal(str(tour.price_inf))
        logger.debug(f"Using pricing for LandTour: sgl={price_sgl}, dbl={price_dbl}, tpl={price_tpl}, chd={price_chd}, inf={price_inf}")
    else:
        price_adult = Decimal(str(tour.price_adult))
        price_chd = Decimal(str(tour.price_child))
        price_inf = Decimal(str(tour.price_inf))
        logger.debug(f"Using pricing for DayTour: adult={price_adult}, child={price_chd}, inf={price_inf}")

    configurations = []
    children_exceed_room_limit = False
    if number_of_adults == 0 and (children > 0 or infants > 0):
        logger.warning("No adult provided with children or infants")
        return []

    if tour_type.lower() in ['land', 'full'] and tour.pricing_type == 'per_room':
        for singles in range(number_of_adults + 1):
            for doubles in range((number_of_adults - singles) // 2 + 1):
                remaining_adults = number_of_adults - singles - doubles * 2
                if remaining_adults < 0:
                    continue
                triples = remaining_adults // 3
                extra_adults = remaining_adults % 3
                adjusted_singles = singles + extra_adults
                total_adults = adjusted_singles + doubles * 2 + triples * 3
                if total_adults != number_of_adults:
                    logger.debug(f"Skipping invalid config: adjusted_singles={adjusted_singles}, doubles={doubles}, triples={triples}, total_adults={total_adults}")
                    continue
                total_rooms = adjusted_singles + doubles + triples
                if total_rooms == 0:
                    logger.debug("Skipping config with zero rooms")
                    continue
                total_children = children + infants
                if total_children > total_rooms * max_children_per_room:
                    logger.debug(f"Children+Infants ({total_children}) exceed limit ({total_rooms * max_children_per_room}) for config: adjusted_singles={adjusted_singles}, doubles={doubles}, triples={triples}")
                    children_exceed_room_limit = True
                    continue
                total_price = (
                    (adjusted_singles * price_sgl) +
                    (doubles * price_dbl) +
                    (triples * price_tpl) +
                    (children * price_chd) +
                    (infants * price_inf)
                )
                total_price = total_price * seasonal_factor * price_adjustment
                total_price = total_price * exchange_rate
                # total_price = total_price + (total_price * Decimal('0.05')) #5% increase

                config = {
                    'singles': adjusted_singles,
                    'doubles': doubles,
                    'triples': triples,
                    'children': children,
                    'infants': infants,
                    'child_ages': child_ages,
                    'total_price': float(round(total_price, 2)),
                    'currency': currency,
                    'total_rooms': total_rooms
                }
                configurations.append(config)
                logger.debug(f"Generated config: {config}")

        unique_configs = []
        seen = set()
        for config in configurations:
            key = (config['singles'], config['doubles'], config['triples'], config['children'], config['infants'])
            if key not in seen:
                seen.add(key)
                unique_configs.append(config)
        configurations = sorted(unique_configs, key=lambda x: x['total_price'])
        if configurations:
            configurations[0]['cheapest'] = True
        logger.debug(f"Final configurations: {configurations}")

    elif tour_type.lower() in ['land', 'full'] and tour.pricing_type == 'per_person':
        total_price = (
            (number_of_adults * price_sgl) +
            (children * price_chd) +
            (infants * price_inf)
        )
        total_price = total_price * seasonal_factor * price_adjustment
        total_price = total_price * exchange_rate
        total_price = total_price + (total_price * Decimal('0.05'))

        configurations = [{
            'singles': 0,
            'doubles': 0,
            'triples': 0,
            'children': children,
            'infants': infants,
            'child_ages': child_ages,
            'total_price': float(round(total_price, 2)),
            'currency': currency,
            'total_rooms': 0,
            'cheapest': True
        }]
        logger.debug(f"Per-person config for {tour_type}: {configurations[0]}")

    else:
        total_price = (
            (number_of_adults * price_adult) +
            (children * price_chd) +
            (infants * price_inf)
        )
        total_price = total_price * seasonal_factor * price_adjustment
        total_price = total_price * exchange_rate
        total_price = total_price + (total_price * Decimal('0.05'))

        configurations = [{
            'singles': 0,
            'doubles': 0,
            'triples': 0,
            'children': children,
            'infants': infants,
            'child_ages': child_ages,
            'total_price': float(round(total_price, 2)),
            'currency': currency,
            'total_rooms': 0,
            'cheapest': True
        }]
        logger.debug(f"DayTour config: {configurations[0]}")

    logger.info(f"Generated configurations for {tour_type}/{tour_id}: {len(configurations)} items")
    return configurations

def render_pricing(request, tour_type, tour_id):
    logger.debug(f"render_pricing called with POST: {request.POST}")
    # Prioritize currency from POST data
    currency = request.POST.get('currency', request.session.get('currency', 'USD')).upper()
    request.session['currency'] = currency  # Update session currency
    logger.debug(f"Selected currency: {currency}")

    configurations = compute_pricing(tour_type, tour_id, request.POST, request.session)
    model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
    tour = get_object_or_404(model_map.get(tour_type.lower()), pk=tour_id)
    form_errors = []
    if not configurations:
        form_errors.append("No valid pricing options generated.")
        logger.warning("No configurations generated in render_pricing")

    try:
        child_ages = json.loads(request.POST.get('child_ages', '[]'))
        child_ages = [int(age) for age in child_ages if 0 <= int(age) <= tour.child_age_max]
    except (json.JSONDecodeError, ValueError):
        child_ages = []
    number_of_adults = int(request.POST.get('number_of_adults', '1'))
    number_of_children = int(request.POST.get('number_of_children', '0'))
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
        'child_age_max': int(getattr(tour, 'child_age_axn', 12)),
        'children_exceed_room_limit': False,
        'max_children_per_room': getattr(tour, 'max_children_per_room', 1),
        'currency': currency,
        'number_of_adults': number_of_adults,
        'number_of_infants': infants,
        'child_ages': child_ages,
        'number_of_children': number_of_children
    }
    response_content = render_to_string('bookings/partials/pricing_options.html', context, request=request)
    logger.debug(f"Rendered pricing_options.html with context: {context}")
    return HttpResponse(response_content, content_type='text/html')

def get_exchange_rate(currency_code: str) -> Decimal:
    """
    Retrieve the exchange rate for a given currency relative to USD.
    Returns 1.0 for USD explicitly to avoid unnecessary database lookup.
    """
    currency_code = currency_code.upper()
    if currency_code == 'USD':
        logger.debug("Using 1:1 exchange rate for USD")
        return Decimal('1.0')
    try:
        rate = ExchangeRate.objects.get(currency_code=currency_code).rate_to_usd
        logger.info(f"Exchange rate for {currency_code}: {rate}")
        return rate
    except ObjectDoesNotExist:
        logger.warning(f"Exchange rate not found for {currency_code}, attempting to fetch")
        return fetch_exchange_rate(currency_code)

def fetch_exchange_rate(currency_code: str) -> Decimal:
    try:
        response = requests.get(
            f"https://api.openexchangerates.org/latest.json?app_id={settings.OPEN_EXCHANGE_RATES_API_KEY}"
        )
        response.raise_for_status()
        data = response.json()
        rate = Decimal(str(data['rates'][currency_code]))
        ExchangeRate.objects.update_or_create(
            currency_code=currency_code,
            defaults={'rate_to_usd': rate}
        )
        logger.info(f"Fetched exchange rate for {currency_code}: {rate}")
        return rate
    except Exception as e:
        logger.error(f"Failed to fetch rate for {currency_code}: {e}")
        return Decimal('1.0')

def book_tour(request, tour_type: str, tour_id: int) -> HttpResponse:
    model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
    model = model_map.get(tour_type.lower())
    if not model:
        logger.error(f"Invalid tour type: {tour_type}")
        messages.error(request, _("Invalid tour type."))
        return redirect('tours_list')
    try:
        tour = model.objects.get(id=tour_id)
    except model.DoesNotExist:
        logger.error(f"Tour not found: type={tour_type}, id={tour_id}")
        messages.error(request, _("Tour not found."))
        return redirect('tours_list')

    currency = request.session.get('currency', 'USD').upper()
    form_data = request.session.get('proposal_form_data', {})

    # Calculate initial travel_date and end_date
    travel_date_str = form_data.get('travel_date', '2025-05-11')
    try:
        if not travel_date_str:
            raise ValueError("Travel date is empty")
        travel_date = parse_date(travel_date_str).date()
        end_date = travel_date + timedelta(days=tour.duration_days - 1) if tour_type in ['full', 'land'] else travel_date
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(f"Invalid travel_date in form_data: {travel_date_str}, error: {str(e)}")
        travel_date = datetime(2025, 5, 11).date()
        end_date = travel_date + timedelta(days=tour.duration_days - 1) if tour_type in ['full', 'land'] else travel_date

    if request.method == 'POST':
        logger.debug(f"POST data received: {request.POST}")
        post_data = request.POST.copy()
        if 'currency' not in post_data:
            post_data['currency'] = currency
        try:
            form = ProposalForm(post_data, initial={'tour_type': tour_type, 'tour_id': tour_id, 'currency': currency})
            if form.is_valid():
                cleaned_data = form.cleaned_data.copy()
                logger.debug(f"book_tour cleaned_data: {cleaned_data}")
                if cleaned_data.get('currency'):
                    request.session['currency'] = cleaned_data['currency'].upper()
                selected_configuration = str(cleaned_data.get('selected_configuration', '0'))
                configurations = compute_pricing(tour_type, tour_id, cleaned_data, request.session)
                if not configurations:
                    logger.error("No configurations generated, redirecting to booking form")
                    messages.error(request, _("No pricing options available. Please try different options."))
                    return redirect('bookings:book_tour', tour_type=tour_type, tour_id=tour_id)
                try:
                    idx = int(selected_configuration)
                    if idx < 0 or idx >= len(configurations):
                        logger.warning(f"Invalid selected_configuration: {selected_configuration}, resetting to 0")
                        selected_configuration = '0'
                except ValueError:
                    logger.warning(f"Non-integer selected_configuration: {selected_configuration}, resetting to 0")
                    selected_configuration = '0'
                form_data = {
                    'customer_name': cleaned_data.get('customer_name', ''),
                    'customer_email': cleaned_data.get('customer_email', ''),
                    'customer_phone': cleaned_data.get('customer_phone', ''),
                    'customer_address': cleaned_data.get('customer_address', ''),
                    'nationality': cleaned_data.get('nationality', ''),
                    'notes': cleaned_data.get('notes', ''),
                    'number_of_adults': cleaned_data.get('number_of_adults', 1),
                    'number_of_children': cleaned_data.get('number_of_children', 0),
                    'child_ages': cleaned_data.get('child_ages', []),
                    'travel_date': cleaned_data.get('travel_date').isoformat() if cleaned_data.get('travel_date') else travel_date.isoformat(),
                    'end_date': cleaned_data.get('end_date').isoformat() if cleaned_data.get('end_date') else end_date.isoformat(),
                    'currency': cleaned_data.get('currency', 'USD'),
                    'selected_configuration': selected_configuration,
                    'configurations': configurations,
                }
                request.session['proposal_form_data'] = form_data
                request.session.modified = True
                logger.debug(f"Stored form data in session: {form_data}")
                context = {
                    'form_data': form_data,
                    'tour': tour,
                    'tour_type': tour_type,
                    'tour_id': tour_id,
                    'tour_duration': tour.duration_days if tour_type in ['full', 'land'] else tour.duration_hours,
                    'configurations': form_data.get('configurations', []),
                    'selected_configuration_index': form_data.get('selected_configuration', '0'),
                    'booking_data_json': {
                        'tourName': tour.safe_translation_getter('title', 'Untitled'),
                        'tourType': tour_type,
                        'tourId': tour_id,
                        'languagePrefix': request.LANGUAGE_CODE,
                        'childAgeMin': getattr(tour, 'child_age_min', 7),
                        'childAgeMax': int(getattr(tour, 'child_age_max', 12)),
                    },
                    'is_confirmation': True,
                }
                logger.debug(f"Rendering confirm_proposal.html with context: {context}")
                return render(request, 'bookings/partials/confirm_proposal.html', context)
            else:
                logger.error(f"Form validation failed: {form.errors}")
                form_errors = [str(error) for error in form.errors.values()]
                context = {
                    'form': form,
                    'tour': tour,
                    'tour_type_val': tour_type,
                    'tour_id': tour_id,
                    'form_errors': form_errors,
                    'tour_duration': tour.duration_days if tour_type in ['full', 'land'] else tour.duration_hours,
                    'configurations': [],
                    'configurations_json': json.dumps([]),
                    'currency': currency,
                    'travel_date': travel_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'child_age_min': getattr(tour, 'child_age_min', 7),
                    'child_age_max': int(getattr(tour, 'child_age_max', 12)),
                    'max_children_per_room': getattr(tour, 'max_children_per_room', 1),
                    'exchange_rates': ExchangeRate.objects.all(),
                }
                return render(request, 'bookings/partials/booking_form.html', context)
        except Exception as e:
            logger.error(f"Unexpected error in book_tour POST: {str(e)}", exc_info=True)
            messages.error(request, _("An unexpected error occurred. Please try again or contact support."))
            return render(request, 'bookings/partials/booking_form.html', {
                'form': form,
                'tour': tour,
                'tour_type_val': tour_type,
                'tour_id': tour_id,
                'form_errors': ['An unexpected error occurred.'],
                'tour_duration': tour.duration_days if tour_type in ['full', 'land'] else tour.duration_hours,
                'configurations': [],
                'configurations_json': json.dumps([]),
                'currency': currency,
                'travel_date': travel_date.isoformat(),
                'end_date': end_date.isoformat(),
                'child_age_min': getattr(tour, 'child_age_min', 7),
                'child_age_max': int(getattr(tour, 'child_age_max', 12)),
                'max_children_per_room': getattr(tour, 'max_children_per_room', 1),
                'exchange_rates': ExchangeRate.objects.all(),
            })
    else:
        initial_data = {
            'tour_type': tour_type,
            'tour_id': tour_id,
            'number_of_adults': form_data.get('number_of_adults', 1),
            'number_of_children': form_data.get('number_of_children', 0),
            'child_ages': json.dumps(form_data.get('child_ages', [])),
            'travel_date': travel_date.isoformat(),
            'end_date': end_date.isoformat(),
            'currency': form_data.get('currency', currency),
            'customer_name': form_data.get('customer_name'),
            'customer_email': form_data.get('customer_email'),
            'customer_phone': form_data.get('customer_phone'),
            'customer_address': form_data.get('customer_address'),
            'nationality': form_data.get('nationality'),
            'notes': form_data.get('notes'),
            'selected_configuration': form_data.get('selected_configuration', '0'),
        }
        form = ProposalForm(initial=initial_data)

    pricing_data = {
        'tour_type': tour_type,
        'tour_id': tour_id,
        'number_of_adults': form_data.get('number_of_adults', '1'),
        'number_of_children': form_data.get('number_of_children', '0'),
        'travel_date': travel_date.isoformat(),
        'currency': form_data.get('currency', currency),
        'form_submission': 'pricing',
        'child_ages': json.dumps(form_data.get('child_ages', [])),
    }
    configurations = compute_pricing(tour_type, tour_id, pricing_data, request.session)
    configurations_json = json.dumps(configurations, ensure_ascii=False)
    cancellation_policy = getattr(tour, 'cancellation_policy', None)
    cancellation_policy_str = (
        str(cancellation_policy) if cancellation_policy else 'CXL 7 / 50 (7 days, 50.00%)'
    )

    booking_data = {
        'tourName': tour.safe_translation_getter('title', 'Untitled'),
        'tourType': tour_type,
        'tourId': str(tour_id),
        'languagePrefix': request.LANGUAGE_CODE,
        'cancellationPolicy': cancellation_policy_str,
        'childAgeMin': getattr(tour, 'child_age_min', 7),
        'childAgeMax': int(getattr(tour, 'child_age_max', 12)),
    }
    try:
        booking_data_json = json.dumps(booking_data, ensure_ascii=False)
        logger.debug(f"booking_data_json: {booking_data_json}")
    except Exception as e:
        logger.error(f"Failed to serialize booking_data to JSON: {e}")
        booking_data_json = json.dumps({})
        logger.warning("Using empty booking_data_json as fallback")

    context = {
        'form': form,
        'tour': tour,
        'tour_type_val': tour_type,
        'tour_id': tour_id,
        'booking_data_json': booking_data_json,
        'tour_duration': tour.duration_days if tour_type in ['full', 'land'] else tour.duration_hours,
        'configurations': configurations,
        'configurations_json': configurations_json,
        'form_errors': [],
        'child_age_min': getattr(tour, 'child_age_min', 7),
        'child_age_max': int(getattr(tour, 'child_age_max', 12)),
        'max_children_per_room': getattr(tour, 'max_children_per_room', 1),
        'select_age_range': list(range(0, getattr(tour, 'child_age_max', 12) + 1)),
        'exchange_rates': ExchangeRate.objects.all(),
        'currency': currency,
        'travel_date': travel_date.isoformat(),
        'end_date': end_date.isoformat(),
    }
    logger.debug(f"Context booking_data_json: {context['booking_data_json']}")
    logger.debug(f"Rendering booking_form.html with context: {context}")
    logger.debug(f"child_age_max for tour {tour.id}: {getattr(tour, 'child_age_max', 12)}")
    return render(request, 'bookings/partials/booking_form.html', context)

def confirm_proposal_submission(request, tour_type: str, tour_id: int) -> HttpResponse:
    model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
    logger.debug(f"confirm_proposal_submission called: method={request.method}, tour_type={tour_type}, tour_id={tour_id}")

    # Validate tour_type
    if not tour_type or tour_type.lower() not in model_map:
        logger.error(f"Invalid tour_type: {tour_type}")
        messages.error(request, _("Invalid tour type."))
        return redirect('tours_list')

    model = model_map.get(tour_type.lower())
    if not model:
        logger.error(f"Model not found for tour_type: {tour_type}")
        messages.error(request, _("Invalid tour type."))
        return redirect('tours_list')

    # Validate tour
    try:
        tour = model.objects.get(id=tour_id)
    except model.DoesNotExist:
        logger.error(f"Tour not found: type={tour_type}, id={tour_id}")
        messages.error(request, _("Tour not found."))
        return redirect('tours_list')

    # Validate session data
    form_data = request.session.get('proposal_form_data')
    if not form_data:
        logger.error("No proposal form data in session")
        messages.error(request, _("No booking data found. Please start over."))
        return redirect('bookings:book_tour', tour_type=tour_type, tour_id=tour_id)

    logger.debug(f"Form data: {form_data}")
    configurations = form_data.get('configurations', [])

    if not configurations:
        logger.error("No configurations in session, redirecting to book_tour")
        messages.error(request, _("No pricing options available. Please try different options."))
        return redirect('bookings:book_tour', tour_type=tour_type, tour_id=tour_id)

    # Use request.POST for selected_configuration
    selected_configuration_index = request.POST.get('selected_configuration', '0')

    # Validate selected_configuration_index
    if selected_configuration_index is None or selected_configuration_index == '':
        logger.warning(f"selected_configuration_index is None or empty, defaulting to '0'")
        selected_configuration_index = '0'
    try:
        idx = int(selected_configuration_index)
        if idx < 0 or idx >= len(configurations):
            logger.warning(f"Invalid configuration index: {selected_configuration_index}, resetting to 0")
            selected_configuration_index = '0'
    except ValueError:
        logger.warning(f"Non-integer configuration index: {selected_configuration_index}, resetting to 0")
        selected_configuration_index = '0'

    logger.debug(f"POST selected_configuration: {request.POST.get('selected_configuration')}, "
                 f"Session selected_configuration: {form_data.get('selected_configuration')}, "
                 f"Final selected_configuration_index: {selected_configuration_index}, "
                 f"Configurations length: {len(configurations)}")

    logger.debug(f"Initial session proposal_form_data: {request.session.get('proposal_form_data')}")

    # Update form_data with selected_configuration
    form_data['selected_configuration'] = selected_configuration_index
    request.session['proposal_form_data'] = form_data
    request.session.modified = True  # Ensure session is saved

    if request.method == 'POST':
        logger.debug(f"POST data received: {request.POST}")
        if 'confirm' in request.POST:
            try:
                selected_config = configurations[int(selected_configuration_index)]
                logger.debug(f"Selected config: {selected_config}")
                content_type = ContentType.objects.get_for_model(model)
                estimated_price = round(Decimal(str(selected_config['total_price'])), 2)
                child_ages = form_data.get('child_ages', [])
                if isinstance(child_ages, str):
                    try:
                        child_ages = json.loads(child_ages)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse child_ages: {child_ages}, using empty list")
                        child_ages = []
                proposal = Proposal(
                    content_type=content_type,
                    object_id=tour_id,
                    travel_date=datetime.fromisoformat(form_data['travel_date']).date() if form_data.get('travel_date') else None,
                    number_of_adults=int(form_data.get('number_of_adults', 1)),
                    number_of_children=int(form_data.get('number_of_children', 0)),
                    children_ages=child_ages,
                    room_config={
                        'singles': selected_config.get('singles', 0),
                        'doubles': selected_config.get('doubles', 0),
                        'triples': selected_config.get('triples', 0),
                        'children': selected_config.get('children', 0),
                        'infants': selected_config.get('infants', 0),
                        'total': float(estimated_price),
                    },
                    estimated_price=estimated_price,
                    currency=form_data.get('currency', 'USD'),
                    customer_name=form_data.get('customer_name', ''),
                    customer_email=form_data.get('customer_email', ''),
                    customer_phone=form_data.get('customer_phone', ''),
                    customer_address=form_data.get('customer_address', ''),
                    nationality=form_data.get('nationality', ''),
                    notes=form_data.get('notes', ''),
                    status='PENDING_SUPPLIER',
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                    supplier_email=tour.supplier_email if hasattr(tour, 'supplier_email') else None,
                    user=get_default_user(request)
                )
                proposal.save()
                # Store selected_configuration_index in session
                request.session['selected_configuration_index'] = selected_configuration_index
                logger.info(f"Proposal saved: ID={proposal.id}, tour={tour.title}, estimated_price={estimated_price}")

                # Create confirmation token and send supplier email
                token = ProposalConfirmationToken.objects.create(proposal=proposal)
                if not send_supplier_email(proposal, token):
                    logger.warning(f"Supplier email not sent Stuart email sent for proposal {proposal.id}, but continuing")
                    messages.warning(request, _("Proposal submitted, but supplier notification failed. We will contact the supplier manually."))

                request.session.pop('proposal_form_data', None)
                messages.success(request, _("Proposal submitted successfully. Awaiting supplier confirmation."))
                return render(request, 'bookings/partials/proposal_success.html', {
                    'proposal': proposal,
                    'tour': tour,
                    'tour_type': tour_type,
                })
            except ContentType.DoesNotExist as e:
                logger.error(f"ContentType error: {e}")
                messages.error(request, _("Invalid tour configuration. Please try again."))
                return redirect('bookings:book_tour', tour_type=tour_type, tour_id=tour_id)
            except ValueError as e:
                logger.error(f"Value error in proposal creation: {e}")
                messages.error(request, _("Invalid data format. Please try again."))
                return redirect('bookings:book_tour', tour_type=tour_type, tour_id=tour_id)
            except Exception as e:
                logger.error(f"Unexpected error saving proposal: {e}", exc_info=True)
                messages.error(request, _("Failed to submit proposal. Please try again."))
                return redirect('bookings:book_tour', tour_type=tour_type, tour_id=tour_id)

        elif 'go_back' in request.POST:
            logger.debug("Go Back to Edit clicked, rendering booking_form via HTMX")
            return revert_to_booking_form(request, tour_type, tour_id)
        else:
            logger.warning("Unknown POST action")
            messages.error(request, _("Invalid action. Please try again."))
            return redirect('bookings:book_tour', tour_type=tour_type, tour_id=tour_id)
    else:
        # Handle GET request
        if not tour_type:
            logger.error("Empty tour_type in GET request")
            messages.error(request, _("Invalid tour type. Please start over."))
            return redirect('tours_list')
        context = {
            'form_data': form_data,
            'tour': tour,
            'tour_type': tour_type,
            'tour_id': tour_id,
            'tour_duration': getattr(tour, 'duration_days', getattr(tour, 'duration_hours', None)),
            'configurations': configurations,
            'selected_configuration': selected_configuration_index,
            'booking_data_json': {
                'tourName': tour.safe_translation_getter('title', 'Untitled'),
                'tourType': tour_type,
                'tourId': tour_id,
                'languagePrefix': request.LANGUAGE_CODE,
            },
            'is_confirmation': True,
        }
        logger.debug(f"Rendering confirm_proposal.html with context: {context}")
        storage = get_messages(request)
        storage.used = True
        return render(request, 'bookings/partials/confirm_proposal.html', context)

def child_ages(request) -> HttpResponse:
    number_of_children = int(request.GET.get('number_of_children', 0))
    tour_type = request.GET.get('tour_type', 'land')
    tour_id = request.GET.get('tour_id', '1')
    child_ages_str = request.GET.get('child_ages', '[]')
    try:
        child_ages = json.loads(urllib.parse.unquote(child_ages_str))
        if not isinstance(child_ages, list):
            child_ages = []
    except json.JSONDecodeError:
        child_ages = []

    model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
    model = model_map.get(tour_type.lower())
    if not model:
        logger.error(f"Invalid tour type: {tour_type}")
        return render(request, 'bookings/partials/child_ages.html', {
            'number_of_children': number_of_children,
            'child_age_min': 0,
            'child_age_max': 12,
            'max_children_per_room': 1,
            'child_ages': child_ages,
            'select_age_range': list(range(0, 13)),
            'tour_type': tour_type,
            'tour_id': tour_id
        })

    try:
        tour = model.objects.get(pk=tour_id)
        child_age_min = tour.child_age_min  # e.g., 7
        child_age_max = tour.child_age_max  # e.g., 12
        max_children_per_room = getattr(tour, 'max_children_per_room', 1)
        select_age_range = list(range(0, child_age_max + 1))  # e.g., [0, ..., 12]
        logger.debug(f"Tour {tour_type} {tour_id}: child_age_min={child_age_min}, child_age_max={child_age_max}, select_age_range={select_age_range}")
    except model.DoesNotExist:
        logger.warning(f"Tour not found: type={tour_type}, id={tour_id}")
        child_age_min = 0
        child_age_max = 12
        max_children_per_room = 1
        select_age_range = list(range(0, 13))

    # Preserve client-provided ages without clamping
    child_ages = [int(age) for age in child_ages if isinstance(age, (int, float)) and 0 <= int(age) <= child_age_max][:number_of_children]
    # Pad with 0 if needed
    if len(child_ages) < number_of_children:
        child_ages = child_ages + [0] * (number_of_children - len(child_ages))

    context = {
        'number_of_children': number_of_children,
        'child_age_min': child_age_min,
        'child_age_max': child_age_max,
        'max_children_per_room': max_children_per_room,
        'child_ages': child_ages,
        'select_age_range': select_age_range,
        'tour_type': tour_type,
        'tour_id': tour_id
    }
    logger.debug(f"Rendering child_ages.html with context: {context}")
    return render(request, 'bookings/partials/child_ages.html', context)

def revert_to_booking_form(request, tour_type: str, tour_id: int) -> HttpResponse:
    logger.debug(f"revert_to_booking_form called: tour_type={tour_type}, tour_id={tour_id}")

    # Map tour type to model
    model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
    model = model_map.get(tour_type.lower())
    if not model:
        logger.error(f"Invalid tour type: {tour_type}")
        return HttpResponse(status=400)

    tour = get_object_or_404(model, pk=tour_id)
    form_data = request.session.get('proposal_form_data', {})
    logger.debug(f"Restored form_data from session: {form_data}")

    # Ensure child_ages is a list and matches number_of_children
    child_ages = form_data.get('child_ages', [])
    if isinstance(child_ages, str):
        try:
            child_ages = json.loads(child_ages)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse child_ages: {child_ages}, using empty list")
            child_ages = []
    if not isinstance(child_ages, list):
        child_ages = []

    number_of_children = int(form_data.get('number_of_children', 0))
    child_age_min = getattr(tour, 'child_age_min', 7)
    child_age_max = getattr(tour, 'child_age_max', 12)

    # Validate and clamp child_ages
    child_ages = [
        max(child_age_min, min(child_age_max, int(age))) if isinstance(age, (int, float)) else child_age_min
        for age in child_ages[:number_of_children]
    ]
    # Pad with child_age_min if needed
    if len(child_ages) < number_of_children:
        child_ages = child_ages + [child_age_min] * (number_of_children - len(child_ages))

    # Get selected_configuration from session
    selected_configuration = form_data.get('selected_configuration', '0')
    try:
        idx = int(selected_configuration)
        if idx < 0:
            logger.warning(f"Negative selected_configuration: {selected_configuration}, resetting to 0")
            selected_configuration = '0'
    except ValueError:
        logger.warning(f"Non-integer selected_configuration: {selected_configuration}, resetting to 0")
        selected_configuration = '0'

    # Prepare form initial data
    initial_data = {
        'customer_name': form_data.get('customer_name', ''),
        'customer_email': form_data.get('customer_email', ''),
        'customer_phone': form_data.get('customer_phone', ''),
        'customer_address': form_data.get('customer_address', ''),
        'nationality': form_data.get('nationality', ''),
        'notes': form_data.get('notes', ''),
        'number_of_adults': form_data.get('number_of_adults', 1),
        'number_of_children': number_of_children,
        'child_ages': child_ages,  # Ensure child_ages is a list
        'tour_type': tour_type,
        'tour_id': tour_id,
        'travel_date': form_data.get('travel_date', ''),
        'end_date': form_data.get('end_date', ''),
        'currency': form_data.get('currency', 'USD'),
        'selected_configuration': selected_configuration,
    }

    form = ProposalForm(initial=initial_data)

    # Recompute configurations
    try:
        configurations = compute_pricing(tour_type, tour_id, initial_data, request.session)
        logger.debug(f"Recomputed configurations: {configurations}")
        # Validate selected_configuration against configurations
        if int(selected_configuration) >= len(configurations):
            logger.warning(f"Selected configuration index {selected_configuration} exceeds configurations length {len(configurations)}, resetting to 0")
            selected_configuration = '0'
            initial_data['selected_configuration'] = '0'
            form_data['selected_configuration'] = '0'
            request.session['proposal_form_data'] = form_data
            request.session.modified = True
    except Exception as e:
        logger.error(f"Error recomputing pricing: {e}", exc_info=True)
        configurations = []

    context = {
        'form': form,
        'tour': tour,
        'tour_type_val': tour_type,
        'tour_id': tour_id,
        'tour_duration': tour.duration_days if tour_type in ['full', 'land'] else tour.duration_hours,
        'configurations': configurations,
        'configurations_json': json.dumps(configurations, ensure_ascii=False),
        'form_errors': [] if configurations else [_("No pricing options available. Please adjust your inputs.")],
        'child_ages': child_ages,
        'child_age_min': child_age_min,
        'child_age_max': child_age_max,
        'max_children_per_room': getattr(tour, 'max_children_per_room', 1),
        'select_age_range': list(range(0, child_age_max + 1)),
        'number_of_children': number_of_children,
        'form_data': initial_data,
        'exchange_rates': ExchangeRate.objects.all(),
        'currency': form_data.get('currency', 'USD'),
        'selected_configuration_index': selected_configuration,
    }

    logger.debug(f"Rendering booking_form.html with context: {context}")
    return render(request, 'bookings/partials/booking_form.html', context)
def manage_proposals(request) -> HttpResponse:
    proposals = Proposal.objects.prefetch_related('translations', 'tour').all()
    paginator = Paginator(proposals, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    if request.htmx:
        status = request.GET.get('status')
        if status:
            proposals = proposals.filter(status=status)
            paginator = Paginator(proposals, 10)
            page_obj = paginator.get_page(request.GET.get('page', 1))
        return render(request, 'bookings/partials/proposal_list.html', {'proposals': page_obj})
    return render(request, 'bookings/manage_proposals.html', {'proposals': page_obj})

def confirm_proposal(request, proposal_id: int) -> HttpResponse:
    try:
        proposal = Proposal.objects.get(id=proposal_id)
        if proposal.status != 'PENDING_SUPPLIER':
            messages.error(request, "Proposal is not pending supplier confirmation.")
            return redirect('bookings:manage_proposals')
        proposal.payment_link = f"{settings.SITE_URL}/bookings/payment/success/{proposal.id}/"
        proposal.status = 'SUPPLIER_CONFIRMED'
        proposal.save()
        send_preconfirmation_email(proposal)
        messages.success(request, "Proposal confirmed. Payment link sent to customer.")
    except Proposal.DoesNotExist:
        messages.error(request, "Proposal not found.")
    return redirect('bookings:manage_proposals')

def confirm_proposal_by_token(request, token: str) -> HttpResponse:
    try:
        token_obj = ProposalConfirmationToken.objects.get(token=token)
        if not token_obj.is_valid():
            messages.error(request, "Invalid or expired confirmation link.")
            return render(request, 'bookings/confirmation_error.html')
        proposal = token_obj.proposal
        proposal.payment_link = f"{settings.SITE_URL}/bookings/payment/success/{proposal.id}/"
        proposal.status = 'SUPPLIER_CONFIRMED'
        proposal.save()
        token_obj.used_at = timezone.now()
        token_obj.save()
        send_preconfirmation_email(proposal)
        return render(request, 'bookings/confirmation_success.html', {
            'proposal': proposal,
            'site_url': settings.SITE_URL,
        })
    except ProposalConfirmationToken.DoesNotExist:
        messages.error(request, "Invalid confirmation link.")
        return render(request, 'bookings/confirmation_error.html')

def send_supplier_email(proposal: Proposal, token: ProposalConfirmationToken = None) -> bool:
    try:
        if not proposal.supplier_email:
            logger.error(f"Supplier email missing for proposal {proposal.id}")
            raise ValueError("Supplier email is required.")
        subject = f"New Tour Proposal - {proposal.tour}"

        context = {
            'proposal': proposal,
            'end_date': proposal.travel_date + timedelta(days=proposal.tour.duration_days),
            'tour': proposal.tour,
            'site_url': settings.SITE_URL,
            'configuration_details': proposal.room_config if proposal.room_config else [],
        }
        if token:
            context['confirm_url'] = f"{settings.SITE_URL}{reverse('bookings:confirm_proposal_by_token', args=[token.token])}"
        message = render_to_string('bookings/emails/supplier_proposal.html', context)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [proposal.supplier_email],
            html_message=message,
            fail_silently=False,
        )
        logger.info(f"Supplier email sent to {proposal.supplier_email} for proposal {proposal.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send supplier email for proposal {proposal.id}: {e}")
        return False

def reject_proposal(request, proposal_id: int) -> HttpResponse:
    try:
        proposal = Proposal.objects.get(id=proposal_id)
        proposal.status = 'REJECTED'
        proposal.save()
        messages.success(request, "Proposal rejected.")
    except Proposal.DoesNotExist:
        messages.error(request, "Proposal not found.")
    return redirect('bookings:manage_proposals')

def send_preconfirmation_email(proposal: Proposal) -> None:
    subject = "Confirm Your Tour Proposal"
    duration = proposal.tour.duration_days
    end_date = proposal.travel_date + timedelta(days=duration)
    message = render_to_string('bookings/emails/preconfirmation.html', {
        'proposal': proposal,
        'tour': proposal.tour,
        'end_date': end_date,
        'payment_link': proposal.payment_link,
        'site_url': settings.SITE_URL,
        'configuration_details': proposal.room_config if proposal.room_config else [],
    })
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [proposal.customer_email],
        html_message=message,
    )
    logger.info(f"Preconfirmation email sent to {proposal.customer_email} for proposal {proposal.id}")

def payment_success(request, proposal_id: int) -> HttpResponse:
    try:
        proposal = Proposal.objects.get(id=proposal_id)
        if proposal.status != 'SUPPLIER_CONFIRMED':
            logger.error(f"Invalid proposal status for payment: {proposal.status}, id={proposal_id}")
            messages.error(request, "Invalid proposal status.")
            return redirect('home')

        # Check if a Booking already exists for this proposal
        existing_booking = Booking.objects.filter(proposal=proposal).first()
        if existing_booking:
            logger.info(f"Booking already exists for proposal {proposal_id}: booking_id={existing_booking.id}")
            messages.info(request, "Booking already confirmed. Itinerary has been sent.")
            try:
                itinerary_pdf = generate_itinerary_pdf(existing_booking)
                send_itinerary_email(existing_booking, itinerary_pdf)
            except Exception as e:
                logger.error(f"Failed to resend itinerary for booking {existing_booking.id}: {e}")
                messages.warning(request, "Booking confirmed, but itinerary resending failed. Contact support.")
            return redirect('home')

        # Create new Booking
        booking = Booking.objects.create(
            customer_name=proposal.customer_name,
            customer_email=proposal.customer_email,
            customer_phone=proposal.customer_phone,
            customer_address=proposal.customer_address,
            nationality=proposal.nationality,
            notes=proposal.notes,
            content_type=proposal.content_type,
            object_id=proposal.object_id,
            number_of_adults=proposal.number_of_adults,
            number_of_children=proposal.number_of_children,
            travel_date=proposal.travel_date,
            total_price=proposal.estimated_price,
            payment_status='PAID',
            status='CONFIRMED',
            payment_method='CREDIT_CARD',
            proposal=proposal,
            currency=proposal.currency,
            user=proposal.user,
        )
        proposal.status = 'PAID'
        proposal.save()
        try:
            itinerary_pdf = generate_itinerary_pdf(booking)
            send_itinerary_email(booking, itinerary_pdf)
            messages.success(request, "Payment successful! Your itinerary has been sent.")
        except Exception as e:
            logger.error(f"Failed to generate/send itinerary for booking {booking.id}: {e}")
            messages.warning(request, "Payment successful, but itinerary generation failed. Contact support.")
    except Proposal.DoesNotExist:
        logger.error(f"Proposal not found: id={proposal_id}")
        messages.error(request, "Proposal not found.")
    return redirect('home')

def payment_cancel(request, proposal_id: int) -> HttpResponse:
    try:
        proposal = Proposal.objects.get(id=proposal_id)
        proposal.status = 'REJECTED'
        proposal.save()
        logger.info(f"Payment cancelled for proposal {proposal_id}")
        messages.error(request, "Payment cancelled. Please contact us to retry.")
    except Proposal.DoesNotExist:
        logger.error(f"Proposal not found: id={proposal_id}")
        messages.error(request, "Proposal not found.")
    return redirect('home')

def generate_itinerary_pdf(booking: Booking) -> bytes:
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=15*mm,
            bottomMargin=15*mm,
            leftMargin=15*mm,
            rightMargin=15*mm
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name='Title',
            parent=styles['Title'],
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor('#1a3c6e'),
            spaceAfter=8,
            alignment=1
        )
        title_shadow_style = ParagraphStyle(
            name='TitleShadow',
            parent=title_style,
            textColor=colors.HexColor('#cccccc'),
            spaceAfter=0
        )
        subtitle_style = ParagraphStyle(
            name='Subtitle',
            parent=styles['Title'],
            fontName='Helvetica',
            fontSize=16,
            textColor=colors.HexColor('#1a3c6e'),
            spaceAfter=12,
            alignment=1
        )
        heading_style = ParagraphStyle(
            name='Heading2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceBefore=12,
            spaceAfter=8
        )
        normal_style = ParagraphStyle(
            name='Normal',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#333333')
        )
        bullet_style = ParagraphStyle(
            name='Bullet',
            parent=normal_style,
            leftIndent=10,
            bulletIndent=0,
            spaceAfter=4,
            fontSize=10,
            bulletFontName='Helvetica',
            bulletText='●'
        )
        footer_style = ParagraphStyle(
            name='Footer',
            parent=normal_style,
            fontName='Helvetica-Bold',
            fontSize=10,
            alignment=1
        )

        elements = []

        def add_watermark(canvas, doc):
            if canvas.getPageNumber() == 1:
                watermark_path = 'static/images/watermark.jpg'
                logger.info(f"Attempting to load watermark: {watermark_path}")
                if not os.path.exists(watermark_path):
                    logger.warning(f"Watermark file does not exist: {watermark_path}")
                try:
                    canvas.saveState()
                    canvas.setFillAlpha(0.15)
                    watermark = Image(watermark_path, width=doc.width+30*mm, height=doc.height+40*mm)
                    watermark.drawOn(canvas, doc.leftMargin-15*mm, doc.bottomMargin-20*mm)
                    canvas.restoreState()
                except Exception as e:
                    logger.warning(f"Could not load watermark: {e}")
            else:
                logo_path = 'static/images/logo.png'
                logger.info(f"Attempting to load logo watermark: {logo_path}")
                if not os.path.exists(logo_path):
                    logger.warning(f"Logo watermark file does not exist: {logo_path}")
                try:
                    canvas.saveState()
                    canvas.setFillAlpha(0.45)
                    logo = Image(logo_path, width=80*mm, height=40*mm)
                    logo.drawOn(canvas, (doc.width-80*mm)/2, (doc.height-40*mm)/2)
                    canvas.restoreState()
                except Exception as e:
                    logger.warning(f"Could not load logo watermark: {e}")

        doc.addPageTemplates([
            PageTemplate(id='First', frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)], onPage=add_watermark),
            PageTemplate(id='Later', frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)], onPage=add_watermark),
        ])

        header_bg_path = 'static/images/header_bg.jpg'
        logo_path = 'static/images/logo.png'
        header_row = []
        logo_row = []

        logger.info(f"Attempting to load header background: {header_bg_path}")
        if not os.path.exists(header_bg_path):
            logger.warning(f"Header background file does not exist: {header_bg_path}")
        try:
            header_bg = Image(header_bg_path, width=doc.width+30*mm, height=45*mm)
            header_row.append(header_bg)
        except Exception as e:
            logger.warning(f"Could not load header background: {e}")
            header_row.append(Paragraph(_("Header Image Missing"), normal_style))

        logger.info(f"Attempting to load logo: {logo_path}")
        if not os.path.exists(logo_path):
            logger.warning(f"Logo file does not exist: {logo_path}")
        try:
            logo = Image(logo_path, width=50*mm, height=25*mm)
            logo_row.append(logo)
            logger.info("Successfully loaded logo for header")
        except Exception as e:
            logger.warning(f"Failed to load logo: {e}")
            logo_row.append(Paragraph(_("Logo Missing"), normal_style))

        header_table = Table([header_row, logo_row], colWidths=[doc.width], rowHeights=[45*mm, 25*mm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, 1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, 1), -30*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), -15*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), -15*mm),
            ('LEFTPADDING', (0, 1), (0, 1), 15*mm),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3c6e'))
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))

        tour = getattr(booking, 'tour', None)
        tour_name = tour.safe_translation_getter('title', _('Unknown Tour')).upper() if tour else _('Unknown Tour').upper()
        duration = _('CUSTOM')
        if tour:
            if isinstance(tour, (FullTour, LandTour)):
                duration_days = getattr(tour, 'duration_days', 0)
                duration = f"{duration_days} DAYS {duration_days-1} NIGHTS" if duration_days else _("CUSTOM")
            elif isinstance(tour, DayTour):
                duration_hours = getattr(tour, 'duration_hours', 8)
                duration = f"{duration_hours} HOURS"
        elements.append(Paragraph(f"{tour_name} FULL PACK", title_shadow_style))
        elements.append(Paragraph(f"{tour_name} FULL PACK", title_style))
        elements.append(Paragraph(duration, subtitle_style))
        elements.append(Spacer(1, 10*mm))

        inclusions = []
        if tour and isinstance(tour, FullTour):
            inclusions = [
                _("Boleto aéreo GYE - CTG - GYE via Avianca con artículo personal"),
                _("Traslados aeropuerto - hotel - aeropuerto"),
                _(f"{getattr(tour, 'duration_days', 3)-1 or 3} noches de alojamiento en hotel a elegir"),
                _("Desayunos diarios"),
                _("City tour en chiva típica + visita al castillo de San Felipe"),
                _("Full Day Isla Barú (Playa Blanca) + almuerzo típico incluido"),
                _("Tasas e Impuestos de Ecuador y Colombia"),
            ]
        elif tour and isinstance(tour, LandTour):
            inclusions = [
                _("Alojamiento en hotel seleccionado"),
                _("Desayunos diarios"),
                tour.safe_translation_getter('courtesies', _("Tour guiado")),
            ]
        elif tour and isinstance(tour, DayTour):
            inclusions = [
                tour.safe_translation_getter('courtesies', _("Botella de agua")),
                _("Guía profesional"),
            ]
        else:
            inclusions = [_("Servicios según disponibilidad")]

        elements.append(KeepTogether([
            Paragraph(_("INCLUDE"), heading_style),
            *[Paragraph(f"• {item}", bullet_style) for item in inclusions]
        ]))
        elements.append(Spacer(1, 10*mm))

        if tour and isinstance(tour, FullTour):
            elements.append(KeepTogether([
                Paragraph(_("ITINERARIO COTIZADO"), heading_style),
                Table(
                    [
                        [_("Flight"), _("Date"), _("Route"), _("Departure"), _("Arrival")],
                        ["AV8374", "03 Apr", "GYE-BOG", "04:15", "06:10"],
                        ["AV9530", "03 Apr", "BOG-CTG", "08:07", "09:39"],
                        ["AV9807", "06 Apr", "CTG-BOG", "08:13", "09:45"],
                        ["AV8389", "06 Apr", "BOG-GYE", "11:50", "13:40"],
                    ],
                    colWidths=[30*mm, 30*mm, 40*mm, 30*mm, 30*mm],
                    style=TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3c6e')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 8),
                        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
                        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f5f5f5')),
                        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f5f5f5')),
                    ])
                )
            ]))
            elements.append(Spacer(1, 10*mm))

        total_price = getattr(booking, 'total_price', 0.00) or 0.00
        currency = getattr(tour, 'currency', 'EUR') if tour else 'EUR'
        configuration_details = getattr(booking, 'configuration_details', {}) or {}

        if configuration_details:
            room_data = []
            singles = configuration_details.get('singles', 0)
            doubles = configuration_details.get('doubles', 0)
            triples = configuration_details.get('triples', 0)
            children = configuration_details.get('children', 0)
            infants = configuration_details.get('infants', 0)
            if singles:
                room_data.append([f"Single Room ({singles} adult{'s' if singles > 1 else ''})", f"{currency} {total_price/singles:.2f}"])
            if doubles:
                room_data.append([f"Double Room ({doubles*2} adults)", f"{currency} {total_price/(doubles*2):.2f}"])
            if triples:
                room_data.append([f"Triple Room ({triples*3} adults)", f"{currency} {total_price/(triples*3):.2f}"])
            if children:
                room_data.append([f"Children ({children})", f"{currency} {total_price/children:.2f}"])
            if infants:
                room_data.append([f"Infants ({infants})", f"{currency} 0.00"])
            if room_data:
                elements.append(KeepTogether([
                    Paragraph(_("ROOM CONFIGURATION"), heading_style),
                    Table(
                        room_data,
                        colWidths=[100*mm, 60*mm],
                        style=TableStyle([
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                            ('TOPPADDING', (0, 0), (-1, -1), 8),
                            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
                            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                        ])
                    )
                ]))
                elements.append(Spacer(1, 10*mm))

        elements.append(KeepTogether([
            Paragraph(_("TOTAL PRICE"), heading_style),
            Table(
                [[_("Total"), f"{currency} {total_price:.2f}"]],
                colWidths=[100*mm, 60*mm],
                style=TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                ])
            )
        ]))
        elements.append(Spacer(1, 10*mm))

        not_included = [
            _("Comidas y bebidas no indicadas en el programa"),
            _("Extras personales en hoteles y restaurantes"),
            _("Propinas"),
            _("Tarjeta de asistencia médica"),
        ]
        if tour and isinstance(tour, DayTour):
            not_included = [
                _("Transporte al punto de inicio"),
                _("Comidas no especificadas"),
                _("Propinas"),
            ]

        elements.append(KeepTogether([
            Paragraph(_("NO INCLUDE"), heading_style),
            *[Paragraph(f"• {item}", bullet_style) for item in not_included]
        ]))
        elements.append(Spacer(1, 10*mm))

        notes = [
            _("PERÍODO DE COMPRA: COMPRA INMEDIATA"),
            _("Check in a partir de las 15:00 y check out a las 12:00"),
            _("Habitaciones triples cuentan únicamente con 2 camas"),
            _("La asignación de habitaciones se hará con base en disponibilidad"),
            _("PRECIOS SUJETOS A CAMBIO Y DISPONIBILIDAD SIN PREVIO AVISO HASTA CONFIRMAR RESERVA"),
        ]
        if tour and isinstance(tour, DayTour):
            notes = [
                _("Confirmación sujeta a disponibilidad"),
                _("Mínimo de participantes requerido"),
                _("PRECIOS SUJETOS A CAMBIO SIN PREVIO AVISO"),
            ]

        elements.append(KeepTogether([
            Paragraph(_("NOTAS IMPORTANTES"), heading_style),
            *[Paragraph(f"• {note}", bullet_style) for note in notes]
        ]))
        elements.append(Spacer(1, 15*mm))

        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#1a3c6e')))
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(_("Thank you for choosing Milano Travel!"), footer_style))
        elements.append(Paragraph(_("Contact us at support@milano-travel.com"), normal_style))

        logger.info(f"Building PDF with {len(elements)} elements for booking {booking.id}")
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        logger.info(f"Successfully generated PDF for booking {booking.id}")
        return pdf
    except Exception as e:
        logger.error(f"PDF generation failed for booking {booking.id}: {e}")
        raise

def send_itinerary_email(booking: Booking, pdf_data: bytes) -> None:
    subject = "Your Tour Itinerary"
    duration = booking.tour.duration_days
    end_date = booking.travel_date + timedelta(days=duration)

    message = render_to_string('bookings/emails/itinerary_email.html', {
        'booking': booking,
        'tour': booking.tour,
        'end_date': end_date,
        'site_url': settings.SITE_URL,
        'configuration_details': booking.configuration_details or {},
    })
    from django.core.mail import EmailMessage
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.customer_email],
    )
    email.attach('itinerary.pdf', pdf_data, 'application/pdf')
    email.content_subtype = 'html'
    email.send()
    logger.info(f"Itinerary email sent to {booking.customer_email} for booking {booking.id}")

def get_bookings(request) -> JsonResponse:
    bookings = [{'id': b.pk, 'name': f"{b.customer_name} ({b.pk})"} for b in Booking.objects.all()]
    return JsonResponse({'bookings': bookings})

def get_partners(request) -> JsonResponse:
    partners = [{'id': p.pk, 'name': p.name} for p in Partner.objects.all()]
    return JsonResponse({'partners': partners})

def manage_bookings(request) -> HttpResponse:
    bookings = Booking.objects.prefetch_related('translations', 'tour').all()
    paginator = Paginator(bookings, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    if request.htmx:
        status = request.GET.get('status')
        if status:
            bookings = bookings.filter(status=status)
            paginator = Paginator(bookings, 10)
            page_obj = paginator.get_page(request.GET.get('page', 1))
        return render(request, 'bookings/partials/booking_list.html', {'bookings': page_obj})
    return render(request, 'bookings/manage_bookings.html', {'bookings': page_obj})

def get_default_user(request):
    from django.contrib.auth.models import User

    default_username = "MTWEB"
    if request.user.is_authenticated:
        return request.user  # Return the authenticated User object
    try:
        return User.objects.get(username=default_username)
    except User.DoesNotExist:
        # Create the default user if it doesn't exist
        return User.objects.create_user(
            username=default_username,
            email="mtweb@yourdomain.com",  # Replace with a valid email
            password="securepassworde7c"  # Use a secure password
        )

def customer_portal(request) -> HttpResponse:
    email = request.GET.get('email', '')
    prop_id = request.GET.get('prop_id', '')
    proposals = []
    bookings = []
    if email:
        proposals = Proposal.objects.filter(customer_email=email).prefetch_related('tour')
        bookings = Booking.objects.filter(customer_email=email).prefetch_related('tour')
    if prop_id:
        proposals = Proposal.objects.filter(prop_id=prop_id).prefetch_related('tour')
        bookings = Booking.objects.filter(customer_email=email).prefetch_related('tour')
    context = {
        'proposals': proposals,
        'bookings': bookings,
        'email': email,
        'prop_id': prop_id,
    }
    return render(request, 'bookings/customer_portal.html', context)

def proposal_status(request, proposal_id: int) -> JsonResponse:
    try:
        proposal = Proposal.objects.get(id=proposal_id)
        return JsonResponse({
            'status': proposal.get_status_display(),
            'payment_link': proposal.payment_link if proposal.status == 'SUPPLIER_CONFIRMED' else ''
        })
    except Proposal.DoesNotExist:
        return JsonResponse({'error': 'Proposal not found'}, status=404)

