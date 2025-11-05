from django.urls import path
from . import views


app_name = 'p_methods'

urlpatterns = [
    path('paypal/checkout/<int:proposal_id>/', views.PayPalCheckoutView.as_view(), name='paypal_checkout'),
    path('api/orders', views.PayPalOrdersCreateView.as_view(), name='paypal_orders_create'),
    path('api/orders/<str:order_id>/capture/', views.PayPalOrdersCaptureView.as_view(), name='paypal_orders_capture'),
]