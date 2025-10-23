# # Admin Registration for Tours
# from . import models
# from django.contrib import admin
# from unfold.sites import UnfoldAdminSite
# from parler.admin import TranslatableAdmin, TranslatableTabularInline

# # Define the custom admin site
# class CustomAdminSite(UnfoldAdminSite):
#     def get_context_data(self, request):
#         context = super().get_context_data(request)
#         context["top_destination"] = "Bali"  # Example static data
#         context["booking_count"] = 150
#         context["pending_bookings"] = 12
#         return context

# class FullTourItineraryItemInline(TranslatableTabularInline):
#     model = models.FullTourItineraryItem
#     extra = 1

# class LandTourItineraryItemInline(TranslatableTabularInline):
#     model = models.LandTourItineraryItem
#     extra = 1

# class DayTourItineraryItemInline(TranslatableTabularInline):
#     model = models.DayTourItineraryItem
#     extra = 1

# @admin.register(models.CancellationPolicy)
# class CancellationPolicyAdmin(TranslatableAdmin):
#     list_display = ('name', 'days_before', 'refund_percentage')
#     search_fields = ('translations__name',)

# @admin.register(models.Amenity)
# class AmenityAdmin(TranslatableAdmin):
#     list_display = ('name',)
#     search_fields = ('translations__name',)

# @admin.register(models.FullTour)
# class FullTourAdmin(TranslatableAdmin):
#     inlines = [FullTourItineraryItemInline]
#     list_display = ('title', 'code_id', 'destination', 'location', 'start_date', 'price_dbl_regular', 'image', 'pdf_file', 'is_on_discount', 'is_sold_out', 'is_special_offer')
#     list_filter = ('start_date', 'is_on_discount', 'is_sold_out', 'is_special_offer')
#     search_fields = ('translations__title', 'translations__destination', 'code_id')
#     fieldsets = (
#         (None, {
#             'fields': ('ref_code', 'code_id', 'image', 'cover_image', 'logo_image', 'pdf_file', 'available_days', 'start_date', 'end_date', 'duration_days', 'nights', 'max_capacity', 'available_slots', 'is_on_discount', 'is_sold_out', 'is_special_offer', 'is_all_inclusive')
#         }),
#         ('Translations', {
#             'fields': ('title', 'destination', 'location', 'description', 'cover_page_content', 'general_info', 'final_message', 'travel_period_note', 'courtesies', 'no_inclusions', 'additional_notes', 'optional_activities', 'flight_details', 'hotel')
#         }),
#         ('Pricing', {
#             'fields': (
#                 'seasonal_factor', 'demand_factor',
#                 'price_sgl_regular', 'price_dbl_regular', 'price_tpl_regular', 'price_chd_regular', 'price_inf_regular'
#                 'price_sgl_cash', 'price_dbl_cash', 'price_tpl_cash', 'price_chd_cash', 'price_inf_cash', 'rep_comm',
#                 'child_age_min', 'child_age_max', 'max_children_per_room',
#             )
#         }),
#         ('Details', {
#             'fields': ('supplier_email', 'partners', 'amenities', 'cancellation_policy')
#         }),
#     )
#     readonly_fields = ('code_id',)
#     filter_horizontal = ('partners', 'amenities')
#     prefetch_related_objects = ('image', 'cover_image', 'logo_image')

# @admin.register(models.LandTour)
# class LandTourAdmin(TranslatableAdmin):
#     inlines = [LandTourItineraryItemInline]
#     list_display = ('title', 'code_id', 'destination', 'location', 'start_date', 'available_days', 'price_dbl', 'rep_comm', 'image', 'pdf_file', 'is_on_discount', 'is_sold_out', 'is_special_offer', 'is_all_inclusive')
#     list_filter = ('start_date', 'is_on_discount', 'is_sold_out', 'is_special_offer')
#     search_fields = ('translations__title', 'translations__destination', 'code_id')
#     fieldsets = (
#         (None, {
#             'fields': ('ref_code', 'code_id', 'image', 'cover_image', 'logo_image', 'pdf_file', 'available_days', 'start_date', 'end_date', 'duration_days', 'nights', 'max_capacity', 'available_slots', 'is_on_discount', 'is_sold_out', 'is_special_offer', 'is_all_inclusive')
#         }),
#         ('Translations', {
#             'fields': ('title', 'destination', 'location', 'description', 'cover_page_content', 'general_info', 'final_message', 'courtesies', 'no_inclusions', 'additional_notes', 'hotel')
#         }),
#         ('Pricing', {
#             'fields': ('seasonal_factor', 'demand_factor', 'price_sgl', 'price_dbl', 'price_tpl', 'price_chd', 'price_inf', 'rep_comm',
#                         'child_age_min', 'child_age_max', 'max_children_per_room',
#             )
#         }),
#         ('Details', {
#             'fields': ('supplier_email', 'partners', 'amenities', 'cancellation_policy')
#         }),
#     )
#     readonly_fields = ('code_id',)
#     filter_horizontal = ('partners', 'amenities')
#     prefetch_related_objects = ('image', 'cover_image', 'logo_image')

# @admin.register(models.DayTour)
# class DayTourAdmin(TranslatableAdmin):
#     inlines = [DayTourItineraryItemInline]
#     list_display = ('title', 'code_id', 'destination', 'location', 'date', 'price_adult', 'rep_comm', 'image', 'pdf_file', 'is_on_discount', 'is_sold_out', 'is_special_offer')
#     list_filter = ('date', 'is_on_discount', 'is_sold_out', 'is_special_offer')
#     search_fields = ('translations__title', 'translations__destination', 'code_id')
#     fieldsets = (
#         (None, {
#             'fields': ('ref_code', 'code_id', 'image', 'cover_image', 'logo_image', 'pdf_file', 'available_days', 'date', 'duration_hours', 'max_capacity', 'available_slots', 'is_on_discount', 'is_sold_out', 'is_special_offer')
#         }),
#         ('Translations', {
#             'fields': ('title', 'translations__destination', 'location', 'description', 'cover_page_content', 'general_info', 'final_message', 'courtesies', 'no_inclusions', 'additional_notes')
#         }),
#         ('Pricing', {
#             'fields': ('seasonal_factor', 'demand_factor', 'price_adult', 'price_child', 'price_inf', 'rep_comm',
#                         'child_age_min', 'child_age_max', 'max_children_per_room',


#             )
#         }),
#         ('Details', {
#             'fields': ('supplier_email', 'partners', 'amenities', 'cancellation_policy')
#         }),
#     )
#     readonly_fields = ('code_id',)
#     filter_horizontal = ('partners', 'amenities')
#     prefetch_related_objects = ('image', 'cover_image', 'logo_image')