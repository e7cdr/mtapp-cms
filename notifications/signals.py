from django.db.models.signals import post_save
from django.dispatch import receiver
from bookings.models import Proposal, Booking, AccommodationBooking
from django.contrib.auth.models import User
from notifications.models import Notification
from django.core.cache import cache


@receiver(post_save, sender=Proposal)
def notify_proposal_created(sender, instance, created, **kwargs):
    if created:
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                message=f"New Proposal #{instance.prop_id}: {instance.customer_name} - {instance.tour} issued by {instance.user.username if instance.user else 'MTWEB'}"
            )
        cache.clear()

@receiver(post_save, sender=Booking)
def notify_booking_created(sender, instance, created, **kwargs):
    if created:
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                message=f"New Booking #{instance.book_id}: {instance.customer_name} - {instance.tour} created for {instance.user.username if instance.user else 'MTWEB'}"
            )
        cache.clear()

@receiver(post_save, sender=AccommodationBooking)
def notify_accommodation_booking_created(sender, instance, created, **kwargs):
    if created:
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                message=f"New Accommodation #{instance.object_id}: {instance.customer_name} - {instance.accommodation} issued by {instance.user.username if instance.user else 'MTWEB'}"
            )
        cache.clear()
