import base64
import json
import logging
from django.http import Http404, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.logging.configuration.api_logging_configuration import LoggingConfiguration, RequestLoggingConfiguration, ResponseLoggingConfiguration
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient

from paypalserversdk.models.amount_breakdown import AmountBreakdown
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.models.money import Money
from paypalserversdk.models.item import Item
from paypalserversdk.models.item_category import ItemCategory
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.exceptions.error_exception import ErrorException
import requests
import urllib
from bookings.models import AccommodationBooking, Booking, Proposal
from decouple import config

from decimal import Decimal, ROUND_HALF_UP

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

class PayPalClientTokenView(View):
    def get(self, request):
        client_id = config("PAYPAL_SANDBOX_CLIENT_ID")
        client_secret = config("PAYPAL_SANDBOX_CLIENT_SECRET")

        auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = requests.post(
            "https://api-m.sandbox.paypal.com/v1/identity/generate-token",
            headers=headers,
            json={},  # empty body is required for basic client token
            timeout=15
        )

        if response.status_code != 200:
            logger.error(f"PayPal client-token request failed {response.status_code}: {response.text}")
            return JsonResponse({"error": f"PayPal error: {response.text}"}, status=500)

        data = response.json()
        return JsonResponse({
            "access_token": data["client_token"],  # keeps old integrations happy
            "client_token": data["client_token"],  # standard for most examples
            "expires_in": data.get("expires_in", 32400)
        })

class PayPalOrdersCreateView(View):
    def post(self, request):
        try:
            # Parse incoming JSON request body
            body_data = json.loads(request.body) if request.body else {}
            print("PARSED BODY:", body_data)     # ← AND THIS ONE
            intent = body_data.get('intent', 'CAPTURE')
            purchase_units_data = body_data.get('purchase_units', [{}])

            if not purchase_units_data:
                raise ValueError("No purchase_units provided")

            # Process the first purchase_unit (assuming single unit for simplicity)
            pu_data = purchase_units_data[0]
            amount_data = pu_data.get('amount', {})
            currency_code = amount_data.get('currency_code', 'USD')
            value_str = amount_data.get('value')

            items_data = pu_data.get('items', [])

            if items_data:
                # Existing detailed flow: calculate from items
                total_amount = Decimal('0.00')
                for item_data in items_data:
                    unit_value = item_data.get('unit_amount', {}).get('value', '0')
                    unit_amount = Decimal(str(unit_value))
                    quantity = int(item_data.get('quantity', 1))
                    total_amount += unit_amount * quantity

                    # Use first item's currency if not already set
                    if currency_code == 'USD':
                        currency_code = item_data.get('unit_amount', {}).get('currency_code', 'USD')

                total_amount = total_amount.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                value_str = str(total_amount)

                # Clean names (keep your existing fix)
                for item_data in items_data:
                    name = item_data.get('name', '')
                    item_data['name'] = name.replace("'", "")

                items = [
                    Item(
                        name=item_data['name'],
                        unit_amount=Money(
                            currency_code=currency_code,
                            value=str(item_data['unit_amount']['value'])
                        ),
                        quantity=item_data['quantity'],
                        description=item_data.get('description', ''),
                        category=ItemCategory.DIGITAL_GOODS
                    ) for item_data in items_data
                ]

                breakdown = AmountBreakdown(
                    item_total=Money(currency_code=currency_code, value=value_str)
                )
            else:
                # Simple amount-only flow (standard Buttons)
                items = None
                breakdown = None

            if not value_str or Decimal(value_str) <= 0:
                raise ValueError("Invalid or missing amount value")
            
            description = "Milano Travel Booking"

            # Try to make it more specific using context from the request (optional but recommended)
            # If you pass booking_id or proposal_id in the createOrder body, you can fetch them here.
            # For now, we'll use a simple fallback; improve later if needed.
            if 'booking_id' in body_data:
                try:
                    from bookings.models import AccommodationBooking
                    booking = AccommodationBooking.objects.get(id=body_data['booking_id'])
                    description = f"{booking.accommodation.name} • Adults: {booking.adults} - Children: {booking.children}. From {booking.check_in} to {booking.check_out}"
                except AccommodationBooking.DoesNotExist:
                    pass
            elif 'proposal_id' in body_data:
                try:
                    from bookings.models import Proposal
                    proposal = Proposal.objects.get(id=body_data['proposal_id'])
                    description = f"Tour: {proposal.tour.name} ~ Travel Date: {proposal.travel_date} -- Adults: {proposal.number_of_adults} + Children: {proposal.number_of_children} + Infrants: {proposal.number_of_infants}. Room Configuration:{proposal.selected_config}"
                except Proposal.DoesNotExist:
                    pass

            # Build purchase unit
            pu = PurchaseUnitRequest(
                amount=AmountWithBreakdown(
                    currency_code=currency_code,
                    value=value_str,
                    breakdown=breakdown
                ) if breakdown else AmountWithBreakdown(
                    currency_code=currency_code,
                    value=value_str
                ),
                items=items,
                description=description
            )

            order_request = OrderRequest(
                intent=intent,
                purchase_units=[pu]
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
            body_data = json.loads(request.body) if request.body else {}
            proposal_id = body_data.get('proposal_id')
            booking_id = body_data.get('booking_id')

            order = orders_controller.capture_order({"id": order_id, "prefer": "return=representation"})
            logger.info(f"Order {order_id} captured: {order.body.status}")

            if order.body.status == 'COMPLETED':
                success_url = None  # ← initialize here

                if proposal_id:
                    proposal = get_object_or_404(Proposal, id=proposal_id)
                    if proposal.status != 'PAID':
                        proposal.status = 'PAID'
                        proposal.save(update_fields=['status'])

                    # Create Booking from Proposal if none exists
                    from django.contrib.contenttypes.models import ContentType

                    tour_page = proposal.tour  # assuming Proposal has FK to tour page
                    if not tour_page:
                        raise ValueError("Proposal missing linked tour page")

                    booking, created = Booking.objects.get_or_create(
                        proposal=proposal,
                        defaults={
                            'travel_date': proposal.travel_date,
                            'number_of_adults': proposal.number_of_adults,
                            'number_of_children': proposal.number_of_children or 0,
                            'number_of_infants': proposal.number_of_infants or 0,
                            'children_ages': proposal.children_ages or [],
                            'customer_name': proposal.customer_name,
                            'customer_email': proposal.customer_email,
                            'customer_phone': proposal.customer_phone or '',
                            'nationality': proposal.nationality or '',
                            'customer_address': proposal.customer_address or '',
                            'notes': proposal.notes or '',
                            'total_price': proposal.estimated_price,
                            'status': 'PAID',
                            'content_type': ContentType.objects.get_for_model(tour_page),
                            'object_id': tour_page.id,
                        }
                    )
                    if created:
                        logger.info(f"Created Booking {booking.id} from paid Proposal {proposal.id}")

                    success_url = reverse('bookings:payment_success', args=[proposal_id])

                elif booking_id:
                    success_url = reverse('bookings:payment_success', args=[booking_id])

                else:
                    return JsonResponse({'error': 'No proposal or booking ID provided'}, status=400)

                if success_url is None:
                    return JsonResponse({'error': 'Failed to determine success URL'}, status=500)

                return JsonResponse({'status': 'COMPLETED', 'redirect': success_url})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except ErrorException as e:
            logger.error(f"Capture failed for {order_id}: {e}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)
        
class PayPalCheckoutView(View):
    def get(self, request, proposal_id=None, booking_id=None):
        client_id = config("PAYPAL_CLIENT_ID")
        if not client_id:
            return HttpResponse("PayPal not configured", status=500)

        if booking_id:
            # ACCOMMODATION
            booking = get_object_or_404(AccommodationBooking, id=booking_id)
            if booking.status != 'PENDING_PAYMENT':
                raise Http404
            context = {
                'amount': str(booking.total_price.quantize(Decimal('0.01'))),
                'currency': 'USD',
                'item_name': f"{booking.accommodation.name} • Adults: {booking.adults} - Children: {booking.children}. From {booking.check_in} to {booking.check_out}",
                'custom_id': f"ACC_{booking.id}",
                'booking_id': booking.id,
            }
        else:
            # TOUR
            proposal = get_object_or_404(Proposal, id=proposal_id)
            if not proposal.tour:
                raise Http404
            context = {
                'proposal': proposal,
                'amount': str(proposal.estimated_price.quantize(Decimal('0.01'))),
                'currency': 'USD',
                'item_name': f"{proposal.tour.name} ~ {proposal.travel_date} - Ad: {proposal.number_of_adults} + Chd: {proposal.number_of_children} + In: {proposal.number_of_infants}. {proposal.selected_config}",
                'custom_id': f"PROP_{proposal.id}",
                'proposal_id': proposal.id,
            }

        context['client_id'] = client_id
        return render(request, 'paypal/paypal_checkout.html', context)


