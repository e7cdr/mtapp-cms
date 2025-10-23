import json
from django.core.management.base import BaseCommand
from tours.models import FullTour, LandTour, DayTour
from django.utils.dateparse import parse_date
from django.db import transaction

class Command(BaseCommand):
    help = 'Imports tour data from a JSON file into the database'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file')

    def handle(self, *args, **options):
        json_file = options['json_file']
        try:
            with open(json_file, 'r', encoding='utf-8') as file:
                data = json.load(file)

            with transaction.atomic():
                self.import_full_tours(data.get('full_tours', []))
                self.import_land_tours(data.get('land_tours', []))
                self.import_day_tours(data.get('day_tours', []))

            self.stdout.write(self.style.SUCCESS('Successfully imported tours'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File {json_file} not found'))
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR('Invalid JSON format'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'General error: {str(e)}'))

    def import_full_tours(self, full_tours):
        for tour in full_tours:
            try:
                if not isinstance(tour.get('nights'), int) or tour.get('nights', 0) <= 0:
                    raise ValueError(f"Invalid 'nights' value for FullTour {tour.get('ref_code')}: {tour.get('nights')}")
                
                full_tour = FullTour(
                    ref_code=tour['ref_code'],
                    duration_days=tour['duration_days'],
                    nights=tour['nights'],
                    start_date=parse_date(tour['start_date']),
                    end_date=parse_date(tour['end_date']),
                    is_all_inclusive=tour['is_all_inclusive'],
                    price_sgl_regular=tour['price_sgl_regular'],
                    price_dbl_regular=tour['price_dbl_regular'],
                    price_tpl_regular=tour['price_tpl_regular'],
                    price_chd_regular=tour['price_chd_regular'],
                    max_capacity=tour['max_capacity'],
                    available_slots=tour['available_slots'],
                )
                full_tour.save()
                # Set translations
                full_tour.set_current_language('en')
                full_tour.title = tour['translations']['title']
                full_tour.destination = tour['translations']['destination']
                full_tour.description = tour['translations']['description']
                full_tour.travel_period_note = tour['translations']['travel_period_note']
                full_tour.courtesies = tour['translations']['courtesies']
                full_tour.additional_notes = tour['translations']['additional_notes']
                full_tour.optional_activities = tour['translations']['optional_activities']
                full_tour.flight_details = tour['translations']['flight_details']
                full_tour.hotel = tour['translations']['hotel']
                full_tour.save()
            except KeyError as e:
                self.stderr.write(self.style.ERROR(f"Missing field {e} in FullTour {tour.get('ref_code')}"))
                raise
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error importing FullTour {tour.get('ref_code')}: {str(e)}"))
                raise

    def import_land_tours(self, land_tours):
        for tour in land_tours:
            try:
                if not isinstance(tour.get('nights'), int) or tour.get('nights', 0) <= 0:
                    raise ValueError(f"Invalid 'nights' value for LandTour {tour.get('ref_code')}: {tour.get('nights')}")
                
                land_tour = LandTour(
                    ref_code=tour['ref_code'],
                    duration_days=tour['duration_days'],
                    nights=tour['nights'],
                    start_date=parse_date(tour['start_date']),
                    end_date=parse_date(tour['end_date']),
                    price_sgl=tour['price_sgl'],
                    price_dbl=tour['price_dbl'],
                    price_tpl=tour['price_tpl'],
                    price_chd=tour['price_chd'],
                    max_capacity=tour['max_capacity'],
                    available_slots=tour['available_slots'],
                )
                land_tour.save()
                # Set translations
                land_tour.set_current_language('en')
                land_tour.title = tour['translations']['title']
                land_tour.destination = tour['translations']['destination']
                land_tour.description = tour['translations']['description']
                land_tour.courtesies = tour['translations']['courtesies']
                land_tour.additional_notes = tour['translations']['additional_notes']
                land_tour.hotel = tour['translations']['hotel']
                land_tour.save()
            except KeyError as e:
                self.stderr.write(self.style.ERROR(f"Missing field {e} in LandTour {tour.get('ref_code')}"))
                raise
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error importing LandTour {tour.get('ref_code')}: {str(e)}"))
                raise

    def import_day_tours(self, day_tours):
        for tour in day_tours:
            try:
                day_tour = DayTour(
                    ref_code=tour['ref_code'],
                    date=parse_date(tour['date']),
                    duration_hours=tour['duration_hours'],
                    price_adult=tour['price_adult'],
                    price_child=tour['price_child'],
                    max_capacity=tour['max_capacity'],
                    available_slots=tour['available_slots'],
                )
                day_tour.save()
                # Set translations
                day_tour.set_current_language('en')
                day_tour.title = tour['translations']['title']
                day_tour.destination = tour['translations']['destination']
                day_tour.description = tour['translations']['description']
                day_tour.courtesies = tour['translations']['courtesies']
                day_tour.additional_notes = tour['translations']['additional_notes']
                day_tour.save()
            except KeyError as e:
                self.stderr.write(self.style.ERROR(f"Missing field {e} in DayTour {tour.get('ref_code')}"))
                raise
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error importing DayTour {tour.get('ref_code')}: {str(e)}"))
                raise