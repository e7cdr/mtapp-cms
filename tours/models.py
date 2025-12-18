from datetime import date, timedelta
from decimal import Decimal
import os
import logging

from wagtail_localize.fields import TranslatableField, SynchronizedField

from mtapp.utils import convert_pdf_to_images, generate_code_id  # Generic JSONField
from mtapp.choices import DESTINATION_CHOICES, GLOBAL_ICON_CHOICES

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.http import HttpRequest
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from wagtail.models import Page
from wagtail.api import APIField
from wagtail.search import index
from wagtail.fields import StreamField, RichTextField
from wagtail.images.models import Image
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.blocks import (
    StructBlock,
    RichTextBlock,
    ListBlock,
    ChoiceBlock,
    IntegerBlock,
    DateBlock,

)

from wagtailseo.models import SeoMixin

from django.utils.translation import gettext_lazy as _
from wagtail.contrib.routable_page.models import RoutablePageMixin, path

from mtapp.utils_blocks import PricingTierBlock
from streams import blocks

logger = logging.getLogger(__name__)

class AbstractTourPage(SeoMixin, Page):
    # Common content fields
    name = models.CharField(max_length=200, help_text=_("e.g., 'Cuenca Cultural Getaway'"))
    destination = models.CharField(
        max_length=100,
        choices=DESTINATION_CHOICES,
        default="Ecuador",
        help_text=_("Select the destination country.")
    )
    description = RichTextField(help_text=_("Description of the tour."))
    location = models.CharField(max_length=30, help_text=_('Location inside the country'))
    cover_page_content = RichTextField(blank=True, help_text=_("Content for the tour's cover page in the PDF Generator."))
    general_info = RichTextField(blank=True, help_text=_("General info like cancellation policy, inclusions in the PDF Generator."))
    final_message = RichTextField(blank=True, help_text=_("Final message from the travel company in the PDF Generator. "))
    courtesies = RichTextField(default="Guided city tour", help_text=_("Tour inclusions"), blank=True)
    cxl_policies = RichTextField(blank=True, null=True, default="", verbose_name="Cancellation Policies")
    disclaimer = RichTextField(blank=True, null=True, default="", verbose_name="Disclaimer Message (Tours Details)", help_text="For example: All prices are subject to availability")

    amenity = StreamField([
        ('include', ListBlock(ChoiceBlock(choices=GLOBAL_ICON_CHOICES)))
    ], blank=True, use_json_field=True, help_text=_("Add as many amenities."))

    no_inclusions = RichTextField(default="Air Ticket", help_text=_("Not included"), blank=True)
    additional_notes = RichTextField(
                default="Subject to availability", blank=True
    )
    hotel = models.CharField(max_length=50, default='LOCAL', help_text="If applicable")

    # Flags: TODO Custom validation, if sold out, none of the others can be on
    is_on_discount = models.BooleanField(default=False)
    is_special_offer = models.BooleanField(default=False)
    is_sold_out = models.BooleanField(default=False)
    is_all_inclusive = models.BooleanField(default=False)

    price_subtext = models.CharField(default="Estimated", help_text="Estimated. IVA not included", max_length=30)

    # Codes
    ref_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="""This is the Referal Code. This is used for referencing a third party tour. Most of the time,
        large tour operators have their own tour code, so this field can be used to reference by that code so it is easy to find it in large databases.
                """
        )
    code_id = models.CharField(max_length=15, editable=False, help_text="This is the Tours unique internal ID. Other companies might use this code as reference. Without this ID, it would be impossible to render the tours.")

    # Media
    image = models.ForeignKey(
        Image, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(app_label)s_%(class)s_image'
    )
    cover_image = models.ForeignKey(
        Image, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(app_label)s_%(class)s_cover',
        help_text=_("Image for the tour's cover page.")
    )
    logo_image = models.ForeignKey(
        Image, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(app_label)s_%(class)s_logo',
        help_text=_("Company logo for the final page.")
    )
    pdf_file = models.ForeignKey(
        "documents.CustomDocument", on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(app_label)s_%(class)s_pdf'
    )
    pdf_images = models.JSONField(default=list, blank=True, help_text=_("List of URLs for PDF page images"))

    # Dates & Availability (common; override as needed)
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    available_days = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Comma-separated days (0=Sunday, 1=Monday, 2=Tuesday..., 6=Saturday), e.g., '0,1,2,3'"
    )
    blackout_entries = StreamField([
        ('single_date', DateBlock(label="Single Blackout Date", help_text="One specific date to disable. You can add as many single dates")),
        ('date_range', StructBlock([
            ('start_date', DateBlock(label="Start Date", required=True)),
            ('end_date', DateBlock(label="End Date", required=True, help_text="Inclusive end date.")),
        ], label="Blackout Date Range", icon='date')),
    ], blank=True, use_json_field=True, help_text=_("Add single blackout dates or ranges (e.g., holidays, strikes)."))

    # Supplier & Pricing (common)
    supplier_email = models.EmailField(blank=True, help_text=_("Supplier contact email. If This is a in House/company tour, check the next box and skip this email field."))
    is_company_tour = models.BooleanField(
        default=False,
        help_text=_("If True, skip supplier confirmation and go direct to payment (company-run tour).")
    )
    collect_price = models.BooleanField(default=True, help_text="If unchecked, the pricing options won't be available in the Booking Form. Basically, a proposal form without price")
    inquiry_message = RichTextField(verbose_name="Inquiry Message", max_length=300, null=True, blank=True, help_text="If Collect Price is unchecked, or more specifically, if no prices to be collected, please write a message to show instead.")
    pricing_type = models.CharField(
        max_length=20,
        choices=[
                ('Per_room', 'Per Room (classic hotel-style)'),
                ('Per_person', 'Per Person (flat rate, no room logic)'),
                ('Combined', 'Combined (Tiered)'),
            ],
        default='Combined',
        help_text="Combined = adult pays base price, gets discount when sharing room. Best for private tours."
        )
    combined_pricing_tiers = StreamField(
        [
            ('tier', PricingTierBlock()),
        ],
        use_json_field=True,
        verbose_name="Combined Pricing Tiers (by Group Size)",
        blank=True,
        null=True,  # Important for migrations
        help_text="Tiered pricing for Combined mode. Ordered from smallest to largest group.",

    )
    max_children_per_room = models.PositiveIntegerField(default=1, null=True, blank=True)
    child_age_min = models.PositiveIntegerField(default=7, verbose_name="Child Minimum Age")
    child_age_max = models.PositiveIntegerField(default=12, verbose_name="Child Maximum Age")
    pricing_table = models.BooleanField(verbose_name="Enable Pricing Table in Tour Details", default=False)
    show_prices_in_table = RichTextField(
        blank=True,
        null=True,
        help_text="If filled, replaces the entire pricing table with this message in the Tours Detail page."
    )
    button_text = models.CharField(blank=True, null=True, help_text="Text to be shown on the button", max_length=22, default="", verbose_name="Button Text")
    button_link = models.URLField(blank=True, null=True, help_text="Where do you want to send the user? Link the button.")
    price_sgl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Single Room Price")
    price_dbl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Double Room Price")
    price_tpl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Triple Room Price")
    price_adult = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Adults Price")
    price_chd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Children Price")
    price_inf = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Infant Price")
    seasonal_factor = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, verbose_name="Seasonal Price Factor increase", help_text="1.0 = 0%. This will increase the price on certain seasons of the year like holidays")
    demand_factor = models.DecimalField(max_digits=3, decimal_places=2, default=0.0, verbose_name="Demand Factor", help_text="The Demand Factor will increase price based on the total occupancy calculated for the next 30 days (counting the selected travel date). 0 = 0%. If 20%, this means the first booking will have an increased value of 0, and the last one 20%")
    rep_comm = models.PositiveIntegerField(default=0, help_text=_('Sales representative commission'))
    yt_vid = models.CharField(max_length=22, default='', help_text=_("For example: https://www.youtube.com/watch?v=UHLdLtEiFGs >> ID = UHLdLtEiFGs. This video will be shown in the Tours Watch Video."), verbose_name="Youtube Video ID")
    max_capacity = models.PositiveIntegerField(default=20, help_text="Maximum Capacity is taken to calculate price increased based on the demand factor")
    available_slots = models.PositiveIntegerField(default=20)

    # Itinerary
    itinerary = StreamField(
        [
            (
                "day_entry",
                StructBlock(
                    [
                        ("day", IntegerBlock(required=True)),
                        (
                            "description",
                            RichTextBlock(required=True, help_text="Day description"),
                        ),
                        (
                            "highlight",
                            RichTextBlock(required=True, max_chars=300),  # Note: Use max_chars, not max_length
                        ),
                    ]
                ),
            ),
        ],
        use_json_field=True,  # Optional: Improves performance/storage for simple structs
        blank=True,  # Optional: Allow empty itineraries
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    description_content = StreamField(
        [
            ("swipers", blocks.Swipers()),

        ],
        null=True,
        blank=True,
        help_text="""
        This content will only be added inside the description content
        """,
    )

        # Shared panels (extend in children)
    content_panels = list(Page.content_panels) + [
        # ─── BASIC INFO ───
        MultiFieldPanel([
            FieldPanel('code_id', read_only=True),
            FieldPanel('ref_code'),
            FieldPanel('name'),
            FieldPanel('description'),
            FieldPanel('description_content'),
            FieldPanel('destination'),
            FieldPanel('location'),
            FieldPanel('hotel'),
            FieldPanel('courtesies'),
            FieldPanel('amenity'),
            FieldPanel('no_inclusions'),
            FieldPanel('additional_notes'),
            FieldPanel('cxl_policies'),
            FieldPanel('supplier_email'),
            FieldPanel('is_company_tour'),
        ], heading="Content & Basic Info", classname="collapsible collapsed"),

        # ─── MEDIA ───
        MultiFieldPanel([
            FieldPanel('cover_image'),
            FieldPanel('pdf_file'),
            FieldPanel('yt_vid'),
        ], heading="Media", classname="collapsible collapsed"),

        # ─── TOUR CONFIG ───
        MultiFieldPanel([
            FieldPanel('max_capacity'),
            FieldPanel('available_slots'),
            FieldPanel('itinerary'),
            FieldPanel('start_date'),
            FieldPanel('end_date'),
            FieldPanel('available_days'),
            FieldPanel('blackout_entries'),
        ], heading="Tour Configuration", classname="collapsible collapsed"),

        # ─── CURRENT STATE ───
        MultiFieldPanel([
            FieldPanel('is_on_discount'),
            FieldPanel('is_special_offer'),
            FieldPanel('is_all_inclusive'),
            FieldPanel('is_sold_out'),
        ], heading="Tour Status", classname="collapsible collapsed"),
        # ─── PRICING CONFIGURATION (THE BIG ONE) ───
        MultiFieldPanel([
            FieldPanel('collect_price'),
            FieldPanel('inquiry_message'),
            FieldPanel('pricing_table'),
            FieldPanel('show_prices_in_table'),
            FieldPanel('button_text'),
            FieldPanel('button_link'),
            FieldPanel('pricing_type', classname='pricing-type-selector'),

            # Per-Room Pricing
            MultiFieldPanel([
                FieldPanel('price_sgl'),
                FieldPanel('price_dbl'),
                FieldPanel('price_tpl'),
                FieldPanel('price_chd'),
                FieldPanel('price_inf'),
            ], heading="Per-Room Pricing", classname="per-room-panel collapsible collapsed"),

            # Per-Person Pricing
            MultiFieldPanel([
                FieldPanel('price_adult'),
                FieldPanel('price_chd'),
                FieldPanel('price_inf'),
            ], heading="Per-Person Pricing", classname="per-person-panel collapsible collapsed"),

            # Combined Tiered Pricing
            MultiFieldPanel([
                FieldPanel('combined_pricing_tiers'),
            ], heading="Read carefully.", classname="combined-pricing-panel collapsible collapsed"),

            # Shared Settings
            MultiFieldPanel([
                FieldPanel('child_age_min'),
                FieldPanel('child_age_max'),
                FieldPanel('max_children_per_room'),
                FieldPanel('price_subtext'),
                FieldPanel('seasonal_factor'),
                FieldPanel('demand_factor'),
                FieldPanel('rep_comm'),
            ], heading="Additional Pricing Settings", classname="collapsible collapsed"),

        ], heading="Pricing Configuration", classname="collapsible"),
    ]



    template = "tours/tour_detail.html"


    class Meta:
        abstract = True  # Key: No DB table
        unique_together = [('locale', 'code_id', 'ref_code')]

    translated_fields = [
        TranslatableField('title'),
        TranslatableField('name'),
        TranslatableField('description'),
        TranslatableField('intro'),
        TranslatableField('itinerary'),
        TranslatableField('courtesies'),
        TranslatableField('cxl_policies'),
        TranslatableField('disclaimer'),
        TranslatableField('seo_title'),
        TranslatableField('search_description'),
        TranslatableField('slug'),  # Optional: pretty URLs per language
    ]

    synchronized_fields = [
        SynchronizedField('cover_image'),
        SynchronizedField('image'),
        SynchronizedField('logo_image'),
        SynchronizedField('pdf_file'),
        SynchronizedField('start_date'),
        SynchronizedField('end_date'),
        SynchronizedField('duration'),
        SynchronizedField('pricing_type'),
        SynchronizedField('price_sgl'),
        SynchronizedField('price_dbl'),
        SynchronizedField('price_tpl'),
        SynchronizedField('price_adult'),
        SynchronizedField('price_chd'),
        SynchronizedField('price_inf'),
        SynchronizedField('is_on_discount'),
        SynchronizedField('is_special_offer'),
        SynchronizedField('is_sold_out'),
        SynchronizedField('is_all_inclusive'),
        # ... any other non-translatable field ...
    ]

    @property
    def active_prices(self):
        """Returns dict of prices based on pricing_type."""
        base = {}
        if self.pricing_type in ['Per_room', 'Combined']:
            base.update({
                'sgl': self.price_sgl,
                'dbl': self.price_dbl,
                'tpl': self.price_tpl,
            })
        if self.pricing_type in ['Per_person', 'Combined']:
            base.update({
                'adult': self.price_adult,
                'chd': self.price_chd,
                'inf': self.price_inf,
            })
        if self.pricing_type == 'Per_person':
            base['max_children_per_room'] = self.max_children_per_room
        return base

    @property
    def blackout_dates_list(self):
        """Flatten blackout_entries to list of 'YYYY-MM-DD' strings (expands ranges)."""
        if not self.blackout_entries:
            return []
        dates = []
        for block in self.blackout_entries:
            if block.block_type == 'single_date':
                dates.append(block.value.strftime('%Y-%m-%d'))
            elif block.block_type == 'date_range':
                start = block.value['start_date']
                end = block.value['end_date']
                current = start
                while current <= end:
                    dates.append(current.strftime('%Y-%m-%d'))
                    current += timedelta(days=1)
        return dates  # JSON-safe list

    def get_itinerary_days(self):
        return self.itinerary

    def get_context(self, request):
        context = super().get_context(request)

        # Extract selected values from amenity StreamField
        selected_values = []
        if self.amenity:
            for block in self.amenity:
                if block.block_type == 'include':  # Your ListBlock type
                    selected_values.extend(block.value)  # Flatten the list of choices

        # Build dict for fast lookup (once, efficient for 20+ choices)
        choice_dict = {choice_value: label for choice_value, label in blocks.GLOBAL_ICON_CHOICES}

        # Get labels for selected values
        amenity_labels = [choice_dict.get(value, value) for value in selected_values]  # Fallback to value if no match
        # Get available days
        if self.available_days:
            context['available_days'] = self.available_days
        else:
            context['available_days'] = []
        context['amenity_labels'] = amenity_labels  # Or ', '.join(amenity_labels) for a single string
        context['blackout_dates_list'] = self.blackout_dates_list  # For JS
        return context

    def clean(self):
        super().clean()

        if not self.collect_price and not self.inquiry_message:
            raise ValidationError({
                'inquiry_message': _(
                    "This field is required when 'Collect Price' is unchecked."
                )
            })

        if self.pricing_type == 'Per_room':
            self.price_adult = self.price_chd = self.price_inf = None
            self.combined_pricing_tiers = []
            self.per_person_pricing = []

        elif self.pricing_type == 'Per_person':
            self.price_sgl = self.price_dbl = self.price_tpl = None
            self.combined_pricing_tiers = []   # ← Add this
            # self.per_room_pricing = []      # if exists

        elif self.pricing_type == 'Combined':
            self.price_sgl = self.price_dbl = self.price_tpl = None
            self.price_adult = self.price_chd = self.price_inf = None


        # Generate code_id only if missing (e.g., new page in default locale)
        if not self.code_id:
            prefix = self.get_code_prefix()
            self.code_id = generate_code_id(prefix)
            # No while loop here—let per-locale validation handle conflicts

        # Per-locale uniqueness checks (allows sharing across locales)
        if self.code_id:
            existing = self.__class__.objects.filter(
                locale=self.locale,
                code_id=self.code_id
            ).exclude(id=self.id)
            if existing.exists():
                raise ValidationError('Tour with this Code ID already exists in this locale.')

        if self.ref_code:  # Assuming ref_code also shared; adjust if unique globally
            existing = self.__class__.objects.filter(
                locale=self.locale,
                ref_code=self.ref_code
            ).exclude(id=self.id)
            if existing.exists():
                raise ValidationError('Tour with this Ref Code already exists in this locale.')

        # Date validation
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError("Start date must be before end date.")
        elif not self.start_date or not self.end_date:
            raise ValidationError("Both start date and end date are required.")
        if self.available_slots > self.max_capacity:
            raise ValidationError(_("Available slots cannot exceed max capacity."))

        if self.pricing_type == 'Per_room':
            room_prices = [p for p in [self.price_sgl, self.price_dbl, self.price_tpl] if p not in (None, Decimal('0.00'))]
            if not room_prices:
                raise ValidationError("At least one per-room price required.")

            # Clear per-person (set to None, including if 0.00)
            self.price_adult = None
            self.price_chd = None
            self.price_inf = None
            self.max_children_per_room = None  # Optional: Clear child room limit too

        elif self.pricing_type == 'Per_person':
            # Require at least one per-person price
            if not any([self.price_adult, self.price_chd, self.price_inf]):
                raise ValidationError("At least one per-person price (Adult, Child, or Infant) is required for 'Per Person'.")

            # Clear per-room
            self.price_sgl = None
            self.price_dbl = None
            self.price_tpl = None

        # Existing validations...
        if self.available_slots > self.max_capacity:
            raise ValidationError(_("Available slots cannot exceed max capacity."))

    def save(self, *args, **kwargs):
        # self.is_sold_out = self.available_slots <= 0
        logger.debug(f"Saving {self.__class__.__name__} {self.id or 'new'}, code_id={self.code_id}, ref_code={self.ref_code}")
        super().save(*args, **kwargs)

        # PDF conversion (shared)
        if self.pdf_file and self.pdf_file.file:
            output_dir = os.path.join(settings.MEDIA_ROOT, f'tour_{self.id}_pdf_images')
            pdf_path = self.pdf_file.file.path
            try:
                image_paths = convert_pdf_to_images(pdf_path, output_dir, self.id)
                if image_paths != self.pdf_images:
                    self.pdf_images = image_paths
                    # super().save(update_fields=['pdf_images'])
                logger.info(f"Generated {len(self.pdf_images)} images for tour {self.id}")
            except Exception as e:
                logger.error(f"Failed to convert PDF for tour {self.id}: {str(e)}")
                self.pdf_images = []
                # super().save(update_fields=['pdf_images'])
        else:
            self.pdf_images = []
            # super().save(update_fields=['pdf_images'])

    # Translation/Alias logic (move your existing methods here, adapting for abstract)
    def copy_for_translation(self, locale, copy_parents=True, alias=False):
        logger.debug(f"Copying page {self.id} for translation to locale {locale.language_code}, code_id={self.code_id}, ref_code={self.ref_code}, alias={alias}")

        # Temporarily set values to pass validation (but we'll override post-copy)
        original_code_id = self.code_id
        original_ref_code = self.ref_code
        # No changes needed—validation will pass since new locale

        try:
            translated_page = super().copy_for_translation(locale, copy_parents, alias)
            logger.debug(f"Translated page created: code_id={translated_page.code_id}, ref_code={translated_page.ref_code}")
        finally:
            pass  # No restore needed

        # Sync the shared identifiers
        translated_page.code_id = original_code_id
        translated_page.ref_code = original_ref_code
        translated_page.full_clean()  # Re-validate with new locale
        translated_page.save()

        logger.debug(f"Translated page saved with shared codes: code_id={translated_page.code_id}, ref_code={translated_page.ref_code}")
        return translated_page

    def create_alias(self, *, recursive=False, parent=None, update_slug=None, **kwargs):

        # Create alias with shared codes
        alias = super().create_alias(recursive=recursive, parent=parent, update_slug=update_slug, **kwargs)

        # Sync identifiers (alias gets same locale? Wait—aliases in wagtail_localize use target locale)
        alias.code_id = self.code_id
        alias.ref_code = self.ref_code
        alias.full_clean()  # Validate in target locale
        alias.save()

        logger.debug(f"Alias created with shared codes: code_id={alias.code_id}, ref_code={alias.ref_code}")
        return alias

    def get_code_prefix(self):
        """Override in children for 'LT', 'FT', 'DT'."""
        raise NotImplementedError("Subclasses must define get_code_prefix()")
    
    def get_jsonld_schema(self):
        """
        100% safe TouristTrip JSON-LD — works on ALL tour types
        """
        site = self.get_site()
        base_url = site.root_url if site else "https://milanotravel.com.ec"

        # Safe description
        description = ""
        if self.description:
            description = self.description.source if hasattr(self.description, 'source') else str(self.description)

        # Safe images
        images = []
        for img in [self.cover_image, self.image]:
            if img:
                try:
                    images.append(img.get_rendition("fill-1200x630").url)
                except:
                    pass

        # Safe itinerary
        itinerary_items = []
        if hasattr(self, 'itinerary') and self.itinerary:
            for i, block in enumerate(self.itinerary, 1):
                desc = ""
                if block.value.get("description"):
                    d = block.value["description"]
                    desc = d.source if hasattr(d, 'source') else str(d)
                if block.value.get("highlight"):
                    h = block.value["highlight"]
                    h_text = h.source if hasattr(h, 'source') else str(h)
                    if desc:
                        desc += f" — {h_text}"
                    else:
                        desc = h_text
                if desc.strip():
                    itinerary_items.append({
                        "@type": "TouristAttraction",
                        "name": f"Day {i}",
                        "description": desc.strip()
                    })

        # Safe pricing
        price = None
        price_text = "Contact us"
        if getattr(self, 'collect_price', False) and not getattr(self, 'is_sold_out', False):
            prices = getattr(self, 'active_prices', {})
            if self.pricing_type == "Per_person":
                price = prices.get("adult") or prices.get("chd") or prices.get("inf")
            elif self.pricing_type == "Per_room":
                price = prices.get("dbl") or prices.get("sgl") or prices.get("tpl")
            else:  # Combined
                tiers = getattr(self, 'combined_pricing_tiers', [])
                if tiers:
                    price = tiers[0].value.get("price_per_person")
                else:
                    price = prices.get("adult") or prices.get("dbl")

            if price:
                price_text = f"From ${price}"

        # Build schema
        schema = {
            "@context": "https://schema.org",
            "@type": "TouristTrip",
            "name": getattr(self, 'name', self.title),
            "description": description.strip(),
            "url": self.full_url or f"{base_url}{self.url}",
            "image": images or None,
            "itinerary": {
                "@type": "ItemList",
                "numberOfItems": len(itinerary_items),
                "itemListElement": itinerary_items
            } if itinerary_items else None,
            "offers": {
                "@type": "Offer",
                "url": self.full_url or f"{base_url}{self.url}",
                "priceCurrency": "USD",
                "price": float(price) if price else None,
                "priceSpecification": {
                    "@type": "PriceSpecification",
                    "price": float(price) if price else None,
                    "priceCurrency": "USD",
                    "description": price_text
                } if price else None,
                "availability": "https://schema.org/InStock" if not getattr(self, 'is_sold_out', False) else "https://schema.org/SoldOut",
                "seller": {"@type": "TravelAgency", "name": "Milano Travel"}
            }
        }

        # FullTour flight
        if getattr(self, 'includes_international_flight', False):
            schema["subTrip"] = {
                "@type": "Flight",
                "departureAirport": {"@type": "Airport", "name": getattr(self, 'departure_cities', 'International')},
                "airline": {"@type": "Airline", "name": getattr(self, 'airline', 'Multiple carriers')}
            }

        # Remove empty values
        return {k: v for k, v in schema.items() if v not in (None, "", [], {})}

    def __str__(self):
        return self.title or self.name or 'Untitled Tour'

class ToursIndexPage(SeoMixin, RoutablePageMixin, Page):
    intro = RichTextField(blank=True, null=True, help_text="Text describing what the user can find on the Tours Index", verbose_name="Explanatory Text")
    max_count = 1

    template = "tours/tours_index_page.html"

    parent_page_types = ['home.HomePage']
    subpage_types = ['tours.LandTourPage', 'tours.DayTourPage', 'tours.FullTourPage']  # TODO: Add 'tours.DayTourPage', 'tours.FullTourPage'

#
    body_content = StreamField([
            ("text_band", blocks.TextBand_Block()),
            ("flex_images", blocks.Flex_Images_Block()),
            ("swipers", blocks.Swipers()),
            ("explore_block", blocks.ExploreBlock()),
            ("video_text_content", blocks.Video_Text_Block()),
            ("cta_2B", blocks.CTA_Block_2B()),

    ],  blank=True,
        null=True,
        use_json_field=True)


    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body_content'),
    ]

    search_fields = Page.search_fields + [  # For future search
        index.SearchField('intro'),
    ]

    translated_fields = [
        TranslatableField('title'),
        TranslatableField('intro'),
        TranslatableField('seo_title'),
        TranslatableField('search_description'),
    ]

    # These stay the same across languages
    synchronized_fields = [
        SynchronizedField('body_content'),  # Usually same layout
    ]

    class Meta:
        verbose_name = "Tours List Page"
        verbose_name_plural = "Tours Indices"

    @property
    def base_price(self):
        """Fallback to first available price for filtering."""
        if self.pricing_type == 'Per_room':
            return self.price_dbl or self.price_sgl or self.price_tpl or 0
        elif self.pricing_type == 'Per_person':
            return self.price_adult or self.price_chd or self.price_inf or 0
        return 0

    # def get_context(self, request: HttpRequest):
    #     context = super().get_context(request)

    #     # Base queryset
    #     tours_qs = LandTourPage.objects.live().public().filter(locale=self.locale).specific()

    #     # Dynamic unique destinations
    #     filtered_qs = tours_qs.exclude(destination__exact='')  # Filter blanks first
    #     unique_destinations = list(filtered_qs.values_list('destination', flat=True).distinct().order_by('destination'))

    #     # Apply filters
    #     tour_type = request.GET.get('tour_type')
    #     status = request.GET.get('status')
    #     min_price = request.GET.get('min_price')
    #     max_price = request.GET.get('max_price')
    #     destination = request.GET.get('destination')
    #     pricing_type = request.GET.get('pricing_type', '').strip()

    #     if tour_type == 'land':
    #         pass

    #     if status:
    #         status_map = {
    #             'on_discount': Q(is_on_discount=True),
    #             'special_offer': Q(is_special_offer=True),
    #             'sold_out': Q(is_sold_out=True),
    #         }
    #         if status in status_map:
    #             tours_qs = tours_qs.filter(status_map[status])
    #             print("*** Applied status", status, "- count:", tours_qs.count())  # TEMP

    #     if destination:
    #         tours_qs = tours_qs.filter(destination=destination)
    #         print("*** Applied destination", destination, "- count:", tours_qs.count())  # TEMP

    #     # Pricing type filter (fixed—no .title())
    #     pricing_type = request.GET.get('pricing_type', '').strip()

    #     if pricing_type and pricing_type != '':
    #         valid_types = ['Per_room', 'Per_person']
    #         if pricing_type in valid_types:  # Exact match—no normalize
    #             tours_qs = tours_qs.filter(pricing_type=pricing_type)
    #             print("*** Applied pricing_type", pricing_type, "- count:", tours_qs.count())  # TEMP
    #         else:
    #             print("*** Invalid pricing_type", pricing_type, "(not in", valid_types, ")")  # TEMP
    #     else:
    #         print("*** Skipped pricing_type (empty)")  # TEMP

    #     # Price min/max
    #     if min_price:
    #         min_price_dec = Decimal(min_price)
    #         price_min_q = (
    #             Q(price_dbl__gte=min_price_dec) | Q(price_sgl__gte=min_price_dec) | Q(price_tpl__gte=min_price_dec) |
    #             Q(price_adult__gte=min_price_dec) | Q(price_chd__gte=min_price_dec) | Q(price_inf__gte=min_price_dec)
    #         )
    #         tours_qs = tours_qs.filter(price_min_q)

    #     if max_price:
    #         max_price_dec = Decimal(max_price)
    #         price_max_q = (
    #             Q(price_dbl__lte=max_price_dec) | Q(price_sgl__lte=max_price_dec) | Q(price_tpl__lte=max_price_dec) |
    #             Q(price_adult__lte=max_price_dec) | Q(price_chd__lte=max_price_dec) | Q(price_inf__lte=max_price_dec)
    #         )
    #         tours_qs = tours_qs.filter(price_max_q)

    #     # Order & Paginate
    #     tours_qs = tours_qs.order_by('-start_date')
    #     paginator = Paginator(tours_qs, 12)
    #     page_num = request.GET.get('page')
    #     try:
    #         tours_pag = paginator.page(page_num)
    #     except PageNotAnInteger:
    #         tours_pag = paginator.page(1)
    #     except EmptyPage:
    #         tours_pag = paginator.page(paginator.num_pages)

    #     # Context
    #     context['tours'] = tours_qs
    #     context['tours_pag'] = tours_pag
    #     context['active_filters'] = request.GET
    #     context['GLOBAL_ICON_CHOICES'] = blocks.GLOBAL_ICON_CHOICES
    #     context['unique_destinations'] = unique_destinations


    #     return context
    def get_context(self, request: HttpRequest):
        context = super().get_context(request)

        from tours.models import LandTourPage, DayTourPage, FullTourPage

        tour_models = (LandTourPage, DayTourPage, FullTourPage)

        # ALL TOURS — start with specific descendants
        base_qs = Page.objects.live().public().descendant_of(self).specific().filter(locale=self.locale)

        # Apply tour type filter first
        tour_type_filter = request.GET.get('tour_type')
        if tour_type_filter:
            type_map = {
                'land': LandTourPage,
                'day': DayTourPage,
                'full': FullTourPage,
            }
            if tour_type_filter in type_map:
                base_qs = base_qs.type(type_map[tour_type_filter])

        # Now get the actual tours (with start_date)
        tours = []
        for model in tour_models:
            qs = base_qs.type(model)
            tours.extend(list(qs))

        print(f"*** Total tours collected: {len(tours)}")

        # UNIQUE DESTINATIONS
        unique_destinations = set()
        for tour in tours:
            if hasattr(tour, 'destination') and tour.destination:
                unique_destinations.add(tour.destination)
        unique_destinations = sorted(list(unique_destinations))
        print(f"*** Unique destinations: {unique_destinations}")

        # APPLY OTHER FILTERS (status, destination, pricing_type, price)
        filtered_tours = tours.copy()

        status = request.GET.get('status')
        if status:
            status_map = {
                'on_discount': lambda t: t.is_on_discount,
                'special_offer': lambda t: t.is_special_offer,
                'sold_out': lambda t: t.is_sold_out,
            }
            if status in status_map:
                filtered_tours = [t for t in filtered_tours if status_map[status](t)]

        destination = request.GET.get('destination')
        if destination:
            filtered_tours = [t for t in filtered_tours if getattr(t, 'destination', '') == destination]

        pricing_type = request.GET.get('pricing_type', '').strip()
        if pricing_type in ['Per_room', 'Per_person', 'Combined']:
            filtered_tours = [t for t in filtered_tours if t.pricing_type == pricing_type]

        # Price filter
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        if min_price or max_price:
            min_dec = Decimal(min_price) if min_price else None
            max_dec = Decimal(max_price) if max_price else None
            price_fields = ['price_sgl', 'price_dbl', 'price_tpl', 'price_adult', 'price_chd', 'price_inf']

            def has_price_in_range(t):
                for field in price_fields:
                    price = getattr(t, field, None)
                    if price is not None:
                        if min_dec and price < min_dec:
                            continue
                        if max_dec and price > max_dec:
                            continue
                        return True
                return False

            filtered_tours = [t for t in filtered_tours if has_price_in_range(t)]

        # ORDER BY start_date (now safe — all objects have it)
        filtered_tours.sort(key=lambda t: getattr(t, 'start_date', date.min), reverse=True)

        print(f"*** Final filtered count: {len(filtered_tours)}")

        # PAGINATE
        paginator = Paginator(filtered_tours, 12)
        page_num = request.GET.get('page', 1)
        try:
            tours_pag = paginator.page(page_num)
        except PageNotAnInteger:
            tours_pag = paginator.page(1)
        except EmptyPage:
            tours_pag = paginator.page(paginator.num_pages)

        context.update({
            'tours_pag': tours_pag,
            'unique_destinations': unique_destinations,
            'active_filters': request.GET,
        })

        return context

    # @path('all/', name='all')
    # def all_tours(self, request):
    #     # Reuse get_context logic, but ensure full list
    #     context = self.get_context(request)
    #     context['tours'] = context['tours']
    #     return self.render(request, context_overrides=context)

    # @path('land-tours/', name='land_tours')
    # def land_tours(self, request):
    #     # Pre-filter to LandTourPage (redundant now, but future-proof)
    #     request.GET = request.GET.copy()  # Mutable copy
    #     request.GET['tour_type'] = 'land'  # Force type for this route
    #     context = self.get_context(request)
    #     return self.render(request, context_overrides=context)

    # # TODO: Add routes for other types
    # @path('day-tours/', name='day_tours')
    # def day_tours(self, request):
    #     request.GET['tour_type'] = 'day'
    #     context = self.get_context(request)
    #     return self.render(request, context_overrides=context)
    
    # @path('full-tours/', name='full_tours')
    # def full_tours(self, request):
    #     request.GET['tour_type'] = 'full'
    #     context = self.get_context(request)
    #     return self.render(request, context_overrides=context)

class LandTourPage(AbstractTourPage): # Land Tour Details
    # Land-specific (e.g., duration_days, nights)
    duration_days = models.PositiveIntegerField(default=3)
    nights = models.PositiveIntegerField(default=2)

    # Add to panels

    content_panels = AbstractTourPage.content_panels + [
        FieldPanel('duration_days'),
        FieldPanel('nights'),
    ]


    # search_fields =  Page.search_fields + [
    #     index.SearchField('nights'),
    #     index.SearchField('description'),

    # ]

    # For Api Foreignkey
    """

    class FieldSerializer(Field):
        def to_representation(self, value):
            return {
                'key_name': value.field_name,
                'key_name2': value.field_name2,
            }


    class ImageSerializer(Field):
        def to_representation(self, value):
        return {
            "original":{
                'key_name': value.field_name,
                'key_name2': value.field_name2,
                },
            "thumbnail":{
                'url': value.get_rendition('max-100x100').url,
                'width': value.get_rendition('max-100x100').width,
                'height': value.get_rendition('max-100x100').height,
                },
            "small":{
                'url': value.get_rendition('max-300x300').url,
                'width': value.get_rendition('max-300x300').width,
                'height': value.get_rendition('max-300x300').height,
                }
        }
from wagtail.templatetags.wagtailcore_tags import richtext
    class RichTextFieldSerializer(Field):
        def to_representation(self, value):
        return richtext(value)

Block representation
    class ImageBlock()
    /The following method needs to be inside the Block/
    def get_api_representation(self, value, context=None):
    return {
        'id': value.id
        'title': value.title,
        'src': value.get_rendition('fill-400x400').url
        }

    class CustomPageChooserBlock(blocks.PageChooserBlock):

    def get_api_representation(self, value, context=None):
        return {
            'id': value.id,
            'title': value.title,
            'subtitle': value.specific.subtitle,
            'url': value.url,
            }

    /specific is used for the specific page field. For example
    If subtitle is coming from tours page model, value.subtitle wont work.
    All pages live in Page.++. Page.tours.subtitle would be value.specific.subtitle

    For orderables, it is a bit different calling APIFields
    """
    #  APIField('field_name', serializer=FieldSerializer()),

    api_fields = [ #To show more details in the API
        APIField('duration_days'),
        APIField('nights'),
        APIField('itinerary'),
        APIField('child_age_min'),

    ]

    template = "tours/tour_detail.html"
    parent_page_types = ['tours.ToursIndexPage']

    class Meta:
        verbose_name = "Land Tour"
        verbose_name_plural = "Land Tours"


    def get_code_prefix(self):
        return "LT"

class FullTourPage(AbstractTourPage):
    """
    Exactly like LandTourPage but includes international/domestic air tickets.
    Perfect for packages from Poland, Iceland, Colombia, Dominican Republic → Ecuador.
    """
    duration_days = models.PositiveIntegerField(default=8, help_text="Total trip days (including flights)")
    nights = models.PositiveIntegerField(default=7)

    # Air-ticket specific fields
    includes_international_flight = models.BooleanField(
        default=True,
        help_text="Check if round-trip international flight is included"
    )
    departure_cities = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. Warsaw (WAW), Reykjavik (KEF), Bogotá (BOG), Santo Domingo (SDQ)"
    )
    airline = models.CharField(max_length=100, blank=True, help_text="e.g. LATAM, Avianca, Copa Airlines")
    flight_class = models.CharField(
        max_length=20,
        choices=[('economy', 'Economy'), ('premium', 'Premium Economy'), ('business', 'Business')],
        default='economy'
    )

    template = "tours/tour_detail.html"


    content_panels = AbstractTourPage.content_panels + [
        MultiFieldPanel([
            FieldPanel('duration_days'),
            FieldPanel('nights'),
        ], heading="Duration"),

        MultiFieldPanel([
            FieldPanel('includes_international_flight'),
            FieldPanel('departure_cities'),
            FieldPanel('airline'),
            FieldPanel('flight_class'),
        ], heading="Flight Details", classname="collapsible"),
    ]

    parent_page_types = ['tours.ToursIndexPage']
    subpage_types = []

    def get_code_prefix(self):
        return "FT"  # FT = Full Tour

    class Meta:
        verbose_name = "Full Tour (with flights)"
        verbose_name_plural = "Full Tours"

class DayTourPage(AbstractTourPage):
    """
    Single-day or max 2-day tours from Cuenca.
    No hotel nights, no flights → pure experiences.
    """
    duration_hours = models.PositiveIntegerField(default=8, help_text="Duration in hours (e.g. 8–10)")
    start_time = models.TimeField(help_text="Usual departure time, e.g. 08:00")
    meeting_point = models.CharField(max_length=255, default="Milano Travel office - Cuenca", help_text="Where clients meet the guide")
    min_group_size = models.PositiveIntegerField(default=2, help_text="Minimum to operate the tour")
    max_group_size = models.PositiveIntegerField(default=15, help_text="Maximum per guide")

    template = "tours/tour_detail.html"

    content_panels = AbstractTourPage.content_panels + [
        MultiFieldPanel([
            FieldPanel('duration_hours'),
            FieldPanel('start_time'),
            FieldPanel('meeting_point'),
            FieldPanel('min_group_size'),
            FieldPanel('max_group_size'),
        ], heading="Day Tour Details", classname="collapsible"),
    ]

    parent_page_types = ['tours.ToursIndexPage']
    subpage_types = []

    def get_code_prefix(self):
        return "DT"  # DT = Day Tour

    class Meta:
        verbose_name = "Day Tour"
        verbose_name_plural = "Day Tours"
