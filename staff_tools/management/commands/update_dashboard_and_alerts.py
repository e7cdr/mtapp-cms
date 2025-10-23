from django.core.management.base import BaseCommand
from staff_tools.models import DashboardData, AutomatedAlert, TourAvailability, StaffTask, Booking
from tours.models import FullTour, LandTour, DayTour
from datetime import date, timedelta
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Updates dashboard data and checks for automated alerts'

    def handle(self, *args, **kwargs):
        today = date.today()

        # Update Dashboard Data
        DashboardData.objects.update_or_create(
            metric="Total Bookings This Month",
            defaults={'value': str(Booking.objects.filter(booking_date__month=today.month).count())}
        )
        DashboardData.objects.update_or_create(
            metric="Pending Tasks",
            defaults={'value': str(StaffTask.objects.filter(status='OPEN').count())}
        )
        DashboardData.objects.update_or_create(
            metric="Confirmed Revenue This Month",
            defaults={'value': str(sum(b.total_price or 0 for b in Booking.objects.filter(
                status='CONFIRMED', booking_date__month=today.month)))}
        )
        self.stdout.write(self.style.SUCCESS("Dashboard data updated"))

        # Check for Alerts
        # Low Availability
        for avail in TourAvailability.objects.filter(current_slots__lt=5):
            AutomatedAlert.objects.get_or_create(
                alert_type='LOW_AVAILABILITY',
                message=f"Low availability for {avail.tour}: {avail.current_slots} slots remaining",
                related_object_type=ContentType.objects.get_for_model(avail.tour),
                related_object_id=avail.tour.pk,
                defaults={'triggered_date': today}
            )

        # Overdue Tasks
        for task in StaffTask.objects.filter(due_date__lt=today, status__in=['OPEN', 'IN_PROGRESS']):
            AutomatedAlert.objects.get_or_create(
                alert_type='OVERDUE_TASK',
                message=f"Task '{task.title}' assigned to {task.assigned_to} is overdue",
                related_object_type=ContentType.objects.get_for_model(StaffTask),
                related_object_id=task.pk,
                defaults={'triggered_date': today}
            )

        # Booking Issues (e.g., pending too long)
        for booking in Booking.objects.filter(status='PENDING', booking_date__lt=today - timedelta(days=3)):
            AutomatedAlert.objects.get_or_create(
                alert_type='BOOKING_ISSUE',
                message=f"Booking {booking.pk} for {booking.customer_name} pending over 3 days",
                related_object_type=ContentType.objects.get_for_model(Booking),
                related_object_id=booking.pk,
                defaults={'triggered_date': today}
            )

        self.stdout.write(self.style.SUCCESS("Alerts checked and updated"))