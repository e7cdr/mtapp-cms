import json  # FIXED: Add for JSON parsing
import logging  # FIXED: Use standard logging
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

logger = logging.getLogger(__name__)  # FIXED: Proper logger

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
            # FIXED: Parse JSON body (frontend sends JSON, not form)
            body_data = json.loads(request.body)
            proposal_id = body_data.get('proposal_id')
            cart = body_data.get('cart', [])
            
            if not proposal_id:
                return JsonResponse({'error': 'Missing proposal_id'}, status=400)
            
            proposal = get_object_or_404(Proposal, id=proposal_id)
            
            # FIXED: Build items from cart (not hardcoded)
            items = []
            for item_data in cart:
                item = Item(
                    name=item_data['name'],
                    description="",  # Optional
                    category=ItemCategory.DIGITAL_GOODS,  # Or PHYSICAL_GOODS for tours
                    quantity=item_data['quantity'],
                    unit_amount=Money(currency_code=proposal.currency, value=str(item_data['price'])),
                )
                items.append(item)
            
            order_request = OrderRequest(
                intent=CheckoutPaymentIntent.CAPTURE,
                purchase_units=[
                    PurchaseUnitRequest(
                        amount=AmountWithBreakdown(
                            currency_code=proposal.currency,
                            value=str(proposal.estimated_price),  # Or sum(cart prices)
                            breakdown=AmountBreakdown(
                                item_total=Money(currency_code=proposal.currency, value=str(proposal.estimated_price))
                            ),
                        ),
                        items=items,
                    ),
                ],
            )
            
            order = orders_controller.create_order({"body": order_request})
            logger.info(f"Order created for proposal {proposal_id}: {order.body.id}")
            return JsonResponse({'id': order.body.id})
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON for proposal {proposal_id}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except ErrorException as e:
            logger.error(f"Order creation failed for {proposal_id}: {e}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({'error': 'Internal server error'}, status=500)


class PayPalOrdersCaptureView(View):
    def post(self, request, order_id):
        try:
            # FIXED: Parse JSON (though body is optional)
            body_data = json.loads(request.body) if request.body else {}
            proposal_id = body_data.get('proposal_id')
            
            order = orders_controller.capture_order({"id": order_id, "prefer": "return=representation"})
            logger.info(f"Order {order_id} captured: {order.body.status}")
            
            if proposal_id and order.body.status == 'COMPLETED':
                # FIXED: Call payment_success if exists (adjust import/path as needed)
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
            'amount': str(proposal.estimated_price),  # FIXED: str for JS
            'site_url': settings.SITE_URL,
        }
        return render(request, 'paypal/paypal_checkout.html', context)