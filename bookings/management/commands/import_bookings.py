import json
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from bookings.models import Booking
from tours.models import FullTour, LandTour, DayTour
from django.utils import translation
from django.utils.dateparse import parse_date
from decimal import Decimal

class Command(BaseCommand):
    help = 'Import bookings from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to JSON file')

    def handle(self, *args, **kwargs):
        json_file = kwargs['json_file']
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                bookings_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File {json_file} not found"))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("Invalid JSON format"))
            return

        model_map = {
            'full': FullTour,
            'land': LandTour,
            'day': DayTour,
        }

        for data in bookings_data:
            try:
                tour_type = data.get('tour_type')
                tour_id = data.get('tour_id')
                model = model_map.get(tour_type)
                if not model:
                    self.stdout.write(self.style.WARNING(f"Invalid tour_type: {tour_type}"))
                    continue

                try:
                    tour = model.objects.get(pk=tour_id)
                except model.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Tour {tour_type}:{tour_id} does not exist"))
                    continue

                booking = Booking(
                    customer_email=data.get('customer_email'),
                    customer_phone=data.get('customer_phone', ''),
                    number_of_adults=data.get('number_of_adults', 1),
                    number_of_children=data.get('number_of_children', 0),
                    travel_date=parse_date(data.get('travel_date')),
                    payment_method=data.get('payment_method', ''),
                    status=data.get('status', 'PENDING'),
                    content_type=ContentType.objects.get_for_model(model),
                    object_id=tour_id,
                )

                # Set translated fields
                translation.activate('en')
                booking.set_current_language('en')
                booking.customer_name = data.get('customer_name')
                booking.customer_address = data.get('customer_address', '')
                booking.nationality = data.get('nationality', '')
                booking.notes = data.get('notes', '')

                booking.save()
                self.stdout.write(self.style.SUCCESS(f"Imported booking for {booking.customer_name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error importing booking: {str(e)}"))
