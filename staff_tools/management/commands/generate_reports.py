from django.core.management.base import BaseCommand
from staff_tools.models import Report, Booking
from tours.models import FullTour, LandTour, DayTour
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Generates reports for bookings, revenue, and availability'

    def handle(self, *args, **kwargs):
        today = date.today()
        last_week = today - timedelta(days=7)

        # Bookings Summary
        bookings_report, _ = Report.objects.get_or_create(
            title="Weekly Bookings Summary",
            report_type="BOOKINGS",
            start_date=last_week,
            end_date=today,
            created_by="System",
            defaults={'data': {}}
        )
        bookings_report.generate_report_data()
        self.stdout.write(self.style.SUCCESS(f"Generated {bookings_report}"))

        # Revenue Report
        revenue_report, _ = Report.objects.get_or_create(
            title="Weekly Revenue Report",
            report_type="REVENUE",
            start_date=last_week,
            end_date=today,
            created_by="System",
            defaults={'data': {}}
        )
        revenue_report.generate_report_data()
        self.stdout.write(self.style.SUCCESS(f"Generated {revenue_report}"))

        # Availability Report
        availability_report, _ = Report.objects.get_or_create(
            title="Weekly Availability Report",
            report_type="AVAILABILITY",
            start_date=last_week,
            end_date=today,
            created_by="System",
            defaults={'data': {}}
        )
        availability_report.generate_report_data()
        self.stdout.write(self.style.SUCCESS(f"Generated {availability_report}"))