# import json
# import re
# import os
# import logging
# from io import BytesIO
# from django.urls import reverse
# from reportlab.lib import colors
# from django.core.cache import cache
# from django.utils import translation
# from datetime import date, timedelta
# from bookings.forms import ProposalForm
# from reportlab.pdfbase import pdfmetrics
# from bookings.models import ExchangeRate
# from bookings.views import compute_pricing
# from django.core.paginator import Paginator
# from reportlab.pdfbase.ttfonts import TTFont
# from django.utils.translation import activate
# from django.db.models import Value, CharField
# from media_app.models import MediaItem, MediaVideo
# from reportlab.platypus import Paragraph, Frame
# from generate_pdf import generate_itinerary_pdf
# from reportlab.lib.styles import ParagraphStyle
# from django.utils.translation import get_language
# from reportlab.lib.pagesizes import A4, landscape
# from tours.models import DayTour, FullTour, LandTour
# from django.views.decorators.http import require_POST
# from django.utils.translation import gettext_lazy as _
# from reportlab.platypus import SimpleDocTemplate, PageBreak
# from django.shortcuts import redirect, render, get_object_or_404
# from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse

# logger = logging.getLogger(__name__)

# def get_tours_by_destination():
#     """Fetch tours grouped by destination, only including destinations with tours."""
#     cache_key = f'tours_by_destination_{get_language()}'
#     cached_data = cache.get(cache_key)
#     if cached_data:
#         return cached_data

#     destinations = [
#         'Ecuador',
#         'Colombia',
#         'Dominican Republic',
#         'iceland',
#         'Poland',
#     ]
#     tours_by_destination = {}
#     current_language = get_language()

#     for dest in destinations:
#         full_tours = FullTour.objects.language(current_language).filter(
#             translations__destination=dest, available_slots__gt=0
#         ).select_related('image').prefetch_related('translations').annotate(
#             tour_type_val=Value('full', output_field=CharField())
#         ).distinct()
#         land_tours = LandTour.objects.language(current_language).filter(
#             translations__destination=dest, available_slots__gt=0
#         ).select_related('image').prefetch_related('translations').annotate(
#             tour_type_val=Value('land', output_field=CharField())
#         ).distinct()
#         day_tours = DayTour.objects.language(current_language).filter(
#             translations__destination=dest, available_slots__gt=0
#         ).select_related('image').prefetch_related('translations').annotate(
#             tour_type_val=Value('day', output_field=CharField())
#         ).distinct()
#         tours = list(full_tours) + list(land_tours) + list(day_tours)
#         # Remove duplicates by tour ID
#         seen_ids = set()
#         unique_tours = []
#         for tour in tours:
#             tour_id = f"{tour.__class__.__name__}_{tour.id}"
#             if tour_id not in seen_ids:
#                 unique_tours.append(tour)
#                 seen_ids.add(tour_id)
#         unique_tours = sorted(unique_tours, key=lambda x: x.start_date if hasattr(x, 'start_date') else x.date)
#         if unique_tours:
#             tours_by_destination[dest] = unique_tours

#     logger.debug(f"Tours by destination: { {k: len(v) for k, v in tours_by_destination.items()} }")
#     cache.set(cache_key, tours_by_destination, 60 * 60)  # Cache for 1 hour
#     return tours_by_destination

# def base_context(request):
#     """Base context for all templates."""
#     tours_by_destination = get_tours_by_destination()
#     logger.debug(f"Base context: destinations: {list(tours_by_destination.keys())}")
#     return {
#         'tours_by_destination': tours_by_destination,
#     }

# def home(request):
#     cache_key = f'home_media_{request.LANGUAGE_CODE}'
#     context = cache.get(cache_key)

#     if not context:
#         try:
#             translation.activate(request.LANGUAGE_CODE)
#             carousel_home = MediaItem.objects.filter(display_location__title='carousel_home', is_active=True)
#             carousel_home_video = MediaVideo.objects.filter(display_location='carousel_home_video', is_active=True)
#             azuay = MediaItem.objects.filter(display_location__title='Azuay', is_active=True).first()
#             iceland = MediaItem.objects.filter(display_location__title='Iceland', is_active=True).first()
#             trips = MediaItem.objects.filter(display_location__title='Trips', is_active=True).first()
#             context = {
#                 'carousel_home': carousel_home,
#                 'carousel_home_video': carousel_home_video,
#                 'azuay': azuay,
#                 'iceland': iceland,
#                 'trips': trips,
#             }
#             cache.set(cache_key, context, 60 * 60 * 24)
#         except Exception as e:
#             logger.error(f"Cache error: {e}")
#             context = {
#                 'carousel_home': MediaItem.objects.filter(display_location__title='carousel_home', is_active=True),
#                 'carousel_home_video': MediaVideo.objects.filter(display_location='carousel_home_video', is_active=True),
#                 'azuay': MediaItem.objects.filter(display_location__title='Azuay', is_active=True).first(),
#                 'iceland': MediaItem.objects.filter(display_location__title='Iceland', is_active=True).first(),
#                 'trips': MediaItem.objects.filter(display_location__title='Trips', is_active=True).first(),
#             }

#     context.update(base_context(request))
#     return render(request, 'home.html', context)

# def tours_list(request):
#     translation.activate(request.LANGUAGE_CODE or 'en')

#     tour_type = request.GET.get('tour_type', '')
#     min_price = request.GET.get('min_price', '')
#     max_price = request.GET.get('max_price', '')
#     status = request.GET.get('status', '')
#     is_on_discount = status == 'is_on_discount'
#     is_special_offer = status == 'is_special_offer'
#     is_sold_out = status == 'is_sold_out'
#     page = request.GET.get('page', 1)

#     tours = []

#     tour_types = [tour_type] if tour_type else ['full', 'land', 'day']

#     if 'full' in tour_types:
#         full_tours = FullTour.objects.language(get_language()).all().select_related('image').prefetch_related('amenities', 'translations').annotate(tour_type_val=Value('full', output_field=CharField()))
#         if is_on_discount:
#             full_tours = full_tours.filter(is_on_discount=True)
#         if is_special_offer:
#             full_tours = full_tours.filter(is_special_offer=True)
#         if is_sold_out:
#             full_tours = full_tours.filter(is_sold_out=True)
#         if min_price and min_price.isdigit():
#             full_tours = full_tours.filter(price_dbl_regular__gte=float(min_price))
#         if max_price and max_price.isdigit():
#             full_tours = full_tours.filter(price_dbl_regular__lte=float(max_price))
#         full_tours = full_tours.order_by('start_date')
#         tours.extend(full_tours)
#     if 'land' in tour_types:
#         land_tours = LandTour.objects.language(get_language()).all().select_related('image').prefetch_related('amenities', 'translations').annotate(tour_type_val=Value('land', output_field=CharField()))
#         if is_on_discount:
#             land_tours = land_tours.filter(is_on_discount=True)
#         if is_special_offer:
#             land_tours = land_tours.filter(is_special_offer=True)
#         if is_sold_out:
#             land_tours = land_tours.filter(is_sold_out=True)
#         if min_price and min_price.isdigit():
#             land_tours = land_tours.filter(price_dbl__gte=float(min_price))
#         if max_price and max_price.isdigit():
#             land_tours = land_tours.filter(price_dbl__lte=float(max_price))
#         land_tours = land_tours.order_by('start_date')
#         tours.extend(land_tours)
#     if 'day' in tour_types:
#         day_tours = DayTour.objects.language(get_language()).all().select_related('image').prefetch_related('amenities', 'translations').annotate(tour_type_val=Value('day', output_field=CharField()))
#         if is_on_discount:
#             day_tours = day_tours.filter(is_on_discount=True)
#         if is_special_offer:
#             day_tours = day_tours.filter(is_special_offer=True)
#         if is_sold_out:
#             day_tours = day_tours.filter(is_sold_out=True)
#         if min_price and min_price.isdigit():
#             day_tours = day_tours.filter(price_adult__gte=float(min_price))
#         if max_price and max_price.isdigit():
#             day_tours = day_tours.filter(price_adult__lte=float(max_price))
#         day_tours = day_tours.order_by('date')
#         tours.extend(day_tours)

#     tours = sorted(tours, key=lambda x: x.start_date if hasattr(x, 'start_date') else x.date)

#     items_per_page = 10
#     paginator = Paginator(tours, items_per_page)
#     tours_page = paginator.get_page(page)

#     context = {
#         'tours': tours_page,
#         'selected_tour_types': tour_type,
#         'min_price': min_price,
#         'max_price': max_price,
#         'status': status,
#         'is_on_discount': is_on_discount,
#         'is_special_offer': is_special_offer,
#         'is_sold_out': is_sold_out,
#     }
#     context.update(base_context(request))
#     logger.debug(f"Rendering tours: {len(tours)} found")

#     if request.htmx:
#         return render(request, 'tours/partials/tours_list.html', context)
#     return render(request, 'tours/tours_list.html', context)

# def tour_detail(request, tour_type_val, tour_id):
#     model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
#     model = model_map.get(tour_type_val.lower())

#     if not model:
#         logger.error(f"Invalid tour type: {tour_type_val}")
#         return redirect('tours_list')
#     tour = get_object_or_404(model, id=tour_id)
#     logger.debug(f"Fetching tour: type={tour_type_val}, id={tour_id}")

#     currency = request.session.get('currency', 'USD').upper()
#     initial = {
#         'tour_type': tour_type_val,
#         'tour_id': tour_id,
#         'number_of_adults': 1,
#         'number_of_children': 0,
#         'travel_date': max(tour.start_date, date.today()) if tour_type_val in ['full', 'land'] else tour.date,
#         'child_ages': '[]',
#         'form_submission': 'pricing',
#         'currency': currency,
#     }
#     form = ProposalForm(initial=initial)
#     pricing_data = {
#         'tour_type': tour_type_val,
#         'tour_id': tour_id,
#         'number_of_adults': '1',
#         'number_of_children': '0',
#         'travel_date': initial['travel_date'].isoformat(),
#         'currency': currency,
#         'form_submission': 'pricing',
#         'child_ages': '[]',
#     }
#     configurations = compute_pricing(tour_type_val, tour_id, pricing_data, request.session)
#     configurations_json = json.dumps(configurations, ensure_ascii=False)

#     booking_data = {
#         'tourName': tour.safe_translation_getter('title', 'Untitled'),
#         'tourType': tour_type_val,
#         'tourId': str(tour_id),
#         'languagePrefix': request.LANGUAGE_CODE,
#         'childAgeMin': getattr(tour, 'child_age_min', 7),
#         'childAgeMax': getattr(tour, 'child_age_max', 12),
#     }
#     booking_data_json = json.dumps(booking_data, ensure_ascii=False)

#     context = {
#         'tour': tour,
#         'form': form,
#         'tour_type_val': tour_type_val,
#         'tour_id': tour_id,
#         'booking_data_json': booking_data_json,
#         'tour_duration': tour.duration_days if tour_type_val in ['full', 'land'] else tour.duration_hours,
#         'configurations': configurations,
#         'configurations_json': configurations_json,
#         'currency': currency,
#         'travel_date': initial['travel_date'].isoformat(),
#         'end_date': (initial['travel_date'] + timedelta(days=tour.duration_days)).isoformat() if tour_type_val in ['full', 'land'] else initial['travel_date'].isoformat(),
#         'form_errors': [],  # Empty list for form errors
#         'child_age_min': getattr(tour, 'child_age_min', 7),
#         'max_children_per_room': getattr(tour, 'max_children_per_room', 1),
#         'exchange_rates': ExchangeRate.objects.all(),  # Fetch all exchange rates
#     }
#     context.update(base_context(request))  # Add this line to include tours_by_destination
#     logger.debug(f"Rendering tour_detail with context: tour={tour.title}")
#     return render(request, 'tours/tour_detail.html', context)

# def get_tours_by_type(request):
#     tour_type = request.GET.get('tour_type')
#     page = request.GET.get('page', 1)
#     cache_key = f"tours_{tour_type}_{page}"
#     tours = cache.get(cache_key)

#     if not tours:
#         model_map = {
#             'full': FullTour,
#             'land': LandTour,
#             'day': DayTour,
#         }
#         model = model_map.get(tour_type)
#         if not model:
#             return JsonResponse({'tours': []})

#         queryset = model.objects.filter(available_slots__gt=0)
#         paginator = Paginator(queryset, 10)
#         page_obj = paginator.get_page(page)
#         tours = [{'id': t.pk, 'name': f"{t.safe_translation_getter('title', 'Untitled')} ({t.code_id})"} for t in page_obj]
#         cache.set(cache_key, tours, 60 * 15)

#     return JsonResponse({
#         'tours': tours,
#         'has_next': page_obj.has_next() if page_obj else False,
#         'has_previous': page_obj.has_previous() if page_obj else False,
#         'page': int(page)
#     })

# def available_dates(request):
#     tour_type = request.GET.get('tour_type')
#     tour_id = request.GET.get('tour_id')
#     if not tour_type or not tour_id:
#         logger.warning(f"Invalid parameters: tour_type={tour_type}, tour_id={tour_id}")
#         return JsonResponse({'available_dates': [], 'error': 'Missing tour_type or tour_id'}, status=400)

#     model_map = {
#         'full': FullTour,
#         'land': LandTour,
#         'day': DayTour,
#     }
#     model = model_map.get(tour_type.lower())
#     if not model:
#         logger.error(f"Invalid tour_type: {tour_type}")
#         return JsonResponse({'available_dates': [], 'error': 'Invalid tour type'}, status=400)

#     try:
#         tour = model.objects.get(id=tour_id)
#         available_dates = []
#         if tour_type.lower() == 'day':
#             if not tour.is_sold_out and tour.date >= date.today():
#                 available_dates.append(tour.date.strftime('%Y-%m-%d'))
#             logger.debug(f"DayTour ID={tour_id}: date={tour.date}, is_sold_out={tour.is_sold_out}, available_dates={available_dates}")
#         else:
#             current_date = tour.start_date
#             while current_date <= tour.end_date and current_date >= date.today():
#                 if not tour.is_sold_out:
#                     available_dates.append(current_date.strftime('%Y-%m-%d'))
#                 current_date += timedelta(days=1)
#             logger.debug(f"Tour ID={tour_id} ({tour_type}): start_date={tour.start_date}, end_date={tour.end_date}, is_sold_out={tour.is_sold_out}, available_dates={available_dates}")
#         return JsonResponse({'available_dates': available_dates})
#     except model.DoesNotExist:
#         logger.error(f"Tour not found: type={tour_type}, id={tour_id}")
#         return JsonResponse({'available_dates': [], 'error': 'Tour not found'}, status=404)

# def debug_session(request):
#     language = request.session.get('django_language', 'Not set')
#     return JsonResponse({
#         'django_language': language,
#         'current_language': request.LANGUAGE_CODE,
#     })

# def clear_language_session(request):
#     if request.method == 'POST':
#         if 'django_language' in request.session:
#             del request.session['django_language']
#         return HttpResponseRedirect(reverse('home'))
#     return HttpResponseRedirect(reverse('home'))

# from django.views.i18n import set_language

# def set_language(request):
#     language_code = request.POST.get('language', 'en')
#     next_url = request.POST.get('next', request.GET.get('next', '/'))
#     tour_type = request.POST.get('tour_type') or request.GET.get('tour_type')
#     tour_id = request.POST.get('tour_id') or request.GET.get('tour_id')

#     activate(language_code)
#     response = HttpResponseRedirect(next_url)
#     response.set_cookie('django_language', language_code)

#     if tour_type and tour_id:
#         next_url = reverse('book_tour', kwargs={'tour_type': tour_type, 'tour_id': tour_id})
#         return HttpResponseRedirect(next_url)

#     return response

# @require_POST
# def set_currency(request):
#     currency = request.POST.get('currency', 'USD')
#     request.session['currency'] = currency
#     # Update pricing if needed (return HTML for HTMX)
#     return HttpResponse('Currency updated')  # Placeholder

# def debug_set_language(request):
#     logger.info(f"set_language called with POST: {request.POST}")
#     response = set_language(request)
#     logger.info(f"set_language response: {response['Location']}")
#     return response

# def download_itinerary_pdf(request, tour_type_val, tour_id):
#     model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
#     model = model_map.get(tour_type_val)
#     if not model:
#         logger.error(f"Invalid tour_type_val: {tour_type_val}")
#         raise Http404("Invalid tour type")
#     tour = get_object_or_404(model, id=tour_id)
#     pdf = generate_itinerary_pdf(tour, language_code=request.LANGUAGE_CODE)
#     response = HttpResponse(pdf, content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="{tour.code_id}_itinerary.pdf"'
#     return response

# def generate_itinerary_pdf(tour, language_code='en'):

#     # Register fonts
#     base_path = os.path.join(os.path.dirname(__file__), 'static', 'fonts')
#     pdfmetrics.registerFont(TTFont('Roboto', os.path.join(base_path, 'Roboto-Regular.ttf')))
#     pdfmetrics.registerFont(TTFont('Roboto-Bold', os.path.join(base_path, 'Roboto-Bold.ttf')))

#     # Unit conversion
#     MM_TO_PT = 2.8346

#     buffer = BytesIO()
#     doc = SimpleDocTemplate(
#         buffer,
#         pagesize=landscape(A4),
#         topMargin=0,
#         bottomMargin=0,
#         leftMargin=0,
#         rightMargin=0,
#     )

#     # Styles
#     # styles = getSampleStyleSheet()
#     # title_style = ParagraphStyle(
#     #     name='Title',
#     #     fontName='Roboto-Bold',
#     #     fontSize=28,
#     #     textColor=colors.white,
#     #     alignment=TA_CENTER,
#     #     spaceAfter=15,
#     #     leading=32
#     # )
#     normal_style = ParagraphStyle(
#         name='Normal',
#         fontName='Roboto',
#         fontSize=16.5,
#         textColor=colors.white,
#         alignment=4,
#         leading=15,
#         spaceAfter=15,

#     )
#     bullet_style = ParagraphStyle(
#         name='Bullet',
#         fontName='Roboto',
#         fontSize=16,
#         leftIndent=20,
#         bulletIndent=10,
#         bulletFontName='Roboto',
#         bulletFontSize=18,
#         textColor=colors.white,
#         alignment=4,
#         spaceAfter=15,
#         leading=17
#     )
#     bullet_style2 = ParagraphStyle(
#         name='Bullet',
#         fontName='Roboto',
#         fontSize=16,
#         # leftIndent=20,
#         # bulletIndent=10,
#         # bulletFontName='Roboto',
#         # bulletFontSize=18,
#         textColor=colors.white,
#         alignment=4,
#         spaceAfter=15,
#         leading=15
#     )

#     elements = []
#     page_images = []

#     def clean_text(text):
#         if not text:
#             return "No content available."
#         text = str(text).strip()
#         text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
#         text = re.sub(r'\n+', '<br/>', text)  # Convert newlines to HTML breaks
#         return text

#     def format_bullet_list(items):
#         return '<br/>'.join(f"• {item.strip()}" for item in items if item.strip())

#     def add_background(canvas, doc):
#         page_num = len(page_images_initial) - len(page_images) + 1

#         if page_images and page_images[0]:
#             try:
#                 canvas.drawImage(
#                     page_images[0],
#                     0, 0,
#                     width=doc.width,
#                     height=doc.height,
#                     mask='auto'
#                 )
#             except Exception as e:
#                 logger.error(f"Failed to draw image {page_images[0]}: {e}")
#             canvas.setFillColor(colors.black, alpha=0.5)
#             canvas.rect(0, 0, doc.width, doc.height, fill=1)

#         canvas.setFillColor(colors.white)

#         if page_num == 1:  # Cover
#             canvas.setFont('Roboto-Bold', 28)
#             title = clean_text(tour.safe_translation_getter('title', language_code=language_code)) or "Amazon Adventure"
#             canvas.drawCentredString(doc.width / 2, doc.height - 50 * MM_TO_PT, title)

#         elif page_num == 2:  # General Info
#             canvas.setFont('Roboto-Bold', 28)
#             canvas.drawCentredString(doc.width / 2, doc.height - 25 * MM_TO_PT, str(_("General Information")))

#             # general_info
#             raw_general_info = tour.safe_translation_getter('general_info', language_code=language_code)
#             text = clean_text(raw_general_info) or "Details about your Amazon adventure."
#             frame = Frame(
#                 70 * MM_TO_PT,
#                 doc.height - 127 * MM_TO_PT,
#                 doc.width - 140 * MM_TO_PT,
#                 80 * MM_TO_PT,
#                 showBoundary=0
#             )
#             para = Paragraph(text, normal_style)
#             frame.addFromList([para], canvas)

#             # no_inclusions
#             canvas.setFont('Roboto', 16)
#             canvas.drawString(50 * MM_TO_PT, doc.height - 121 * MM_TO_PT, str(_("Not Included")))
#             no_inclusions_text = tour.safe_translation_getter('no_inclusions', language_code=language_code)
#             items = [item.strip() for item in no_inclusions_text.split(',') if item.strip()]
#             logger.debug(f"No inclusions items: {items}")
#             text = format_bullet_list(items)
#             frame = Frame(
#                 55 * MM_TO_PT,
#                 doc.height - 250 * MM_TO_PT,
#                 doc.width - 120 * MM_TO_PT,
#                 120 * MM_TO_PT,
#                 showBoundary=0,

#             )
#             para = Paragraph(text, bullet_style)
#             frame.addFromList([para], canvas)

#             # cancellation_policy
#             if tour.cancellation_policy:
#                 text = f"{_('Cancellation Policy')}: {tour.cancellation_policy.safe_translation_getter('name')} ({tour.cancellation_policy.refund_percentage}% refund if cancelled {tour.cancellation_policy.days_before} days before)"
#                 text = clean_text(text)
#                 logger.debug(f"Cancellation policy: {text}")
#                 frame = Frame(
#                     20 * MM_TO_PT,
#                     doc.height - 280 * MM_TO_PT,
#                     doc.width - 40 * MM_TO_PT,
#                     20 * MM_TO_PT,
#                     showBoundary=0
#                 )
#                 para = Paragraph(text, normal_style)
#                 frame.addFromList([para], canvas)

#         elif page_num == 3:  # Inclusions
#             canvas.setFont('Roboto-Bold', 28)
#             canvas.drawCentredString(doc.width / 2, doc.height - 20 * MM_TO_PT, str(_("Inclusions")))

#             raw_courtesies = tour.safe_translation_getter('courtesies', language_code=language_code)
#             courtesies_items = [item.strip() for item in raw_courtesies.split('.') if item.strip()]
#             text = format_bullet_list(courtesies_items)
#             frame = Frame(
#                 60 * MM_TO_PT,
#                 doc.height - 150 * MM_TO_PT,
#                 doc.width - 110 * MM_TO_PT,
#                 120 * MM_TO_PT,
#                 showBoundary=0,

#             )
#             para = Paragraph(text, bullet_style2)
#             frame.addFromList([para], canvas)

#         elif 4 <= page_num <= tour.duration_days + 3:  # Day Pages
#             day_index = page_num - 4
#             logger.debug(f"Rendering Day {day_index + 1}, page_num: {page_num}, day_index: {day_index}, itinerary_days: {len(itinerary_days)}")
#             canvas.setFont('Roboto-Bold', 22)
#             canvas.drawCentredString(doc.width / 2, doc.height - 40 * MM_TO_PT, f"Day {day_index + 1}")

#             if day_index < len(itinerary_days):
#                 item = itinerary_days[day_index]
#                 raw_text = item.safe_translation_getter('description', language_code=language_code) or "No description available."
#                 text = clean_text(raw_text)
#                 frame = Frame(
#                     35 * MM_TO_PT,
#                     doc.height - 150 * MM_TO_PT,
#                     doc.width - 70 * MM_TO_PT,
#                     100 * MM_TO_PT,
#                     showBoundary=0
#                 )
#                 para = Paragraph(text, normal_style)
#                 frame.addFromList([para], canvas)
#             else:
#                 logger.warning(f"No itinerary item for day_index: {day_index}")
#                 text = "No itinerary available."
#                 frame = Frame(
#                     20 * MM_TO_PT,
#                     doc.height - 150 * MM_TO_PT,
#                     doc.width - 40 * MM_TO_PT,
#                     100 * MM_TO_PT,
#                     showBoundary=0
#                 )
#                 para = Paragraph(text, normal_style)
#                 frame.addFromList([para], canvas)

#         elif page_num == tour.duration_days + 4:  # Final Page
#             logger.debug("Rendering Final page")
#             # Only logo_image, no text
#             pass

#         page_images.pop(0) if page_images else None

#     # Build pages
#     itinerary_days = list(tour.get_itinerary_days())
#     logger.debug(f"Itinerary days: {[item.safe_translation_getter('description', language_code=language_code)[:50] for item in itinerary_days]}")

#     # Page 1: Cover
#     page_images.append(tour.cover_image.image.path if tour.cover_image else None)
#     elements.append(PageBreak())

#     # Page 2: General Info
#     page_images.append(tour.cover_image.image.path if tour.cover_image else None)
#     elements.append(PageBreak())

#     # Page 3: Inclusions
#     page_images.append(tour.cover_image.image.path if tour.cover_image else None)
#     elements.append(PageBreak())

#     # Pages 4–7: Days 1–4
#     for i, item in enumerate(itinerary_days[:tour.duration_days]):
#         page_images.append(item.watermark_image.image.path if item and item.watermark_image else None)
#         elements.append(PageBreak())

#     # Page 8: Final
#     page_images.append(tour.logo_image.image.path if tour.logo_image else None)
#     elements.append(PageBreak())

#     # Extra image
#     page_images.append(None)

#     page_images_initial = page_images.copy()

#     # Debug output
#     print(f"Elements: {len(elements)}")
#     print(f"Page images: {len(page_images)}")
#     print(f"Itinerary days: {len(itinerary_days)}")
#     print(f"Duration days: {tour.duration_days}")

#     # Build PDF
#     doc.build(elements, onFirstPage=add_background, onLaterPages=add_background)
#     pdf = buffer.getvalue()
#     buffer.close()
#     return pdf

# def preview_itinerary_pdf(request, tour_type_val, tour_id):
#     model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
#     model = model_map.get(tour_type_val)
#     if not model:
#         logger.error(f"Invalid tour_type_val: {tour_type_val}")
#         raise Http404("Invalid tour type")
#     tour = get_object_or_404(model, id=tour_id)
#     pdf = generate_itinerary_pdf(tour, language_code=request.LANGUAGE_CODE)
#     response = HttpResponse(pdf, content_type='application/pdf')
#     response['Content-Disposition'] = 'inline; filename="preview_itinerary.pdf"'
#     return response