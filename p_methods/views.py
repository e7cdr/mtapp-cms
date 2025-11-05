from datetime import timedelta, date
import json
import logging
from django.http import Http404, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.conf import settings
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.logging.configuration.api_logging_configuration import LoggingConfiguration, RequestLoggingConfiguration, ResponseLoggingConfiguration
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient
from paypalserversdk.controllers.orders_controller import OrdersController
from paypalserversdk.controllers.payments_controller import PaymentsController
from paypalserversdk.models.amount_breakdown import AmountBreakdown
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.models.capture_request import CaptureRequest
from paypalserversdk.models.money import Money
from paypalserversdk.models.item import Item
from paypalserversdk.models.item_category import ItemCategory
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.exceptions.error_exception import ErrorException
from paypalserversdk.api_helper import ApiHelper
from bookings.models import Proposal
from decouple import config
from bookings.utils import get_30_day_used_slots  # FIXED: Import required utils

from decimal import Decimal, ROUND_HALF_UP

from bookings.views import calculate_demand_factor, get_exchange_rate, get_remaining_capacity

logger = logging.getLogger(__name__)

# PayPal Client (unchanged)
client_credentials = ClientCredentialsAuthCredentials(
    o_auth_client_id=config("PAYPAL_CLIENT_ID"),
    o_auth_client_secret=config("PAYPAL_CLIENT_SECRET"),
)
paypal_client = PaypalServersdkClient(
    client_credentials_auth_credentials=client_credentials,
    logging_configuration=LoggingConfiguration(
        log_level=logging.INFO,
        mask_sensitive_headers=False,
        request_logging_config=RequestLoggingConfiguration(log_headers=True, log_body=True),
        response_logging_config=ResponseLoggingConfiguration(log_headers=True, log_body=True),
    ),
)
orders_controller = paypal_client.orders
payments_controller = paypal_client.payments


class PayPalOrdersCreateView(View):
    def post(self, request):
        try:
            # Parse incoming JSON request body
            body_data = json.loads(request.body) if request.body else {}
            intent_str = body_data.get('intent', 'CAPTURE')
            purchase_units_data = body_data.get('purchase_units', [{}])

            if not purchase_units_data:
                raise ValueError("No purchase_units provided")

            # Process the first purchase_unit (assuming single unit for simplicity)
            pu_data = purchase_units_data[0]
            items_data = pu_data.get('items', [])

            if not items_data:
                raise ValueError("No items provided in purchase_units")

            # FIXED: Calculate total from items to avoid null values
            total_amount = Decimal('0.00')
            currency_code = 'USD'  # Default; override if provided
            for item_data in items_data:
                unit_amount = Decimal(str(item_data.get('unit_amount', {}).get('value', '0')))
                quantity = int(item_data.get('quantity', 1))
                total_amount += unit_amount * quantity
                # Use first item's currency
                if not currency_code or currency_code == 'USD':  # FIXED: Simple override
                    currency_code = item_data['unit_amount'].get('currency_code', 'USD')

            # Round to 2 decimals
            total_amount = total_amount.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
            total_str = str(total_amount)

            # FIXED: Ensure item names are clean (remove problematic quotes)
            for item_data in items_data:
                name = item_data.get('name', '')
                item_data['name'] = name.replace("'", "")  # Strip single quotes to avoid JSON issues

            # FIXED: Direct enum access for intent
            intent = CheckoutPaymentIntent.CAPTURE  # Hardcoded for 'CAPTURE'; add mapping if needed for 'AUTHORIZE'

            order_request = OrderRequest(
                intent=intent,
                purchase_units=[
                    PurchaseUnitRequest(
                        amount=AmountWithBreakdown(
                            currency_code=currency_code,
                            value=total_str,  
                            breakdown=AmountBreakdown(
                                item_total=Money(currency_code=currency_code, value=total_str)  # FIXED: Matches sum
                            )
                        ),
                        items=[
                            Item(
                                name=item_data['name'],
                                unit_amount=Money(
                                    currency_code=currency_code,
                                    value=str(item_data['unit_amount']['value'])
                                ),
                                quantity=item_data['quantity'],
                                description=item_data.get('description', ''),
                                category=ItemCategory.DIGITAL_GOODS  # FIXED: Direct enum access—no () or string arg
                            ) for item_data in items_data
                        ]
                    )
                ]
            )

            # Create the order
            order = orders_controller.create_order({"body": order_request, "prefer": "return=representation"})
            logger.info(f"Order created successfully: {order.body.id}")

            return JsonResponse({'id': order.body.id})

        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            return JsonResponse({'error': str(ve)}, status=400)
        except ErrorException as e:
            debug_id = getattr(e, 'debug_id', 'unknown')
            details = getattr(e, 'details', [])
            logger.error(f"PayPal error: {e}, debug_id={debug_id}, details={details}")
            return JsonResponse({'error': f'PayPal validation failed: {e.message} (debug_id: {debug_id})'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({'error': 'Internal server error'}, status=500)
        
class PayPalOrdersCaptureView(View):
    def post(self, request, order_id):
        try:
            # Parse JSON (though body is optional)
            body_data = json.loads(request.body) if request.body else {}
            proposal_id = body_data.get('proposal_id')
            
            order = orders_controller.capture_order({"id": order_id, "prefer": "return=representation"})
            logger.info(f"Order {order_id} captured: {order.body.status}")
            
            if proposal_id and order.body.status == 'COMPLETED':
                # Call payment_success if exists (adjust import/path as needed)
                from bookings.views import payment_success  # Assume in bookings/views.py
                return payment_success(request, int(proposal_id))
            
            return JsonResponse({'status': order.body.status})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except ErrorException as e:
            logger.error(f"Capture failed for {order_id}: {e}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({'error': 'Internal server error'}, status=500)



class PayPalCheckoutView(View):
    
    def get(self, request, proposal_id):
        proposal = get_object_or_404(Proposal, id=proposal_id)
        client_id = config("PAYPAL_CLIENT_ID")
        if not client_id:
            logger.error("PAYPAL_CLIENT_ID not set in .env")
            return HttpResponse("PayPal configuration error—contact support.", status=500)
        
        if not proposal.tour:
            raise Http404("Tour not found for this proposal.")
        
        tour = proposal.tour
        # Calculate end_date
        duration = getattr(tour, 'duration_days', 0)
        end_date = proposal.travel_date + timedelta(days=duration)
        
        # Effective children/infants from ages (mirror compute_pricing)
        child_age_min = getattr(tour, 'child_age_min', 0)  # Assume 2 or model default
        effective_children_ages = [age for age in proposal.children_ages if age >= child_age_min]
        effective_infants_ages = [age for age in proposal.children_ages if age < child_age_min]
        effective_children = len(effective_children_ages)
        effective_infants = len(effective_infants_ages)
        
        # FIXED: Determine tour_type for accurate price_adult in per_person
        tour_class_name = tour.__class__.__name__.lower()
        is_full_or_land = any(t in tour_class_name for t in ['fulltourpage', 'landtourpage'])
        
        # Extract pricing details (mirror compute_pricing logic)
        pricing_type = getattr(tour, 'pricing_type', 'Per_room')
        
        # Base prices (universal)
        price_child = Decimal(str(getattr(tour, 'price_child', getattr(tour, 'price_chd', '0'))))
        price_infant = Decimal(str(getattr(tour, 'price_inf', '0')))
        
        # Room prices (if Per_room)
        price_sgl = Decimal(str(getattr(tour, 'price_sgl', '0')))
        price_dbl = Decimal(str(getattr(tour, 'price_dbl', '0')))
        price_tpl = Decimal(str(getattr(tour, 'price_tpl', '0')))
        
        # FIXED: Set price_adult based on tour_type for per_person consistency
        if is_full_or_land:
            price_adult = price_sgl
        else:
            price_adult = Decimal(str(getattr(tour, 'price_adult', '0')))
        
        # FIXED: Compute actual factors to match compute_pricing (for accurate subtotals summing to estimated_price)
        seasonal_factor = Decimal(str(getattr(tour, 'seasonal_factor', '1.0')))
        demand_factor = Decimal('0')
        
        # Capacity-based demand (fallback, overridden below)
        if proposal.travel_date:
            try:
                travel_date = date.fromisoformat(str(proposal.travel_date)) if hasattr(proposal.travel_date, 'isoformat') else proposal.travel_date
                capacity = get_remaining_capacity(proposal.object_id, travel_date, tour.__class__, duration)
                if 'total_remaining' in capacity:
                    demand_factor = calculate_demand_factor(capacity['total_remaining'], sum(d['total_daily'] for d in capacity['per_day']))
                else:
                    demand_factor = Decimal('0')
                    logger.warning("No capacity data—default demand_factor=0")
            except (ValueError, Exception) as e:
                demand_factor = Decimal('0')
                logger.warning(f"Error computing capacity demand_factor: {e}—default demand_factor=0")
        price_adjustment = Decimal('1') + Decimal('0.2') * demand_factor
        
        # Override with 30-day demand
        try:
            demand_info = get_30_day_used_slots(proposal.object_id, tour.__class__)
            full_percent = demand_info['full_percent']
            if isinstance(full_percent, (int, float)):
                full_percent = Decimal(str(full_percent))
            model_demand_factor = Decimal(str(getattr(tour, 'demand_factor', '0')))
            demand_factor = model_demand_factor * full_percent
            price_adjustment = Decimal('1') + demand_factor
            logger.debug(f"Computed 30-day demand_factor={demand_factor}, price_adjustment={price_adjustment}")
        except Exception as e:
            logger.warning(f"Error computing 30-day demand_factor: {e}—using fallback adjustment {price_adjustment}")
        
        # Exchange rate
        currency = request.session.get('currency', 'USD')
        exchange_rate = get_exchange_rate(currency)
        if exchange_rate <= Decimal('0'):
            logger.warning(f"Invalid exchange rate for {currency}: {exchange_rate}, falling back to USD")
            currency = 'USD'
            request.session['currency'] = currency
            exchange_rate = Decimal('1.0')
        factor = seasonal_factor * price_adjustment * exchange_rate
        
        # Adjusted rates (for "Qty x Rate")
        adjusted_price_adult = price_adult * factor
        adjusted_price_child = price_child * factor
        adjusted_price_infant = price_infant * factor
        adjusted_price_sgl = price_sgl * factor
        adjusted_price_dbl = price_dbl * factor
        adjusted_price_tpl = price_tpl * factor
        
        # FIXED: Use selected_config for configuration_details to match qty with subtotals
        configuration_details = proposal.selected_config if proposal.selected_config else {}
        
        # Subtotals (qty * adjusted_rate—use effective for children/infants)
        adult_subtotal = proposal.number_of_adults * adjusted_price_adult
        child_subtotal = effective_children * adjusted_price_child
        infant_subtotal = effective_infants * adjusted_price_infant
        per_person_details = {
            'adult_subtotal': adult_subtotal,
            'child_subtotal': child_subtotal,
            'infant_subtotal': infant_subtotal,
            'total_breakdown': adult_subtotal + child_subtotal + infant_subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),  # FIXED: Quantize for precision
        }
        
        # Per_room subtotals (if config—apply factor if base)
        room_subtotals = {}
        if pricing_type == 'Per_room' and proposal.selected_config:
            selected_config = proposal.selected_config
            singles_sub = selected_config.get('singles', 0) * adjusted_price_sgl
            doubles_sub = selected_config.get('doubles', 0) * adjusted_price_dbl
            triples_sub = selected_config.get('triples', 0) * adjusted_price_tpl
            children_sub = effective_children * adjusted_price_child
            infants_sub = effective_infants * adjusted_price_infant
            room_subtotals = {
                'singles_subtotal': singles_sub,
                'doubles_subtotal': doubles_sub,
                'triples_subtotal': triples_sub,
                'children_subtotal': children_sub,
                'infants_subtotal': infants_sub,
                'total_breakdown': (singles_sub + doubles_sub + triples_sub + children_sub + infants_sub).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),  # FIXED: Quantize for precision
            }
        
        context = {
            'proposal': proposal,
            'tour': tour,
            'end_date': end_date,
            'configuration_details': configuration_details,  # FIXED: Use selected_config for consistent qty/subtotal
            'is_company_tour': getattr(tour, 'is_company_tour', False),
            'site_url': settings.SITE_URL,
            'pricing_type': pricing_type,
            'per_person_details': per_person_details,
            'room_subtotals': room_subtotals,
            'adjusted_price_adult': adjusted_price_adult,
            'adjusted_price_child': adjusted_price_child,
            'adjusted_price_infant': adjusted_price_infant,
            'adjusted_price_sgl': adjusted_price_sgl,
            'adjusted_price_dbl': adjusted_price_dbl,
            'adjusted_price_tpl': adjusted_price_tpl,
            'factor': factor,
            'effective_children': effective_children,  # NEW: For template
            'effective_infants': effective_infants,
            'amount': str(proposal.estimated_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'currency': currency,
            'client_id': client_id,  # JS SDK
        }
        return render(request, 'paypal/paypal_checkout.html', context)