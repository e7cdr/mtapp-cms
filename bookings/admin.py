# from datetime import timezone
# from django.conf import settings
# from django.contrib import admin
# from unfold.admin import ModelAdmin
# from django.core.mail import send_mail
# from parler.admin import TranslatableAdmin
# from .models import ExchangeRate, Proposal, Booking
# from django.template.loader import render_to_string
# from django.utils.translation import gettext_lazy as _
# from django.contrib.contenttypes.models import ContentType


# class TourTypeFilter(admin.SimpleListFilter):
#     title = _('Tour Type')
#     parameter_name = 'tour_type'

#     def lookups(self, request, model_admin):
#         return (
#             ('fulltour', _('Full Tour')),
#             ('landtour', _('Land Tour')),
#             ('daytour', _('Day Tour')),
#         )

#     def queryset(self, request, queryset):
#         if self.value():
#             content_type = ContentType.objects.filter(model=self.value()).first()
#             if content_type:
#                 return queryset.filter(content_type=content_type)
#         return queryset

# @admin.register(Proposal)
# class ProposalAdmin(TranslatableAdmin, ModelAdmin):
#     list_display = ['id', 'prop_id', 'get_customer_name', 'user', 'tour_title', 'travel_date', 'status', 'estimated_price']
#     list_filter = ['status', 'user', 'travel_date', TourTypeFilter, 'prop_id']
#     search_fields = ['prop_id','user', 'translations__customer_name', 'translations__notes', 'customer_email']
#     list_per_page = 20
#     actions = ['confirm_proposals', 'reject_proposals']
#     readonly_fields = ['prop_id', 'created_at', 'updated_at']
#     date_hierarchy = 'travel_date'

#     fieldsets = (
#         (None, {
#             'fields': ('user', 'content_type', 'object_id', 'travel_date', 'status', 'estimated_price', 'supplier_email', 'payment_link')
#         }),
#         (_('Customer Information'), {
#             'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_address', 'nationality', 'notes')
#         }),
#         (_('Participants'), {
#             'fields': ('number_of_adults', 'number_of_children')
#         }),
#     )

#     def tour_title(self, obj):
#         """Display the tour title in the admin list view."""
#         return obj.tour.safe_translation_getter('title', default=obj.tour.title) if obj.tour else 'N/A'
#     tour_title.short_description = _('Tour')

#     def get_customer_name(self, obj):
#         return obj.safe_translation_getter('customer_name', default='Unknown')
#     get_customer_name.short_description = _('Customer Name')

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('content_type').prefetch_related('translations', 'tour')

#     def get_search_results(self, request, queryset, search_term):
#         """Custom search to include tour title without querying GenericForeignKey."""
#         queryset, use_distinct = super().get_search_results(request, queryset, search_term)
#         if search_term:
#             content_types = ContentType.objects.filter(model__in=['fulltour', 'landtour', 'daytour'])
#             for ct in content_types:
#                 model = ct.model_class()
#                 tour_ids = model.objects.filter(translations__title__icontains=search_term).values_list('id', flat=True)
#                 queryset |= self.model.objects.filter(
#                     content_type=ct,
#                     object_id__in=tour_ids
#                 )
#         return queryset, use_distinct

#     def confirm_proposals(self, request, queryset):
#         for proposal in queryset.filter(status='PENDING_SUPPLIER'):
#             try:
#                 session = stripe.checkout.Session.create(
#                     payment_method_types=['card'],
#                     line_items=[{
#                         'price_data': {
#                             'currency': 'usd',
#                             'product_data': {
#                                 'name': str(proposal.tour),
#                             },
#                             'unit_amount': int(proposal.estimated_price * 100),
#                         },
#                         'quantity': 1,
#                     }],
#                     mode='payment',
#                     success_url=f"{settings.SITE_URL}/bookings/payment_success/{proposal.id}/",
#                     cancel_url=f"{settings.SITE_URL}/bookings/payment_cancel/{proposal.id}/",
#                     expires_at=int((proposal.created_at + timezone.timedelta(hours=48)).timestamp()),
#                 )
#                 proposal.payment_link = session.url
#                 proposal.status = 'SUPPLIER_CONFIRMED'
#                 proposal.save()
#                 subject = _("Confirm Your Tour Proposal")
#                 message = render_to_string('bookings/emails/preconfirmation.html', {
#                     'proposal': proposal,
#                     'tour': proposal.tour,
#                     'payment_link': proposal.payment_link,
#                     'site_url': settings.SITE_URL,
#                 })
#                 send_mail(
#                     subject,
#                     message,
#                     settings.DEFAULT_FROM_EMAIL,
#                     [proposal.customer_email],
#                     html_message=message,
#                 )
#                 self.message_user(request, f"Proposal {proposal.id} confirmed. Payment link sent.")
#             except Exception as e:
#                 self.message_user(request, f"Error confirming proposal {proposal.id}: {str(e)}", level='error')
#     confirm_proposals.short_description = _("Confirm selected proposals")

#     def reject_proposals(self, request, queryset):
#         for proposal in queryset.filter(status='PENDING_SUPPLIER'):
#             proposal.status = 'REJECTED'
#             proposal.save()
#             self.message_user(request, f"Proposal {proposal.id} rejected.")
#     reject_proposals.short_description = _("Reject selected proposals")

# class BookingAdmin(TranslatableAdmin, ModelAdmin):
#     list_display = ['id', "book_id", 'get_customer_name', 'user', 'tour_title', 'travel_date', 'status', 'payment_status', 'total_price']
#     list_filter = ['status', 'book_id', 'user', 'payment_status', TourTypeFilter, 'travel_date', 'content_type']
#     search_fields = ['translations__customer_name','user', 'book_id' 'translations__notes', 'customer_email', 'tour__translations__title']
#     list_per_page = 20

#     fieldsets = (
#         (None, {
#             'fields': ('user', 'content_type', 'object_id', 'travel_date', 'status', 'payment_status', 'payment_method', 'total_price', 'proposal')
#         }),
#         (_('Customer Information'), {
#             'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_address', 'nationality', 'notes')
#         }),
#         (_('Participants'), {
#             'fields': ('number_of_adults', 'number_of_children')
#         }),
#     )
#     def tour_title(self, obj):
#         """Display the tour title in the admin list view."""
#         return obj.tour.safe_translation_getter('title', default=obj.tour.title) if obj.tour else 'N/A'
#     tour_title.short_description = _('Tour')

#     def get_customer_name(self, obj):
#         return obj.safe_translation_getter('customer_name', default='Unknown')
#     get_customer_name.short_description = _('Customer Name')

#     def get_queryset(self, request):
#         return super().get_queryset(request).prefetch_related('translations', 'tour', 'content_type')
    
# class RatesAdmin(ModelAdmin):
#     list_display = ['currency_code', 'rate_to_usd', 'last_updated']
#     list_filter = ['currency_code', 'rate_to_usd']
#     search_fields = ['currency_code', 'rate_to_usd', 'last_updated']
#     list_per_page = 20

#     fieldsets = (
#         (None, {
#             'fields': ('currency_code', 'rate_to_usd')
#         }),
#     )


# admin.site.register(Booking, BookingAdmin)
# admin.site.register(ExchangeRate, RatesAdmin)