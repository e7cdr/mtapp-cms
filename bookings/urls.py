# bookings/urls.py
from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

app_name = 'bookings'
urlpatterns = [
    path('', views.get_bookings, name='get_bookings'),
    path('child_ages/', views.child_ages, name='child_ages'),
    path('partners/', views.get_partners, name='get_partners'),
    path('customer-portal/', views.customer_portal, name='customer_portal'),
    path('manage/bookings/', views.manage_bookings, name='manage_bookings'),
    path('book_tour/<str:tour_type>/<int:tour_id>/', views.book_tour, name='book_tour'),
    path('payment/cancel/<int:proposal_id>/', views.payment_cancel, name='payment_cancel'),
    path('payment/success/<int:proposal_id>/', views.payment_success, name='payment_success'),
    path('proposal/<int:proposal_id>/reject/', views.reject_proposal, name='reject_proposal'),
    path('proposal_status/<int:proposal_id>/', views.proposal_status, name='proposal_status'),
    path('proposal/<int:proposal_id>/confirm/', views.confirm_proposal, name='confirm_proposal'),
    path('manage/proposals/', views.manage_proposals, name='manage_proposals'),
    path('calculate_pricing/<str:tour_type>/<int:tour_id>/', views.render_pricing, name='render_pricing'),
    path('<str:tour_type>/<int:tour_id>/revert/', views.revert_to_booking_form, name='revert_to_booking_form'),
    path('proposal/<str:token>/confirm-token/', views.confirm_proposal_by_token, name='confirm_proposal_by_token'),
    path('confirm/<str:tour_type>/<int:tour_id>/', views.confirm_proposal_submission, name='confirm_proposal_submission'),


]

