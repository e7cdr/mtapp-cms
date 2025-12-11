from datetime import date
from wagtail.api.v2.views import BaseAPIViewSet


from . import models
from tours.models import LandTourPage
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from .tours_utils import calculate_demand_factor, get_remaining_capacity


class AvailableDatesView(APIView):
    def get(self, request):
        tour_type = request.GET.get('tour_type')
        tour_id = request.GET.get('tour_id')
        travel_date_str = request.GET.get('travel_date')
        if not tour_type or not tour_id:
            return Response({'error': 'Missing tour_type or tour_id'}, status=400)
        
        tour_type_map = {
            'full': "FullTourPage",
            'land': LandTourPage,
            'day': "DayTourPage",
        }
        tour_model = tour_type_map.get(tour_type.lower())
        if not tour_model:
            return Response({'error': 'Invalid tour_type'}, status=400)
        
        tour = get_object_or_404(tour_model, id=tour_id)
        
        if travel_date_str:
            try:
                travel_date = date.fromisoformat(travel_date_str)
            except ValueError:
                return Response({'error': 'Invalid date format'}, status=400)
            
            duration_days = getattr(tour, 'duration_days', 1)
            capacity = get_remaining_capacity(tour_id, travel_date, tour_model, duration_days)
            return Response({
                'remaining_capacity': capacity['trip_remaining'],  # FIXED: Trip min
                'per_day': capacity['per_day'],
                'is_full': capacity['is_full'],
                'demand_factor': calculate_demand_factor(capacity['trip_remaining'], sum(d['total_daily'] for d in capacity['per_day'])),
            })
        
        # Full available dates (stubbed)
        available_dates = []
        return Response({'available_dates': available_dates})  

class ProposalsAPIView(BaseAPIViewSet):
    model = models.Proposal
    permission_classes = (IsAuthenticated,)


class BookingsAPIView(BaseAPIViewSet):
    model = models.Booking
    permission_classes = (IsAuthenticated,)


    