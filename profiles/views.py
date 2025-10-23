import csv
import logging
import re
from django.db import models  # Add this import for Sum
from django.forms import ValidationError
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import render
from bookings.models import Booking
from revenue_management.models import Commission
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


@login_required
def profile_dashboard(request):
    # Get month and year from query parameters (e.g., ?month=5&year=2025)
    month = request.GET.get('month', timezone.now().month)
    year = request.GET.get('year', timezone.now().year)
    try:
        month = int(month)
        year = int(year)
    except ValueError:
        month = timezone.now().month
        year = timezone.now().year

    # Calculate date range for the selected month
    first_day_of_month = datetime(year, month, 1).date()
    next_month = (first_day_of_month + timedelta(days=31)).replace(day=1)

    # Get recent bookings for the user
    bookings = Booking.objects.filter(user=request.user).select_related('content_type', 'user').order_by('-booking_date')[:5]
    
    # Calculate total bookings
    total_bookings = bookings.count()
    
    # Calculate total commission (sum of all commissions for the user)
    total_commission = Commission.objects.filter(
        user=request.user,
        status__in=['PENDING', 'PAID']
    ).aggregate(total=models.Sum('amount'))['total'] or 0.00
    
    # Calculate monthly commission
    monthly_commission = Commission.objects.filter(
        user=request.user,
        created_at__range=[first_day_of_month, next_month],
        status__in=['PENDING', 'PAID']
    ).aggregate(total=models.Sum('amount'))['total'] or 0.00
    
    # Get recent notices (placeholder; replace with your Notice model query)
    notices = []  # Example: Notice.objects.filter(user=request.user)[:5]
    
    context = {
        'total_bookings': total_bookings,
        'total_commission': total_commission,
        'monthly_commission': monthly_commission,
        'month': month,
        'year': year,
        'bookings': bookings,
        'notices': notices,
    }
    return render(request, 'profiles/profile_dashboard.html', context)

@login_required
def export_commissions(request):
    # Get date range and format from query parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    export_format = request.GET.get('format', 'csv').lower()

    # Validate dates
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    try:
        if start_date and not re.match(date_pattern, start_date):
            raise ValidationError(_("Invalid start date format. Use YYYY-MM-DD."))
        if end_date and not re.match(date_pattern, end_date):
            raise ValidationError(_("Invalid end date format. Use YYYY-MM-DD."))
        
        # Default to current month if no dates provided
        today = timezone.now().date()
        if not start_date:
            start_date = today.replace(day=1)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if not end_date:
            end_date = (today.replace(day=1) + timedelta(days=31)).replace(day=1)
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if start_date > end_date:
            raise ValidationError(_("Start date must be before end date."))
    except (ValidationError, ValueError) as e:
        logger.error(f"Invalid date parameters: {e}")
        return HttpResponse(
            _("Invalid date parameters. Please use YYYY-MM-DD format and ensure start date is before end date."),
            status=400
        )

    # Query commissions
    commissions = Commission.objects.filter(
        user=request.user,
        created_at__range=[start_date, end_date + timedelta(days=1)],  # Include end_date
        status__in=['PENDING', 'PAID']
    ).select_related('booking')

    if export_format == 'csv':
        # Generate CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="commissions_{start_date}_to_{end_date}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            _('Booking ID'),
            _('Tour Title'),
            _('Commission Amount'),
            _('Status'),
            _('Date'),
            _('Customer Name'),
        ])

        for commission in commissions:
            booking = commission.booking
            tour_title = booking.tour.safe_translation_getter('title', default='Unknown Tour') if booking.tour else 'N/A'
            writer.writerow([
                booking.book_id,
                tour_title,
                f"${commission.amount:.2f}",
                commission.get_status_display(),
                commission.created_at.strftime('%Y-%m-%d %H:%M'),
                booking.customer_name or 'N/A',
            ])

        logger.info(f"Exported {commissions.count()} commissions as CSV for user {request.user.username}")
        return response

    elif export_format == 'pdf':
        # Generate LaTeX for PDF
        latex_content = r"""
        \documentclass[a4paper,12pt]{article}
        \usepackage[utf8]{inputenc}
        \usepackage{geometry}
        \geometry{margin=1in}
        \usepackage{booktabs}
        \usepackage{siunitx}
        \sisetup{output-decimal-marker={.}}
        \usepackage[T1]{fontenc}
        \usepackage{noto}
        \usepackage{pdflscape}
        \usepackage{longtable}
        \usepackage{array}

        \begin{document}

        \begin{center}
            \textbf{\Large Commission Report} \\
            \vspace{0.5em}
            \textbf{User: """ + request.user.username + r"""} \\
            \textbf{Period: """ + start_date.strftime('%Y-%m-%d') + r""" to """ + end_date.strftime('%Y-%m-%d') + r"""} \\
        \end{center}

        \vspace{1em}

        \begin{landscape}
        \begin{longtable}{l l S[table-format=6.2] l l l}
            \toprule
            \textbf{Booking ID} & \textbf{Tour Title} & \textbf{Commission Amount (USD)} & \textbf{Status} & \textbf{Date} & \textbf{Customer Name} \\
            \midrule
            \endhead
        """

        for commission in commissions:
            booking = commission.booking
            tour_title = (booking.tour.safe_translation_getter('title', default='Unknown Tour') 
                         if booking.tour else 'N/A').replace('&', r'\&').replace('_', r'\_')
            customer_name = (booking.customer_name or 'N/A').replace('&', r'\&').replace('_', r'\_')
            latex_content += (
                f"  {booking.book_id} & {tour_title} & {commission.amount:.2f} & "
                f"{commission.get_status_display()} & {commission.created_at.strftime('%Y-%m-%d %H:%M')} & "
                f"{customer_name} \\\\\n"
            )

        latex_content += r"""
            \bottomrule
        \end{longtable}
        \end{landscape}

        \end{document}
        """

        # Return LaTeX response (will be processed by latexmk for PDF)
        response = HttpResponse(content_type='text/latex')
        response['Content-Disposition'] = f'attachment; filename="commissions_{start_date}_to_{end_date}.pdf"'
        response.write(latex_content.encode('utf8'))
        
        logger.info(f"Exported {commissions.count()} commissions as PDF for user {request.user.username}")
        return response

    else:
        logger.error(f"Invalid export format: {export_format}")
        return HttpResponse(_("Invalid format. Use 'csv' or 'pdf'."), status=400)