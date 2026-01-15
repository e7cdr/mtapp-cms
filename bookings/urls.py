# bookings/urls.py
from django.urls import path

from bookings.tours_utils import  booking_management, manage_proposals, payment_cancel, proposal_detail, reject_proposal, booking_detail
from bookings.utils.pricing import render_pricing
from . import views

app_name = 'bookings'


urlpatterns = [
    # Core flow
    path('customer-portal/', views.customer_portal, name='customer_portal'),
    path('management/', booking_management, name='booking_management'),
    path('payment/cancel/<int:proposal_id>/', payment_cancel, name='payment_cancel'),
    path('payment-success/<int:pk>/', views.payment_success, name='payment_success'),
    path('manage/bookings/<int:booking_id>/detail/', booking_detail, name='booking_detail'),
    
    # Dynamic booking start — GOOD
    path('<str:tour_type>/<int:tour_id>/book/', views.BookingStartView.as_view(), name='booking_start'),
    
    # Proposals — FIXED: now include tour_type
    path('proposal/<int:proposal_id>/reject/', reject_proposal, name='reject_proposal'),
    path('submit-proposal/<str:tour_type>/<int:tour_id>/', views.submit_proposal, name='submit_proposal'),
    path('confirm/<str:tour_type>/<int:tour_id>/', views.render_confirmation, name='render_confirmation'),
    path('proposal/<int:proposal_id>/status/', views.proposal_status, name='proposal_status'),
    path('manage/proposals/<int:proposal_id>/detail/', proposal_detail, name='proposal_detail'),
    path('manage/proposals/<int:proposal_id>/confirm/', views.confirm_proposal, name='confirm_proposal'),
    path('proposal-success/<int:proposal_id>/', views.ProposalSuccessView.as_view(), name='proposal_success'),
    path('proposal/<str:token>/confirm-token/', views.confirm_proposal_by_token, name='confirm_proposal_by_token'),
    
    # Pricing (AJAX) — already good
    path('calculate_pricing/<str:tour_type>/<int:tour_id>/', render_pricing, name='render_pricing'),
]