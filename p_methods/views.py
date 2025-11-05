import json
import logging
from django.http import JsonResponse, HttpResponse
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
        
        context = {
            'proposal': proposal,
            'tour': proposal.tour,
            'client_id': client_id,
            'currency': proposal.currency,
            'amount': str(proposal.estimated_price),  # str for JS
            'site_url': settings.SITE_URL,
        }
        return render(request, 'paypal/paypal_checkout.html', context)
    