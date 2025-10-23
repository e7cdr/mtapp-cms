
from requests import request
from bookings.models import Booking
from tours.views import base_context
from partners.models import Partner
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.utils.translation import get_language
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import TourAvailability, CommunicationLog, Report, StaffTask, DashboardData, AutomatedAlert
from .forms import StaffTaskForm, FullTourForm, LandTourForm, DayTourForm, BookingUpdateForm, TourAvailabilityForm, CommunicationForm
from django.core.cache import cache
from django.core.paginator import Paginator

def is_staff(user):
    return user.is_staff

@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def staff_dashboard(request):
    if request.htmx:
        section = request.GET.get('section')
        if section == 'tasks':
            tasks = StaffTask.objects.filter(assigned_to=request.user).prefetch_related('translations')
            paginator = Paginator(tasks, 5)
            page_obj = paginator.get_page(request.GET.get('page', 1))
            return render(request, 'staff_tools/partials/recent_tasks.html', {'recent_tasks': page_obj})
        elif section == 'alerts':
            alerts = AutomatedAlert.objects.filter(is_resolved=False).prefetch_related('translations')[:5]
            return render(request, 'staff_tools/partials/recent_alerts.html', {'recent_alerts': alerts})
        elif section == 'communications':
            comms = CommunicationLog.objects.filter(staff_name=request.user.username).prefetch_related('translations')[:5]
            return render(request, 'staff_tools/partials/recent_communications.html', {'recent_communications': comms})

    # Full page load
    dashboard_data = cache.get_or_set(
        'dashboard_data',
        DashboardData.objects.prefetch_related('translations').all(),
        60 * 60
    )
    recent_tasks = StaffTask.objects.filter(assigned_to=request.user).prefetch_related('translations')
    task_paginator = Paginator(recent_tasks, 5)
    task_page = task_paginator.get_page(request.GET.get('task_page', 1))
    
    recent_alerts = AutomatedAlert.objects.filter(is_resolved=False).prefetch_related('translations')[:5]
    recent_communications = CommunicationLog.objects.filter(staff_name=request.user.username).prefetch_related('translations')[:5]
    
    return render(request, 'staff_tools/staff_dashboard.html', {
        'dashboard_data': dashboard_data,
        'recent_tasks': task_page,
        'recent_alerts': recent_alerts,
        'recent_communications': recent_communications,
    })

@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def manage_tasks(request):
    if request.method == 'POST':
        form = StaffTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_to = request.user
            task.save()
            form.save_translations(task)
            if request.htmx:
                tasks = StaffTask.objects.filter(assigned_to=request.user).prefetch_related('translations')
                paginator = Paginator(tasks, 10)
                page_obj = paginator.get_page(request.GET.get('page', 1))
                return render(request, 'partials/task_list.html', {'tasks': page_obj})
            return redirect('manage_tasks')
        if request.htmx:
            return render(request, 'partials/task_form.html', {'form': form})
    else:
        form = StaffTaskForm()

    tasks = StaffTask.objects.filter(assigned_to=request.user).prefetch_related('translations')
    paginator = Paginator(tasks, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'staff_tools/manage_tasks.html', {'form': form, 'tasks': page_obj})



@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def tour_detail(request, tour_type, tour_id):
    content_type = ContentType.objects.get(model=tour_type)
    tour = content_type.model_class().objects.prefetch_related('translations', 'amenities').get(id=tour_id)
    return render(request, 'tours/tour_detail.html', {'tour': tour, 'tour_type': tour_type})    

@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def report_detail(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    return render(request, 'report_detail.html', {'report': report})

@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def manage_bookings(request):
    bookings = Booking.objects.prefetch_related('translations').order_by('-booking_date')
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    if request.htmx:
        return render(request, 'partials/booking_list.html', {'bookings': page_obj})
    return render(request, 'staff_tools/manage_bookings.html', {'bookings': page_obj})

@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def booking_detail(request, booking_id):

    booking = get_object_or_404(Booking, pk=booking_id)
    if request.method == 'POST':
        form = BookingUpdateForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            return redirect('manage_bookings')
    else:
        form = BookingUpdateForm(instance=booking)
    return render(request, 'staff_tools/booking_detail.html', {'form': form, 'booking': booking})

@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def manage_availability(request):
    if request.method == 'POST':
        form = TourAvailabilityForm(request.POST)
        if form.is_valid():
            availability = form.save()
            return redirect('manage_availability')
    else:
        form = TourAvailabilityForm()
    availabilities = TourAvailability.objects.all()
    return render(request, 'staff_tools/manage_availability.html', {'form': form, 'availabilities': availabilities})

@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def manage_partners(request):
    partners = Partner.objects.all()
    return render(request, 'staff_tools/manage_partners.html', {'partners': partners})

@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def partner_detail(request, partner_id):
    from .forms import PartnerForm

    partner = get_object_or_404(Partner, pk=partner_id)
    if request.method == 'POST':
        form = PartnerForm(request.POST, instance=partner)
        if form.is_valid():
            form.save()
            return redirect('manage_partners')
    else:
        form = PartnerForm(instance=partner)
    return render(request, 'staff_tools/partner_detail.html', {'form': form, 'partner': partner})

@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def send_communication(request):

    if request.method == 'POST':
        form = CommunicationForm(request.POST)
        if form.is_valid():
            communication = form.save(commit=False)
            communication.staff_name = request.user.username
            communication.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def create_tour(request):

    if request.method == 'POST':
        tour_type = request.POST.get('tour_type')
        if tour_type == 'full':
            form = FullTourForm(request.POST)
        elif tour_type == 'land':
            form = LandTourForm(request.POST)
        elif tour_type == 'day':
            form = DayTourForm(request.POST)
        else:
            return render(request, 'create_tour.html', {'error': 'Invalid tour type'})
        
        if form.is_valid():
            form.save()
            return redirect('staff_dashboard')
    else:
        full_form = FullTourForm()
        land_form = LandTourForm()
        day_form = DayTourForm()
    return render(request, 'staff_tools/create_tour.html', {
        'full_form': full_form,
        'land_form': land_form,
        'day_form': day_form,
    })

# API endpoint for chart data
def chart_data(request, chart_type):
    today = datetime.today()
    last_30_days = today - timedelta(days=30)
    cache_key = f"chart_{chart_type}_{request.user.id}"
    data = cache.get(cache_key)

    if not data:
        if chart_type == 'bookings':
            data = Booking.objects.filter(booking_date__gte=last_30_days).extra(
                select={'date': "date(booking_date)"}
            ).values('date').annotate(count=Count('id')).order_by('date')
        elif chart_type == 'revenue':
            data = Booking.objects.filter(booking_date__gte=last_30_days, status='CONFIRMED').extra(
                select={'date': "date(booking_date)"}
            ).values('date').annotate(total=Sum('total_price')).order_by('date')
        elif chart_type == 'tour_popularity':
            popularity = Booking.objects.values('content_type_id', 'object_id').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            data = []
            for t in popularity:
                content_type = ContentType.objects.get_for_id(t['content_type_id'])
                tour_model = content_type.model_class()
                tour = tour_model.objects.get(pk=t['object_id'])
                data.append({'tour': str(tour), 'count': t['count']})
        elif chart_type == 'age_groups':
            data = {
                'Under 18': Booking.objects.filter(age__lt=18).count(),
                '18-30': Booking.objects.filter(age__gte=18, age__lte=30).count(),
                '31-50': Booking.objects.filter(age__gte=31, age__lte=50).count(),
                '51+': Booking.objects.filter(age__gt=50).count(),
            }
        elif chart_type == 'nationalities':
            current_language = get_language()
            data = Booking.objects.translated(current_language).values('translations__nationality').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
        elif chart_type == 'payment_methods':
            data = Booking.objects.filter(booking_date__gte=last_30_days).values('payment_method').annotate(
                count=Count('id'),
                total_revenue=Sum('total_price')
            ).order_by('-count')
        elif chart_type == 'booking_status':
            data = Booking.objects.filter(booking_date__gte=last_30_days).values('status').annotate(
                count=Count('id')
            ).order_by('status')
        cache.set(cache_key, data, 60 * 15)

    return JsonResponse({'data': list(data)})
@login_required(login_url='/staff/login/')
@user_passes_test(is_staff)
def task_detail(request, task_id):
    task = get_object_or_404(StaffTask.objects.prefetch_related('translations', 'related_booking'), id=task_id, assigned_to=request.user)
    if request.htmx:
        return render(request, 'partials/task_detail.html', {'task': task})
    return render(request, 'staff_tools/task_detail.html', {'task': task})