import json
import urllib
import logging
import paypalrestsdk as paypal

from decouple import config
from datetime import date, datetime, timedelta
from bookings.pdf_gen import generate_itinerary_pdf
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP  # Add InvalidOperation if not imported

from .forms import ProposalForm
from partners.models import Partner
from tours.models import LandTourPage
from bookings.forms import ProposalForm
from bookings.models import (
    ExchangeRate,
    Proposal,
    Booking,
    ProposalConfirmationToken
    )

from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView
from django.http import Http404, JsonResponse, HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, render, redirect

from bookings.utils import (
    calculate_demand_factor,
    get_30_day_used_slots,
    get_exchange_rate,
    get_remaining_capacity,
    send_internal_confirmation_email,
    send_itinerary_email,
    send_preconfirmation_email,
    send_proposal_submitted_email,
    send_supplier_email
)


logger = logging.getLogger(__name__)

class BookingStartView(FormView):
    template_name = 'bookings/booking_start.html'
    form_class = ProposalForm
    success_url = reverse_lazy('bookings:customer_portal')  # Fallback, not used

    # @method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True)) Uncomment for more strict security for anom users
    @method_decorator(ratelimit(key='user', rate='10/d', method='POST', block=True)) # Uncomment for per user
    # @method_decorator(ratelimit(key='user:ip', rate='8/h', method='POST', block=True))
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        tour_id = self.kwargs['tour_id']
        self.tour = get_object_or_404(LandTourPage, id=tour_id)
        kwargs['tour'] = self.tour
        kwargs['initial'] = {
            'tour_type': 'land',
            'tour_id': tour_id,
            'form_submission': 'pricing',
            'currency': 'USD',
            'travel_date': date.today(),  # FIXED: Hard today (overrides tour.start_date)
        }
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tour'] = self.tour
        context['tour_type'] = 'land'
        context['tour_duration'] = self.tour.duration_days if self.tour else 0
        context['booking_data'] = {'tourName': self.tour.name}
        context['blackout_dates_json'] = json.dumps(self.tour.blackout_dates_list)  # Flattened list
        # Safe form access for initial_children
        form = kwargs.get('form', self.get_form())
        is_bound = form.is_bound
        context['initial_children'] = form.cleaned_data.get('number_of_children', 0) if is_bound else 0
        initial_child_ages = form.cleaned_data.get('child_ages', []) if is_bound else []
        context['initial_child_ages'] = initial_child_ages
        context['initial_child_ages_json'] = json.dumps(initial_child_ages)

        min_age = getattr(self.tour, 'child_age_min', 0)
        max_age = getattr(self.tour, 'child_age_max', 12)
        context['select_age_range'] = list(range(min_age, max_age + 1))

        if self.tour:
            context['tour_start_date'] = self.tour.start_date.isoformat() if self.tour.start_date else date.today().isoformat()
            context['tour_end_date'] = self.tour.end_date.isoformat() if self.tour.end_date else (date.today() + timedelta(days=365)).isoformat()
            context['available_days'] = self.tour.available_days  # e.g., '0,1,2,3'

        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            cleaned_data = form.cleaned_data
            # Force currency default if missing (e.g., field not rendered)
            if 'currency' not in cleaned_data or not cleaned_data['currency']:
                cleaned_data['currency'] = 'USD'

            # Force travel_date from POST (ensure it's saved even if form quirky) - Enhanced
            travel_date_str = request.POST.get('travel_date', '')
            print(f"DEBUG Post: Raw travel_date from POST: '{travel_date_str}'")  # Key: Check if Flatpickr sets this
            if travel_date_str:
                try:
                    from datetime import datetime
                    parsed_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()
                    cleaned_data['travel_date'] = parsed_date
                    print(f"DEBUG Post: Parsed travel_date from POST '{travel_date_str}' to {parsed_date}")
                except ValueError:
                    print(f"DEBUG Post: Invalid travel_date '{travel_date_str}' - falling back")
                    cleaned_data['travel_date'] = self.tour.start_date or date.today()  # Fallback to tour or today
            else:
                print("DEBUG Post: No travel_date in POST - falling back")
                cleaned_data['travel_date'] = self.tour.start_date or date.today()

            print("Form valid - storing for confirmation")
            print(f"DEBUG Post: Final cleaned travel_date: {cleaned_data['travel_date']} (type: {type(cleaned_data['travel_date'])})")

            # Compute configs for reference
            configs = compute_pricing(
                cleaned_data['tour_type'], self.tour.id,
                request.POST, request.session
            )

            # Parse selected
            selected_config_str = cleaned_data.get('selected_configuration', '0')
            selected_index = int(selected_config_str) if selected_config_str.isdigit() else 0
            selected_room_config = configs[selected_index] if selected_index < len(configs) else {}



            # Store in session—no save yet
            proposal_data = {
                'tour_type': cleaned_data['tour_type'],
                'tour_id': cleaned_data['tour_id'],
                'customer_name': cleaned_data['customer_name'],
                'customer_email': cleaned_data['customer_email'],
                'customer_phone': cleaned_data.get('customer_phone', ''),
                'customer_address': cleaned_data.get('customer_address', ''),
                'nationality': cleaned_data.get('nationality', ''),
                'notes': cleaned_data.get('notes', ''),
                'number_of_adults': cleaned_data['number_of_adults'],
                'number_of_children': cleaned_data['number_of_children'],
                'child_ages': cleaned_data.get('child_ages', []),
                'travel_date': cleaned_data['travel_date'].isoformat() if hasattr(cleaned_data['travel_date'], 'isoformat') else str(cleaned_data['travel_date']),
                'selected_configuration': selected_index,
                'currency': cleaned_data['currency'],
                'supplier_email': self.tour.supplier_email,
                'estimated_price': str(selected_room_config.get('total_price', '0')),  # Str for JSON
                'room_config': {'options': configs},
                'selected_room_config': selected_room_config,
                'number_of_infants': sum(1 for age in cleaned_data.get('child_ages', []) if age < self.tour.child_age_min),
            }

            temp_proposal = Proposal(
                number_of_adults=proposal_data['number_of_adults'],
                number_of_children=proposal_data['number_of_children'],
                number_of_infants=proposal_data['number_of_infants'],
                selected_config=proposal_data['selected_room_config'],
                content_type=ContentType.objects.get_for_model(self.tour),
                object_id=self.tour.id,
                travel_date=datetime.strptime(proposal_data['travel_date'], '%Y-%m-%d').date(),
                currency=proposal_data['currency'],
                tour=self.tour,  # For calc
            )
            proposal_data['estimated_price'] = str(selected_room_config.get('total_price', '0'))

            request.session['proposal_data'] = proposal_data
            print(f"DEBUG Post: Saved session travel_date: {proposal_data['travel_date']}")

            print(f"Stored data for confirmation: {len(proposal_data)} keys")

            # Handle AJAX vs non-AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Data saved for confirmation'})
            else:
                # Non-AJAX: FIXED: Redirect to modal loader (your render_confirmation)
                return redirect('bookings:render_confirmation', tour_id=self.tour.id)
        else:
            print(f"DEBUG Post: Form invalid - errors: {form.errors}")  # Add this for validation fails
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # FIXED: Flatten errors to list of strings for JS
                error_messages = []
                for field, errors in form.errors.items():
                    for error in errors:
                        error_messages.append(f"{field.title() if field != '__all__' else 'Form'}: {error}")
                return JsonResponse({'success': False, 'errors': error_messages}, status=400)
            # Non-AJAX: re-render with errors
            return self.form_invalid(form)

class ProposalSuccessView(TemplateView):
    template_name = 'bookings/proposal_success.html'

    def get_context_data(self, **kwargs):  # Fixed: get_context_data, not get_context
        context = super().get_context_data(**kwargs)
        proposal_id = self.kwargs['proposal_id']
        proposal = get_object_or_404(Proposal, id=proposal_id)  # Fixed: get_object_or_404
        tour = proposal.tour
        context['proposal'] = proposal
        context['tour'] = tour
        context['tour_type'] = 'land'  # Or detect from proposal.content_type
        context['site_url'] = settings.SITE_URL  # For links
        context['is_company_tour'] = tour.is_company_tour
        context['status_note'] = ' (Internal review pending)' if tour.is_company_tour else ' (Awaiting supplier confirmation)'
        return context

paypal.configure({
    "mode": "sandbox",  # "live" for prod
    "client_id": config('PAYPAL_CLIENT_ID'),
    "client_secret": config('PAYPAL_CLIENT_SECRET'),
})



logger = logging.getLogger(__name__)  # Assuming defined; add if needed

def compute_pricing(tour_type, tour_id, form_data, session):
    logger.debug(f"compute_pricing inputs: form_data={form_data}, tour_type={tour_type}, tour_id={tour_id}")
    model_map = {'full': "FullTourPage", 'land': LandTourPage, 'day': "DayTourPage"}
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
    if number_of_adults == 0 and (children > 0 or infants > 0):
        logger.warning("No adult provided with children or infants")
        return []

    if tour_type.lower() in ['land', 'full'] and tour.pricing_type == 'Per_room':
        # Full enumeration: Nested loops for all combos (capped for performance)
        max_rooms = number_of_adults  # Max singles = n
        for singles in range(0, number_of_adults + 1):
            remaining_after_singles = number_of_adults - singles
            max_doubles = remaining_after_singles // 2
            for doubles in range(0, max_doubles + 1):
                remaining_after_doubles = remaining_after_singles - doubles * 2
                max_triples = remaining_after_doubles // 3
                for triples in range(0, max_triples + 1):
                    remaining_after_triples = remaining_after_doubles - triples * 3
                    if remaining_after_triples == 0:  # Exact match
                        total_rooms = singles + doubles + triples
                        if total_rooms == 0:
                            continue
                        total_children = children + infants
                        if total_children > total_rooms * max_children_per_room:
                            children_exceed_room_limit = True
                            continue

                        total_price = (
                            (singles * price_sgl) +
                            (doubles * price_dbl) +
                            (triples * price_tpl) +
                            (children * price_chd) +
                            (infants * price_inf)
                        )
                        total_price *= seasonal_factor * price_adjustment * exchange_rate
                        rounded_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        config = {
                            'singles': singles,
                            'doubles': doubles,
                            'triples': triples,
                            'children': children,
                            'infants': infants,
                            'child_ages': child_ages,
                            'total_price': float(rounded_price),
                            'currency': currency,
                            'total_rooms': total_rooms
                        }
                        configurations.append(config)
                        logger.debug(f"Generated config: {config}")

        # Dedupe and sort
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
            (number_of_adults * price_adult) +
            (children * price_chd) +
            (infants * price_inf)
        )
        total_price *= seasonal_factor * price_adjustment * exchange_rate
        rounded_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        configurations = [{
            'singles': 0,
            'doubles': 0,
            'triples': 0,
            'children': children,
            'infants': infants,
            'child_ages': child_ages,
            'total_price': float(rounded_price),
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
        total_price *= seasonal_factor * price_adjustment * exchange_rate
        rounded_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        configurations = [{
            'singles': 0,
            'doubles': 0,
            'triples': 0,
            'children': children,
            'infants': infants,
            'child_ages': child_ages,
            'total_price': float(rounded_price),
            'currency': currency,
            'total_rooms': 0,
            'cheapest': True
        }]
        logger.debug(f"DayTour config: {configurations[0]}")

    logger.info(f"Generated configurations for {tour_type}/{tour_id}: {len(configurations)} items")
    return configurations

class PaymentView(TemplateView):
    template_name = 'bookings/payment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proposal_id = self.kwargs['proposal_id']
        proposal = get_object_or_404(Proposal, id=proposal_id, status='SUPPLIER_CONFIRMED')
        context['proposal'] = proposal
        context['amount'] = str(proposal.estimated_price)  # For JS
        context['paypal_client_id'] = settings.PAYPAL_CLIENT_ID  # JS SDK
        return context

    def post(self, request, proposal_id):  # On approve/capture
        proposal = get_object_or_404(Proposal, id=proposal_id)
        payment_id = request.POST.get('paymentId')
        if not payment_id:
            return JsonResponse({'error': 'No payment ID'}, status=400)

        # Server-side capture (secure)
        payment = paypal.Payment.find(payment_id)
        if payment.state == 'approved':
            payment.execute({'payer_id': request.POST.get('PayerID')})
            if payment.state == 'completed':
                proposal.status = 'PAID'
                proposal.save()

                # Create Booking
                booking = Booking.objects.create(
                    customer_name=proposal.customer_name,
                    customer_email=proposal.customer_email,
                    # ... copy other fields: number_of_adults, travel_date, etc.
                    content_type=proposal.content_type,
                    object_id=proposal.object_id,
                    total_price=proposal.estimated_price,
                    payment_status='PAID',
                    payment_method='PAYPAL',
                    proposal=proposal,
                    configuration_details=proposal.room_config,
                    user=proposal.user,
                )
                booking.save()  # Triggers commission, etc.

                # Send itinerary
                pdf_data = generate_itinerary_pdf(booking)
                send_itinerary_email(booking, pdf_data)

                messages.success(request, "Payment successful! Itinerary sent.")
                return redirect('customer_portal')
        return JsonResponse({'error': 'Payment failed'}, status=400)

@csrf_exempt
def submit_proposal(request, tour_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    session_data = request.session.get('proposal_data')
    if not session_data:
        return JsonResponse({'error': 'No data in session'}, status=400)

    # Parse travel_date
    travel_date_str = session_data['travel_date']
    try:
        travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()
    except ValueError as ve:
        logger.error(f"Invalid travel_date format '{travel_date_str}': {ve}")
        return JsonResponse({'error': 'Invalid travel date format'}, status=400)

    tour = get_object_or_404(LandTourPage, id=tour_id)  # Adjust model as needed
    content_type = ContentType.objects.get_for_model(tour)

    # NEW: Read is_company_tour early from tour
    is_company_tour = getattr(tour, 'is_company_tour', False)
    logger.info(f"Proposal for tour {tour_id}: is_company_tour={is_company_tour}")  # Debug log

    try:
        proposal = Proposal.objects.create(
            customer_name=session_data['customer_name'],
            customer_email=session_data['customer_email'],
            customer_phone=session_data.get('customer_phone', ''),
            customer_address=session_data.get('customer_address', ''),
            nationality=session_data.get('nationality', ''),
            notes=session_data.get('notes', ''),
            content_type=content_type,
            object_id=tour_id,
            number_of_adults=session_data['number_of_adults'],
            number_of_children=session_data['number_of_children'],
            children_ages=session_data['child_ages'],
            travel_date=travel_date,
            supplier_email=session_data['supplier_email'],
            currency=session_data['currency'],
            estimated_price=Decimal(session_data['estimated_price']),
            user=request.user if request.user.is_authenticated else None,
            status='PENDING_SUPPLIER',  # Default; override below
            room_config=session_data.get('room_config', {}),
            selected_config=session_data.get('selected_room_config', {}),
            number_of_infants=session_data.get('number_of_infants', 0),
        )

        # Calculate end_date
        duration = getattr(tour, 'duration_days', 0)
        end_date = proposal.travel_date + timedelta(days=duration)

        # 1. ALWAYS: Send initial client email
        send_proposal_submitted_email(proposal, tour, end_date)

        # 2. CONDITIONAL: Handle based on is_company_tour (from tour)
        if is_company_tour:
            # Company tour: Internal flow
            proposal.status = 'PENDING_INTERNAL'  # Requires STATUS_CHOICES update
            proposal.save()
            send_internal_confirmation_email(proposal, tour, end_date)
            logger.info(f"Internal proposal {proposal.id} created for company tour {tour_id}")
        else:
            # Normal supplier flow
            # Status already 'PENDING_SUPPLIER' from create
            if proposal.supplier_email:
                token = ProposalConfirmationToken.objects.create(proposal=proposal)
                send_supplier_email(proposal, token, tour, end_date)
                logger.info(f"Supplier email sent for proposal {proposal.id}")
            else:
                logger.warning(f"No supplier email for proposal {proposal.id}")

        # Clear session
        if 'proposal_data' in request.session:
            del request.session['proposal_data']

        messages.success(request, f"Proposal {proposal.prop_id} submitted!")
        return JsonResponse({
            'success': True,
            'proposal_id': proposal.id,
            'prop_id': proposal.prop_id,
            'message': 'Proposal submitted successfully! Redirecting to confirmation...',
            'redirect_url': f"{settings.SITE_URL}/bookings/proposal-success/{proposal.id}/",
            'is_company_tour': is_company_tour,  # Optional: For JS/client display
        })

    except Exception as e:
        logger.error(f"Error creating proposal {tour_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def render_confirmation(request, tour_id):
    context = {
        'tour_id': tour_id,
        'submit_url': reverse('bookings:submit_proposal', args=[tour_id]),  # Pre-compute here
    }
    session_data = request.session.get('proposal_data')
    print(f"DEBUG: session_data exists? {bool(session_data)}")  # Keep for now
    if not session_data:
        context['error'] = _("No booking data found. Please start over.")
        print("DEBUG: No session_data - error set")
        # Always render template, no redirect for AJAX compatibility
    else:
        print(f"DEBUG: Raw travel_date in session: '{session_data.get('travel_date', 'MISSING')}' (type: {type(session_data.get('travel_date'))})")
        try:
            tour = get_object_or_404(LandTourPage, id=tour_id)
        except Http404:
            context['error'] = _("Invalid tour selected.")
            print("DEBUG: Tour 404 - error set")
            # Render with error
        else:
            # Fallback for missing travel_date
            if 'travel_date' not in session_data or not session_data['travel_date']:
                from datetime import date
                session_data['travel_date'] = date.today().isoformat()
                print(f"DEBUG: Fallback triggered - set to {session_data['travel_date']}")

            # Safe access to avoid KeyError
            context.update({
                'tour': tour,
                'tour_type': session_data.get('tour_type', 'land'),
                'form_data': session_data,
                'booking_data': {'tourName': tour.name},
                'selected_room_config': session_data.get('selected_room_config', {}),
                'tour_duration': getattr(tour, 'duration_days', 0),
                'selected_configuration_index': session_data.get('selected_configuration', 0),
            })
            print(f"DEBUG: Final form_data.travel_date for template: '{session_data['travel_date']}'")
            print(f"DEBUG Render: Context tour_id = {context['tour_id']} (type: {type(context['tour_id'])})")
            print(f"DEBUG Render: submit_url = {context['submit_url']}")

    return render(request, 'bookings/partials/confirm_proposal.html', context)

def render_pricing(request, tour_type, tour_id):
    logger.debug(f"render_pricing called with POST: {request.POST}")
    # Prioritize currency from POST data
    currency = request.POST.get('currency', request.session.get('currency', 'USD')).upper()
    request.session['currency'] = currency  # Update session currency
    logger.debug(f"Selected currency: {currency}")

    configurations = compute_pricing(tour_type, tour_id, request.POST, request.session)
    model_map = {'full': "FullTourPage", 'land': LandTourPage, 'day': "DayTourPage"}
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
    response_content = render_to_string('bookings/partials/pricing_options.html', context, request=request)
    logger.debug(f"Rendered pricing_options.html with context: {context}")
    return HttpResponse(response_content, content_type='text/html')

def confirm_proposal(request, proposal_id: int) -> HttpResponse:
    # Scoped to single object
    proposal = get_object_or_404(
        Proposal.objects.select_related('content_type'),
        id=proposal_id
    )

    tour = proposal.tour
    if not tour:
        messages.error(request, "Tour not found for this proposal.")
        return redirect('bookings:manage_proposals')

    is_company_tour = getattr(tour, 'is_company_tour', False)
    pending_status = 'PENDING_INTERNAL' if is_company_tour else 'PENDING_SUPPLIER'

    if proposal.status != pending_status:
        messages.error(request, f"Proposal not pending {'internal' if is_company_tour else 'supplier'} confirmation.")
        return redirect('bookings:manage_proposals')

    # Placeholder payment link (PayPal placeholder—update later)
    proposal.payment_link = f"{settings.SITE_URL}/p-methods/paypal/checkout/{proposal.id}/"
    # proposal.payment_link = f"{settings.SITE_URL}/bookings/payment/success/{proposal.id}/"  # FIXED: Use existing success view for fake checkout        proposal.status = 'SUPPLIER_CONFIRMED'

    proposal.status = 'SUPPLIER_CONFIRMED'
    proposal.save()

    # FIX: Call without extra kwargs (func handles tour/end_date internally)
    send_preconfirmation_email(proposal)

    # Clear stray session (defensive)
    if 'proposal_data' in request.session:
        del request.session['proposal_data']

    msg = f"Proposal {proposal.prop_id or proposal.id} confirmed ({'internally' if is_company_tour else 'by supplier'}). Payment link sent to {proposal.customer_email}."
    messages.success(request, msg)

    return redirect('bookings:manage_proposals')

def confirm_proposal_by_token(request, token: str) -> HttpResponse:
    try:
        token_obj = ProposalConfirmationToken.objects.get(token=token)
        if not token_obj.is_valid():
            messages.error(request, "Invalid or expired confirmation link.")
            return render(request, 'bookings/confirmation_error.html')
        proposal = token_obj.proposal
        if not proposal.tour:
            messages.error(request, "Tour not found.")
            return render(request, 'bookings/confirmation_error.html')

        # For company tours: Redirect to portal (no token support)
        if getattr(proposal.tour, 'is_company_tour', False):
            messages.info(request, "Company tour proposals must be confirmed via the internal portal.")
            return redirect('bookings:manage_proposals')

        # Normal supplier flow
        proposal.payment_link = f"{settings.SITE_URL}/p-methods/paypal/checkout/{proposal.id}/"  # FIXED: Checkout page        proposal.status = 'SUPPLIER_CONFIRMED'
        proposal.save()
        token_obj.used_at = timezone.now()
        token_obj.save()
        send_preconfirmation_email(proposal)
        return render(request, 'bookings/confirmation_success.html', {
            'proposal': proposal,
            'site_url': settings.SITE_URL,
        })
    except ProposalConfirmationToken.DoesNotExist:
        messages.error(request, "Invalid confirmation link.")  # FIXED: "Reject" → "Invalid"
        return render(request, 'bookings/confirmation_error.html')

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

    model_map = {'full': "FullTourPage", 'land': LandTourPage, 'day': "DayTourPage"}
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
    model_map = {'full': "FullTourPage", 'land': LandTourPage, 'day': "DayTourPage"}
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

def customer_portal(request):
    proposals = Proposal.objects.select_related('content_type', 'user').prefetch_related('confirmation_tokens')
    bookings = Booking.objects.select_related('content_type', 'user')

    # Search/filter logic (email/ID/status)
    email = request.GET.get('email', '').strip()
    id_filter = request.GET.get('id', '').strip()
    status = request.GET.get('status', 'all')

    if email:
        proposals = proposals.filter(customer_email__icontains=email)
        bookings = bookings.filter(customer_email__icontains=email)
        logger.info(f"Filtering by email: {email}")
    if id_filter:
        proposals = proposals.filter(
            Q(prop_id__icontains=id_filter) | Q(id__icontains=id_filter)
        )
        bookings = bookings.filter(
            Q(book_id__icontains=id_filter) | Q(id__icontains=id_filter)
        )
        logger.info(f"Filtering by ID: {id_filter}")
    if status != 'all':
        proposals = proposals.filter(status=status)
        bookings = bookings.filter(status=status)
        logger.info(f"Filtering by status: {status}")

    # Pagination (separate—10 each)
    proposals_paginator = Paginator(proposals, 10)
    bookings_paginator = Paginator(bookings, 10)
    proposals = proposals_paginator.get_page(request.GET.get('proposals_page', 1))
    bookings = bookings_paginator.get_page(request.GET.get('bookings_page', 1))

    context = {
        'proposals': proposals,
        'bookings': bookings,
        'email': email,
        'id': id_filter,
        'current_status': status,
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
        return JsonResponse({'error': 'Proposal not to found'}, status=404)

