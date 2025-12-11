# bookings/utils/emails.py
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_accommodation_booking_email(booking, paypal_url=None):
    """
    Sends confirmation email to the CLIENT
    """
    context = {
        'booking': booking,
        'accommodation': booking.accommodation,
        'nights': booking.get_nights(),
        'paypal_url': paypal_url,
        'site_name': settings.SITE_NAME or "Milano Travel",
    }

    subject = f"Booking Confirmation: {booking.accommodation.name} ({booking.check_in} → {booking.check_out})"

    html_message = render_to_string('bookings/emails/accommodation_booking_confirmation.html', context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.customer_email],
        html_message=html_message,
        fail_silently=False,
    )


def send_supplier_booking_notification(booking):
    """
    Sends notification to SUPPLIER (only after payment)
    """
    if not booking.accommodation.supplier_email or booking.accommodation.is_company_accom:
        return  # No supplier or it's our own → skip

    context = {
        'booking': booking,
        'accommodation': booking.accommodation,
        'nights': booking.get_nights(),
        'site_name': settings.SITE_NAME or "Milano Travel",
    }

    subject = f"New Paid Booking: {booking.accommodation.name} • {booking.customer_name}"

    html_message = render_to_string('bookings/emails/supplier_booking_notification.html', context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.accommodation.supplier_email],
        html_message=html_message,
        fail_silently=False,
    )