# bookings/urls.py
from django.urls import path

from bookings.api_views import AvailableDatesView
from bookings.utils import  manage_proposals, payment_cancel, payment_success, proposal_detail, reject_proposal
from . import views

app_name = 'bookings'


urlpatterns = [
    # Core flow
    path('start/<int:tour_id>/', views.BookingStartView.as_view(), name='booking_start'),
    path('pay/<int:proposal_id>/', views.PaymentView.as_view(), name='payment_view'),
    path('payment/success/<int:proposal_id>/', payment_success, name='payment_success'),
    path('payment/cancel/<int:proposal_id>/', payment_cancel, name='payment_cancel'),
    path('customer-portal/', views.customer_portal, name='customer_portal'),
    path('manage/bookings/', views.manage_bookings, name='manage_bookings'),
    # Proposals
    path('proposal-success/<int:proposal_id>/', views.ProposalSuccessView.as_view(), name='proposal_success'),
    path('proposal/<int:proposal_id>/status/', views.proposal_status, name='proposal_status'),  # Fixed name (was 'proposal_status' but URL 'proposal_status')
    path('proposal/<int:proposal_id>/reject/', reject_proposal, name='reject_proposal'),
    path('proposal/<str:token>/confirm-token/', views.confirm_proposal_by_token, name='confirm_proposal_by_token'),
    path('manage/proposals/<int:proposal_id>/confirm/', views.confirm_proposal, name='confirm_proposal'),    # Admin/portal (keep if used)
    path('manage/proposals/', manage_proposals, name='manage_proposals'),
    path('manage/proposals/<int:proposal_id>/detail/', proposal_detail, name='proposal_detail'),
    path('submit-proposal/<int:tour_id>/', views.submit_proposal, name='submit_proposal'),  # Function view for AJAX save
    path('confirm/<int:tour_id>/', views.render_confirmation, name='render_confirmation'),  # FIXED: Matches JS fetch
    # Pricing (AJAX)
    path('calculate_pricing/<str:tour_type>/<int:tour_id>/', views.render_pricing, name='render_pricing'),


    # Legacy (comment out if not needed; remove later)
    # path('child_ages/', views.child_ages, name='child_ages'),
    # path('partners/', views.get_partners, name='get_partners'),
]