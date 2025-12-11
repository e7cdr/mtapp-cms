from django.urls import path
from bookings import accommodation_views

app_name = "accommodation"

urlpatterns = [
    path('<int:accommodation_id>/book/', accommodation_views.accommodation_booking_modal, name='accommodation_booking'),
    path('<int:accommodation_id>/price-preview/', accommodation_views.accommodation_price_preview, name='price_preview'),
]
