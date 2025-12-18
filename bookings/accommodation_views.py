from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .utils.pricing import calculate_accommodation_price
from .AccommodationBookingForm import AccommodationBookingForm
from bookings.models import AccommodationBooking  # ← we’ll create this next
from bookings.utils.emails import send_accommodation_booking_email
from django.contrib.contenttypes.models import ContentType
from wagtail.models import Page


@require_http_methods(["GET", "POST"])
@csrf_exempt  # We'll use our own CSRF protection via AJAX header
def accommodation_booking_modal(request, accommodation_id):
    page = get_object_or_404(Page.objects.live(), id=accommodation_id)
    accommodation = page.specific

    if request.method == "GET":
        form = AccommodationBookingForm(accommodation=accommodation)
        return render(request, "accommodation/includes/booking_modal.html", {
            "form": form,
            "accommodation": accommodation,
            "page": accommodation,  # for blocked_dates_list, etc.
        })

    if request.method == "POST":
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({"error": "AJAX required"}, status=400)

        form = AccommodationBookingForm(request.POST, accommodation=accommodation)

        if form.is_valid():
            booking = AccommodationBooking.objects.create(
                content_type=ContentType.objects.get_for_model(accommodation),
                object_id=accommodation.id,
                check_in=form.cleaned_data['check_in'],
                check_out=form.cleaned_data['check_out'],
                adults=form.cleaned_data['adults'],
                children=form.cleaned_data['children'],
                child_ages=form.cleaned_data.get('child_ages', []),
                customer_name=form.cleaned_data['name'],
                customer_email=form.cleaned_data['email'],
                customer_phone=form.cleaned_data.get('phone', ''),
                notes=form.cleaned_data.get('notes', ''),
                total_price=calculate_accommodation_price(accommodation, form.cleaned_data),
                status='PENDING_PAYMENT',
                created_at=timezone.now(),
            )

            paypal_url = request.build_absolute_uri(
                reverse('p_methods:paypal_accommodation_checkout', kwargs={'booking_id': booking.id})
            )

            send_accommodation_booking_email(booking, paypal_url)

            return JsonResponse({
                "success": True,
                "message": "Booking created! Redirecting to payment...",
                "redirect_url": paypal_url,
            })

        return JsonResponse({
            "success": False,
            "errors": form.errors,
        }, status=400)
    
@require_http_methods(["GET"])
def accommodation_price_preview(request, accommodation_id):
    page = get_object_or_404(Page.objects.live(), id=accommodation_id)
    accommodation = page.specific

    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')
    adults = int(request.GET.get('adults', 1))
    children = int(request.GET.get('children', 0))
    child_ages_str = request.GET.get('child_ages', '[]')

    if not check_in or not check_out:
        return JsonResponse({'total': 0})

    from datetime import datetime
    import json
    try:
        child_ages = json.loads(child_ages_str)
    except json.JSONDecodeError:
        child_ages = []
    
    data = {
        'check_in': datetime.strptime(check_in, '%Y-%m-%d').date(),
        'check_out': datetime.strptime(check_out, '%Y-%m-%d').date(),
        'adults': adults,
        'children': children,
        'child_ages': child_ages,
    }

    total = calculate_accommodation_price(accommodation, data)
    return JsonResponse({'total': float(total)})
    