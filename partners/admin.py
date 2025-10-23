# from django.contrib import admin
# from .models import Partner
# from parler.admin import TranslatableAdmin
# from unfold.admin import ModelAdmin

# @admin.register(Partner)
# class PartnerAdmin(TranslatableAdmin, ModelAdmin):
#     list_display = ('name', 'email', 'phone', 'contact_person')
#     search_fields = ('name', 'email', 'contact_person')
#     list_filter = ('created_at',)
#     fieldsets = (
#         (None, {
#             'fields': ('name', 'contact_person', 'email', 'phone')
#         }),
#         ('Additional Info', {
#             'fields': ('address', 'website', 'notes'),
#             'classes': ('collapse',),
#         }),
#     )