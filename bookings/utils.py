from datetime import date, timedelta
from decimal import Decimal
from venv import logger

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.mail import send_mail
from django.contrib.contenttypes.models import ContentType


from bookings.models import Booking, Proposal, ProposalConfirmationToken

from django.template.loader import render_to_string
from django.contrib import messages
from django.core.paginator import Paginator

from django.db.models import Sum

from .pdf_gen import generate_itinerary_pdf

def send_supplier_email(proposal: Proposal, token: ProposalConfirmationToken = None, tour=None, end_date=None) -> bool:
    try:
        if not proposal.supplier_email:
            logger.error(f"Supplier email missing for proposal {proposal.id}")
            raise ValueError("Supplier email is required.")
        
        subject = f"New Tour Proposal - {proposal.prop_id} - {tour or 'Unknown Tour'}"

        context = {
            'proposal': proposal,
            'end_date': end_date or (proposal.travel_date + timedelta(days=(tour.duration_days if tour else 0))),
            'tour': tour or 'Unknown Tour',  # Fallback
            'site_url': settings.SITE_URL,
            'configuration_details': proposal.room_config if proposal.room_config else [],
        }
        if token:
            context['confirm_url'] = f"{settings.SITE_URL}{reverse('bookings:confirm_proposal_by_token', args=[token.token])}"
        
        message = render_to_string('bookings/emails/supplier_proposal.html', context)
        send_mail(
            subject,
            '',  # No plain text (HTML only, Django auto-generates basic plain)
            settings.DEFAULT_FROM_EMAIL,
            [proposal.supplier_email],
            html_message=message,
            fail_silently=False,
        )
        logger.info(f"Supplier email sent to {proposal.supplier_email} for proposal {proposal.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send supplier email for proposal {proposal.id}: {e}")
        return False
    
def send_preconfirmation_email(proposal: Proposal) -> None:
    subject = "Confirm Your Tour Proposal"
    duration = proposal.tour.duration_days if proposal.tour else 0
    end_date = proposal.travel_date + timedelta(days=duration)
    
    # NEW: Extract pricing details for context
    tour = proposal.tour
    pricing_type = getattr(tour, 'pricing_type', 'Per_room') if tour else 'Per_room'
    price_adult = getattr(tour, 'price_adult', 0) if tour else 0
    price_child = getattr(tour, 'price_child', 0) if tour else 0
    price_infant = getattr(tour, 'price_inf', 0) if tour else 0  # Adjust field names if different
    
    # Subtotals
    adult_subtotal = proposal.number_of_adults * price_adult
    child_subtotal = proposal.number_of_children * price_child
    infant_subtotal = proposal.number_of_infants * price_infant
    per_person_details = {
        'adult_subtotal': adult_subtotal,
        'child_subtotal': child_subtotal,
        'infant_subtotal': infant_subtotal,
        'total_breakdown': adult_subtotal + child_subtotal + infant_subtotal,
    }
    
    message = render_to_string('bookings/emails/preconfirmation.html', {
        'proposal': proposal,
        'tour': tour,
        'end_date': end_date,
        'payment_link': proposal.payment_link,
        'site_url': settings.SITE_URL,
        'configuration_details': proposal.room_config if proposal.room_config else [],
        'pricing_type': pricing_type,
        'per_person_details': per_person_details,
        'price_adult': price_adult,
        'price_child': price_child,
        'price_infant': price_infant,
    })
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [proposal.customer_email],
        html_message=message,
    )
    logger.info(f"Preconfirmation email sent to {proposal.customer_email} for proposal {proposal.id}")

def send_itinerary_email(booking: Booking, pdf_data: bytes) -> None:
    subject = "Your Tour Itinerary"
    duration = booking.tour.duration_days
    end_date = booking.travel_date + timedelta(days=duration)

    message = render_to_string('bookings/emails/itinerary_email.html', {
        'booking': booking,
        'tour': booking.tour,
        'end_date': end_date,
        'site_url': settings.SITE_URL,
        'configuration_details': booking.configuration_details or {},
    })
    from django.core.mail import EmailMessage
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.customer_email],
    )
    email.attach('itinerary.pdf', pdf_data, 'application/pdf')
    email.content_subtype = 'html'
    email.send()
    logger.info(f"Itinerary email sent to {booking.customer_email} for booking {booking.id}")

def send_proposal_submitted_email(proposal: Proposal, tour=None, end_date=None) -> bool:
    try:
        if not proposal.customer_email:
            logger.error(f"Customer email missing for proposal {proposal.id}")
            raise ValueError("Customer email is required.")
        
        subject = f"Your Tour Proposal Submitted - ID: {proposal.prop_id or 'N/A'}"
        duration = getattr(tour, 'duration_days', 0) if tour else 0
        end_date = end_date or (proposal.travel_date + timedelta(days=duration))
        
        context = {
            'proposal': proposal,
            'tour': tour or 'Unknown Tour',
            'end_date': end_date,
            'site_url': settings.SITE_URL,
            'configuration_details': proposal.room_config if proposal.room_config else [],
            'proposal_url': f"{settings.SITE_URL}{reverse('bookings:proposal_success', args=[proposal.id])}",
            'is_company_tour': getattr(tour, 'is_company_tour', False),  # NEW: Explicit for template
        }
        
        # Render with error logging
        try:
            message = render_to_string('bookings/emails/proposal_submitted.html', context)
        except Exception as render_e:
            logger.error(f"Template render failed for proposal_submitted.html (proposal {proposal.id}): {render_e}")
            raise
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [proposal.customer_email],
            html_message=message,
            fail_silently=False,
        )
        logger.info(f"Proposal submitted email sent to {proposal.customer_email} for proposal {proposal.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send proposal submitted email for {proposal.id}: {e}")
        return False
    
def send_internal_confirmation_email(proposal: Proposal, tour=None, end_date=None) -> bool:
    """
    Notifies internal staff of new company tour proposal for review in portal.
    """
    try:
        # Internal recipients (hardcode or from settings)
        internal_emails = [settings.DEFAULT_FROM_EMAIL, 'staff@milanotravel.com.ec']  # Add more as needed
        
        subject = f"Internal Review Needed: Company Tour Proposal {proposal.prop_id} - {tour or 'Unknown Tour'}"
        
        context = {
            'proposal': proposal,
            'end_date': end_date,
            'tour': tour or 'Unknown Tour',
            'site_url': settings.SITE_URL,
            'portal_url': f"{settings.SITE_URL}/bookings/manage/proposals/",  # Link to confirm
            'configuration_details': proposal.room_config if proposal.room_config else [],
        }
        
        message = render_to_string('bookings/emails/internal_proposal.html', context)
        send_mail(
            subject,
            '',  # HTML-only
            settings.DEFAULT_FROM_EMAIL,
            internal_emails,
            html_message=message,
            fail_silently=False,
        )
        logger.info(f"Internal email sent for company proposal {proposal.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send internal email for proposal {proposal.id}: {e}")
        return False

def manage_proposals(request) -> HttpResponse:
    # Base queryset with safe eager-loading (no 'translations'; GenericFK via content_type)
    queryset = Proposal.objects.select_related('content_type', 'user').prefetch_related('confirmation_tokens')
    
    # Status filter (from GET; default to pending for usability)
    status = request.GET.get('status')
    if status and status != 'all':
        if status in ['PENDING_SUPPLIER', 'PENDING_INTERNAL']:
            queryset = queryset.filter(status=status)
        else:
            queryset = queryset.filter(status=status)  # Other statuses like PAID

    # Month/Year Filter
    month = request.GET.get('month')
    year = request.GET.get('year')
    if month and year:
        queryset = queryset.filter(created_at__year=year, created_at__month=month)  # Or travel_date__year/month
    elif month:
        queryset = queryset.filter(created_at__month=month)
    elif year:
        queryset = queryset.filter(created_at__year=year)
    
    # Pagination (after filter)
    paginator = Paginator(queryset, 10)  # 10 per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Always render full template (includes partial for list)
    return render(request, 'bookings/manage_proposals.html', {
        'proposals': page_obj,  # Pass page_obj (has .object_list, pagination attrs)
        'current_status': status or 'all',  # For template highlighting active button
    })

def reject_proposal(request, proposal_id: int) -> HttpResponse:
    try:
        proposal = Proposal.objects.get(id=proposal_id)
        proposal.status = 'REJECTED'
        proposal.save()
        messages.success(request, "Proposal rejected.")
    except Proposal.DoesNotExist:
        messages.error(request, "Proposal not found.")
    return redirect('bookings:manage_proposals')

# @login_required  # Uncomment for login enforcement
# @user_passes_test(lambda u: u.is_staff)  # Or staff-only
def proposal_detail(request, proposal_id: int) -> HttpResponse:
    proposal = get_object_or_404(
        Proposal.objects.select_related('content_type', 'user').prefetch_related('confirmation_tokens'),
        id=proposal_id
    )
    
    if not proposal.tour:
        raise Http404("Tour not found for this proposal.")
    
    tour = proposal.tour
    # Calculate end_date
    duration = getattr(tour, 'duration_days', 0)
    end_date = proposal.travel_date + timedelta(days=duration)
    
    # Effective children/infants from ages (mirror compute_pricing)
    child_age_min = getattr(tour, 'child_age_min', 0)  # Assume 2 or model default
    effective_children_ages = [age for age in proposal.children_ages if age >= child_age_min]
    effective_infants_ages = [age for age in proposal.children_ages if age < child_age_min]
    effective_children = len(effective_children_ages)
    effective_infants = len(effective_infants_ages)
    
    # Extract pricing details (mirror compute_pricing logic)
    pricing_type = getattr(tour, 'pricing_type', 'Per_room')
    
    # Base prices (universal)
    price_adult = Decimal(str(getattr(tour, 'price_adult', '0')))
    price_child = Decimal(str(getattr(tour, 'price_child', getattr(tour, 'price_chd', '0'))))
    price_infant = Decimal(str(getattr(tour, 'price_inf', '0')))
    
    # Room prices (if Per_room)
    price_sgl = Decimal(str(getattr(tour, 'price_sgl', '0')))
    price_dbl = Decimal(str(getattr(tour, 'price_dbl', '0')))
    price_tpl = Decimal(str(getattr(tour, 'price_tpl', '0')))
    
    # Factors (from compute_pricing)
    seasonal_factor = Decimal(str(getattr(tour, 'seasonal_factor', '1.0')))
    model_demand_factor = Decimal(str(getattr(tour, 'demand_factor', '0')))
    full_percent = Decimal('1.0')  # FIXED: For breakdowns, use full (or compute if needed)
    demand_factor = model_demand_factor * full_percent
    price_adjustment = Decimal('1') + demand_factor
    exchange_rate = Decimal('1.0')
    factor = seasonal_factor * price_adjustment * exchange_rate
    
    # Adjusted rates (for "Qty x Rate")
    adjusted_price_adult = price_adult * factor
    adjusted_price_child = price_child * factor
    adjusted_price_infant = price_infant * factor
    adjusted_price_sgl = price_sgl * factor
    adjusted_price_dbl = price_dbl * factor
    adjusted_price_tpl = price_tpl * factor
    
    # Subtotals (qty * adjusted_rate—use effective for children/infants)
    adult_subtotal = proposal.number_of_adults * adjusted_price_adult
    child_subtotal = effective_children * adjusted_price_child
    infant_subtotal = effective_infants * adjusted_price_infant
    per_person_details = {
        'adult_subtotal': adult_subtotal,
        'child_subtotal': child_subtotal,
        'infant_subtotal': infant_subtotal,
        'total_breakdown': adult_subtotal + child_subtotal + infant_subtotal,
    }
    
    # Per_room subtotals (if config—apply factor if base)
    room_subtotals = {}
    if pricing_type == 'Per_room' and proposal.selected_config:
        config = proposal.selected_config
        room_subtotals = {
            'singles_subtotal': config.get('singles', 0) * adjusted_price_sgl,
            'doubles_subtotal': config.get('doubles', 0) * adjusted_price_dbl,
            'triples_subtotal': config.get('triples', 0) * adjusted_price_tpl,
            'children_subtotal': effective_children * adjusted_price_child,
            'infants_subtotal': effective_infants * adjusted_price_infant,
            'total_breakdown': sum([config.get('singles', 0) * adjusted_price_sgl, config.get('doubles', 0) * adjusted_price_dbl, config.get('triples', 0) * adjusted_price_tpl, effective_children * adjusted_price_child, effective_infants * adjusted_price_infant]),
        }
    
    context = {
        'proposal': proposal,
        'tour': tour,
        'end_date': end_date,
        'configuration_details': proposal.room_config if proposal.room_config else {},
        'is_company_tour': getattr(tour, 'is_company_tour', False),
        'site_url': settings.SITE_URL,
        'pricing_type': pricing_type,
        'per_person_details': per_person_details,
        'room_subtotals': room_subtotals,
        'adjusted_price_adult': adjusted_price_adult,
        'adjusted_price_child': adjusted_price_child,
        'adjusted_price_infant': adjusted_price_infant,
        'adjusted_price_sgl': adjusted_price_sgl,
        'adjusted_price_dbl': adjusted_price_dbl,
        'adjusted_price_tpl': adjusted_price_tpl,
        'factor': factor,
        'effective_children': effective_children,  # NEW: For template
        'effective_infants': effective_infants,
    }
    
    return render(request, 'bookings/proposal_detail.html', context)

def payment_success(request, proposal_id: int) -> HttpResponse:
    try:
        proposal = Proposal.objects.get(id=proposal_id)
        if proposal.status != 'SUPPLIER_CONFIRMED':
            logger.error(f"Invalid proposal status for payment: {proposal.status}, id={proposal_id}")
            messages.error(request, "Invalid proposal status.")
            return redirect('bookings:manage_proposals')

        # Check if a Booking already exists for this proposal
        existing_booking = Booking.objects.filter(proposal=proposal).first()
        if existing_booking:
            logger.info(f"Booking already exists for proposal {proposal_id}: booking_id={existing_booking.id}")
            messages.info(request, "Booking already confirmed. Itinerary has been sent.")
            try:
                itinerary_pdf = generate_itinerary_pdf(existing_booking)
                send_itinerary_email(existing_booking, itinerary_pdf)
            except Exception as e:
                logger.error(f"Failed to resend itinerary for booking {existing_booking.id}: {e}")
                messages.warning(request, "Booking confirmed, but itinerary resending failed. Contact support.")
            return render(request, 'bookings/payment_success.html', {'booking': existing_booking})

        # Create new Booking with correct GenericFK
        booking = Booking.objects.create(
            customer_name=proposal.customer_name,
            customer_email=proposal.customer_email,
            customer_phone=proposal.customer_phone,
            customer_address=proposal.customer_address,
            nationality=proposal.nationality,
            notes=proposal.notes,
            content_type=proposal.content_type,
            object_id=proposal.object_id,
            number_of_adults=proposal.number_of_adults,
            number_of_children=proposal.number_of_children,
            children_ages=proposal.children_ages,
            travel_date=proposal.travel_date,
            total_price=proposal.estimated_price,
            payment_status='PAID',
            status='CONFIRMED',  # FIXED: Matches model choices (post-payment confirmed)
            payment_method='PAYPAL',
            proposal=proposal,
            configuration_details=proposal.room_config if proposal.room_config else {},
            currency=proposal.currency,
            user=proposal.user,
        )
        
        # Update proposal to 'PAID' after Booking
        proposal.status = 'PAID'
        proposal.save()
        
        # FIXED: Log for capacity test
        logger.info(f"Booking created from proposal {proposal_id}: booking_id={booking.id}, travel_date={booking.travel_date}, status={booking.status}, content_type_id={booking.content_type_id}, object_id={booking.object_id}")
        
        try:
            itinerary_pdf = generate_itinerary_pdf(booking)
            send_itinerary_email(booking, itinerary_pdf)
            messages.success(request, "Payment successful! Your itinerary has been sent.")
        except Exception as e:
            logger.error(f"Failed to generate/send itinerary for booking {booking.id}: {e}")
            messages.warning(request, "Payment successful, but itinerary generation failed. Contact support.")
        
        context = {
            'booking': booking,
            'tour': booking.tour,
            'site_url': settings.SITE_URL,
            'messages': messages.get_messages(request),
        }
        return render(request, 'bookings/payment_success.html', context)
    except Proposal.DoesNotExist:
        logger.error(f"Proposal not found: id={proposal_id}")
        messages.error(request, "Proposal not found.")
        return redirect('bookings:manage_proposals')

def payment_cancel(request, proposal_id: int) -> HttpResponse:
    try:
        proposal = Proposal.objects.get(id=proposal_id)
        if proposal.status != 'SUPPLIER_CONFIRMED':
            messages.error(request, "Proposal not pending payment.")
            return redirect('home')
        
        proposal.status = 'REJECTED'
        proposal.save()
        logger.info(f"Payment cancelled for proposal {proposal_id}")
        messages.error(request, "Payment cancelled. Please contact us to retry.")
    except Proposal.DoesNotExist:
        logger.error(f"Proposal not found: id={proposal_id}")
        messages.error(request, "Proposal not found.")
    return redirect('/')

def get_30_day_used_slots(tour_id, tour_model):
    """
    Sum confirmed bookings over next 30 days from today, only on available days.
    Returns: {'used_slots': int, 'total_slots': int, 'full_percent': Decimal (0-1)}
    """
    today = date.today()
    end_date = today + timedelta(days=30)
    
    # Fetch tour for max_capacity/available_days
    tour = get_object_or_404(tour_model, id=tour_id)
    daily_capacity = tour.max_capacity or 0
    available_days_str = getattr(tour, 'available_days', '')  # e.g., '0,1,2,3'
    available_days = [int(d.strip()) for d in available_days_str.split(',') if d.strip()] if available_days_str else list(range(7))  # All days if empty
    logger.debug(f"Available days for tour {tour_id}: {available_days}")
    
    total_slots = 0
    used_slots = 0
    
    current_date = today
    while current_date <= end_date:
        weekday_python = current_date.weekday()  # 0=Mon, 6=Sun
        day_of_week_model = (weekday_python + 1) % 7  # FIXED: 0=Sun, 6=Sat
        if day_of_week_model not in available_days:
            current_date += timedelta(days=1)
            continue
        
        total_slots += daily_capacity
        # Confirmed for this date
        adults_sum = Booking.objects.filter(
            content_type=ContentType.objects.get_for_model(tour_model),
            object_id=tour_id,
            travel_date=current_date,
            status='CONFIRMED',
        ).aggregate(Sum('number_of_adults'))['number_of_adults__sum'] or 0
        children_sum = Booking.objects.filter(
            content_type=ContentType.objects.get_for_model(tour_model),
            object_id=tour_id,
            travel_date=current_date,
            status='CONFIRMED',
        ).aggregate(Sum('number_of_children'))['number_of_children__sum'] or 0
        used_slots += adults_sum + children_sum
        print(f"Date {current_date}: weekday_python={weekday_python}, day_model={day_of_week_model}, adults_sum={adults_sum}, children_sum={children_sum}, used_slots so far={used_slots}")

        current_date += timedelta(days=1)
    
    if total_slots == 0:
        full_percent = Decimal('0')
    else:
        full_percent = Decimal(used_slots) / Decimal(total_slots)
    
    logger.debug(f"30-day used_slots={used_slots}, total_slots={total_slots}, full_percent={full_percent}")
    return {
        'used_slots': used_slots,
        'total_slots': total_slots,
        'full_percent': full_percent
    }