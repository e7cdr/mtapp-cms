from django.urls import path

# from api.views import DynamicPricingView #TODO
from . import views
from django.urls import path, include

app_name = 'tours'

urlpatterns = [
    # path('', views.tours_list, name='tours_list'),
    # path('set_currency/', views.set_currency, name='set_currency'),
    # path('<str:tour_type_val>/<int:tour_id>/', views.tour_detail, name='tour_detail'),
    # path('debug-session/', views.debug_session, name='debug_session'),
    # path('clear-language-session/', views.clear_language_session, name='clear_language_session'),
    # path('<str:tour_type_val>/<int:tour_id>/pdf/', views.download_itinerary_pdf, name='download_itinerary_pdf'),
    # path('<str:tour_type_val>/<int:tour_id>/preview/', views.preview_itinerary_pdf, name='preview_itinerary_pdf'),
    # # path('available-dates/', views.available_dates, name='available_dates'),
    # path('calculate_pricing/<str:tour_type>/<int:tour_id>/', DynamicPricingView.as_view(), name='calculate_pricing')
    ]

