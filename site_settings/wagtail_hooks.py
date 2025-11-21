# wagtail_hooks.py
from os import path
from django.contrib.contenttypes.models import ContentType
from django.urls import include, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register
from import_export.admin import ImportExportMixin  # This gives you Import/Export buttons

from bookings.models import Proposal, Booking


# Helper: link to the actual tour page in Wagtail explorer
def tour_admin_link(obj):
    if not obj.tour:
        return "-"
    try:
        # Works for Wagtail Page models
        page = obj.tour
        url = reverse("wagtailadmin_pages:edit", args=[page.id])
        return format_html('<a href="{}" target="_blank">{}</a>', url, str(page))
    except Exception:
        return str(obj.tour or "-")

tour_admin_link.short_description = _("Tour")


# ======================== PROPOSAL ADMIN ================================
class ProposalAdmin(ImportExportMixin, ModelAdmin):
    model = Proposal
    menu_label = _("Proposals")
    menu_icon = "doc-full-inverse"
    menu_order = 200
    list_display = (
        "prop_id",
        "customer_name",
        "customer_email",
        tour_admin_link,
        "travel_date",
        "number_of_adults",
        "status",
        "estimated_price",
        "currency",
        "created_at",
    )
    list_filter = ("status", "currency", "travel_date", "created_at", "content_type")
    search_fields = (
        "prop_id",
        "customer_name",
        "customer_email",
        "customer_phone",
        "notes",
    )
    read_only_fields = ("prop_id", "created_at", "updated_at")
    ordering = ("-created_at",)

    index_template_name = "modeladmin/wagtail_index.html"
    inspect_template_name = "modeladmin/wagtail_inspect.html"
    create_template_name = "modeladmin/wagtail_create.html"
    edit_template_name = "modeladmin/wagtail_edit.html"
    # Optional: customize export (tour title instead of ID)
    def get_resource_class(self):
        from import_export import resources

        class ProposalResource(resources.ModelResource):
            tour = resources.Field(column_name="tour_title")

            class Meta:
                model = Proposal
                fields = (
                    "prop_id", "customer_name", "customer_email", "customer_phone",
                    "nationality", "travel_date", "number_of_adults", "number_of_children",
                    "children_ages", "estimated_price", "currency", "status", "created_at",
                )
                export_order = fields

            def dehydrate_tour(self, obj):
                return str(obj.tour) if obj.tour else ""

        return ProposalResource


# ======================== BOOKING ADMIN ================================
class BookingAdmin(ImportExportMixin, ModelAdmin):
    model = Booking
    menu_label = _("Bookings")
    menu_icon = "folder-open-inverse"
    menu_order = 201
    list_display = (
        "book_id",
        "customer_name",
        "customer_email",
        tour_admin_link,
        "travel_date",
        "total_price",
        "currency",
        "payment_status",
        "status",
        "proposal",
        "created_at",
    )
    list_filter = (
        "status",
        "payment_status",
        "currency",
        "travel_date",
        "created_at",
        "content_type",
    )
    search_fields = (
        "book_id",
        "customer_name",
        "customer_email",
        "customer_phone",
    )
    read_only_fields = ("book_id", "created_at", "updated_at")

    index_template_name = "modeladmin/wagtail_index.html"
    inspect_template_name = "modeladmin/wagtail_inspect.html"
    create_template_name = "modeladmin/wagtail_create.html"
    edit_template_name = "modeladmin/wagtail_edit.html"

# ======================== GROUP =========================================
class SalesAdminGroup(ModelAdminGroup):
    menu_label = _("Sales & Bookings")
    menu_icon = "folder-open-1"
    menu_order = 300
    items = (ProposalAdmin, BookingAdmin)
    index_template_name = "modeladmin/wagtail_index.html"
    inspect_template_name = "modeladmin/wagtail_inspect.html"
    create_template_name = "modeladmin/wagtail_create.html"
    edit_template_name = "modeladmin/wagtail_edit.html"


# Register it
modeladmin_register(SalesAdminGroup)

