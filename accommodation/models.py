from datetime import datetime, timedelta
from decimal import Decimal
import os
from venv import logger
from django.conf import settings
from django.db import models
from wagtailseo.models import SeoMixin

from django.forms import ValidationError
from wagtail.models import Page

from mtapp.choices import GLOBAL_ICON_CHOICES, DESTINATION_CHOICES
from mtapp.utils import convert_pdf_to_images, generate_code_id
from mtapp.utils_blocks import PricingTierBlock
from streams import blocks
from django.utils.translation import gettext_lazy as _
from wagtail.images.models import Image
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from django.db import models
from django.http import HttpRequest
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.fields import RichTextField, StreamField
from wagtail.search import index
from django.db.models import Q
from wagtail.blocks import (
    StructBlock,
    RichTextBlock,
    ListBlock,
    ChoiceBlock,
    IntegerBlock,
    DateBlock,
)

class AbstractAccommodationPage(SeoMixin, Page):
    # Common content fields
    name = models.CharField(max_length=200, help_text=_("e.g., 'Cuenca Cultural Getaway'"))
    destination = models.CharField(
        max_length=100,
        choices=DESTINATION_CHOICES,
        default="Ecuador",
        help_text=_("Select the destination country.")
    )
    description = RichTextField(help_text=_("Description of the accommodation."))
    location = models.CharField(max_length=30, help_text=_('Location inside the country'))
    cover_page_content = RichTextField(blank=True, help_text=_("Content for the accommodation's cover page in the PDF Generator."))
    general_info = RichTextField(blank=True, help_text=_("General info like cancellation policy, inclusions in the PDF Generator."))
    final_message = RichTextField(blank=True, help_text=_("Final message from the travel company in the PDF Generator. "))
    courtesies = RichTextField(default="Guided city accommodation", help_text=_("Accommodation inclusions"), blank=True)
    cxl_policies = RichTextField(blank=True, null=True, default="", verbose_name="Cancellation Policies")
    disclaimer = RichTextField(blank=True, null=True, default="", verbose_name="Disclaimer Message (Accommodations Details)", help_text="For example: All prices are subject to availability")

    amenity = StreamField([
        ('include', ListBlock(ChoiceBlock(choices=GLOBAL_ICON_CHOICES)))
    ], blank=True, use_json_field=True, help_text=_("Add as many amenities."))

    no_inclusions = RichTextField(default="Air Ticket", help_text=_("Not included"), blank=True)
    additional_notes = RichTextField(
                default="Subject to availability", blank=True
    )
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
        help_text="""This is the Referal Code. This is used for referencing a third party accommodation. Most of the time,
        large accommodation operators have their own accommodation code, so this field can be used to reference by that code so it is easy to find it in large databases.
                """
        )
    code_id = models.CharField(max_length=15, editable=False, help_text="This is the Accommodations unique internal ID. Other companies might use this code as reference. Without this ID, it would be impossible to render the accommodations.")

    # Media
    image = models.ForeignKey(
        Image, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(app_label)s_%(class)s_image'
    )
    cover_image = models.ForeignKey(
        Image, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(app_label)s_%(class)s_cover',
        help_text=_("Image for the accommodation's cover page.")
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
    supplier_email = models.EmailField(blank=True, help_text=_("Supplier contact email. If This is a in House/company accommodation, check the next box and skip this email field."))
    is_company_accom = models.BooleanField(
        default=False,
        help_text=_("If True, skip supplier confirmation and go direct to payment (company-run accommodation).")
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
        help_text="Combined = adult pays base price, gets discount when sharing room. Best for private accommodations."
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
    pricing_table = models.BooleanField(verbose_name="Enable Pricing Table in Accommodation Details", default=False)
    show_prices_in_table = RichTextField(
        blank=True,
        null=True,
        help_text="If filled, replaces the entire pricing table with this message in the Accommodations Detail page."
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
    yt_vid = models.CharField(max_length=22, default='', help_text=_("For example: https://www.youtube.com/watch?v=UHLdLtEiFGs >> ID = UHLdLtEiFGs. This video will be shown in the Accommodations Watch Video."), verbose_name="Youtube Video ID")
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
            FieldPanel('courtesies'),
            FieldPanel('amenity'),
            FieldPanel('no_inclusions'),
            FieldPanel('additional_notes'),
            FieldPanel('cxl_policies'),
            FieldPanel('supplier_email'),
            FieldPanel('is_company_accom'),
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
        ], heading="Accommodation Configuration", classname="collapsible collapsed"),

        # ─── CURRENT STATE ───
        MultiFieldPanel([
            FieldPanel('is_on_discount'),
            FieldPanel('is_special_offer'),
            FieldPanel('is_all_inclusive'),
            FieldPanel('is_sold_out'),
        ], heading="Accommodation Status", classname="collapsible collapsed"),
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



    template = "accommodation/accommodation_detail.html"


    class Meta:
        abstract = True  # Key: No DB table
        unique_together = [('locale', 'code_id', 'ref_code')]

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
        if self.code_id:
                # Check for duplicate code_id in the same locale
                duplicates = self.__class__.objects.filter(
                    locale=self.locale,
                    code_id=self.code_id
                ).exclude(pk=self.pk)

                if duplicates.exists():
                    # Extremely rare, but handle gracefully
                    self.code_id = generate_code_id(self.get_code_prefix())
                    # Optionally log or notify
                    # logger.warning(f"Duplicate code_id detected, regenerated: {self.code_id}")

        if not self.code_id:
            self.code_id = generate_code_id(self.get_code_prefix())            # No while loop here—let per-locale validation handle conflicts

        # Per-locale uniqueness checks (allows sharing across locales)
        if self.code_id:
            existing = self.__class__.objects.filter(
                locale=self.locale,
                code_id=self.code_id
            ).exclude(id=self.id)
            if existing.exists():
                raise ValidationError('Accommodation with this Code ID already exists in this locale.')

        if self.ref_code:  # Assuming ref_code also shared; adjust if unique globally
            existing = self.__class__.objects.filter(
                locale=self.locale,
                ref_code=self.ref_code
            ).exclude(id=self.id)
            if existing.exists():
                raise ValidationError('Accommodation with this Ref Code already exists in this locale.')

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
            output_dir = os.path.join(settings.MEDIA_ROOT, f'accommodation_{self.id}_pdf_images')
            pdf_path = self.pdf_file.file.path
            try:
                image_paths = convert_pdf_to_images(pdf_path, output_dir, self.id)
                if image_paths != self.pdf_images:
                    self.pdf_images = image_paths
                    # super().save(update_fields=['pdf_images'])
                logger.info(f"Generated {len(self.pdf_images)} images for accommodation {self.id}")
            except Exception as e:
                logger.error(f"Failed to convert PDF for accommodation {self.id}: {str(e)}")
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
    
    # accommodations/models.py — add inside AbstractAccommodationPage class (near the bottom)

    def get_jsonld_schema(self):
        """
        100% safe AccommodationistTrip JSON-LD — works on ALL accommodation types
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
                        "@type": "AccommodationistAttraction",
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
            "@type": "Accommodation",
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

        # Remove empty values
        return {k: v for k, v in schema.items() if v not in (None, "", [], {})}

    def __str__(self):
        return self.title or self.name or 'Untitled Accommodation'

class AccommodationsIndexPage(SeoMixin, RoutablePageMixin, Page):
    intro = RichTextField(
        blank=True,
        help_text=_("Introduction text shown above the accommodation grid")
    )
    body_content = StreamField([
        ("text_band", blocks.TextBand_Block()),
        ("flex_images", blocks.Flex_Images_Block()),
        ("swipers", blocks.Swipers()),
        ("explore_block", blocks.ExploreBlock()),
        ("video_text_content", blocks.Video_Text_Block()),
        ("cta_2B", blocks.CTA_Block_2B()),
    ], blank=True, use_json_field=True)

    # Only one index page allowed
    max_count = 1

    template = "accommodation/accommodation_index_page.html"

    parent_page_types = ['home.HomePage']
    subpage_types = [
        'accommodation.GlampingPage',
        'accommodation.CabinPage',
        'accommodation.HostelPage',
        'accommodation.CampsitePage',
        'accommodation.HotelRoomPage',
        # Add more as you create them!
    ]

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body_content'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
    ]

    class Meta:
        verbose_name = "Accommodations Index Page"

    def get_accommodation_models(self):
        return [
            model for model in AbstractAccommodationPage.__subclasses__()
            if not model._meta.abstract
        ]

    def get_context(self, request: HttpRequest):
        context = super().get_context(request)

        # Start with only Cabin for now — like tours only has LandTourPage
        Model = CabinPage
        acc_type = request.GET.get('type', '').lower()

        # If type is selected and it's a valid one → switch model
        type_map = {
            'glamping': GlampingPage,
            'cabin': CabinPage,
            'hostel': HostelPage,
            'campsite': CampsitePage,
            'hotel': HotelRoomPage,
        }

        if acc_type in type_map:
            Model = type_map[acc_type]

        # Base queryset — only one model (like tours)
        qs = Model.objects.live().public().specific()

        # Apply filters
        if request.GET.get('destination'):
            qs = qs.filter(destination=request.GET['destination'])
        if request.GET.get('status') == 'discount':
            qs = qs.filter(is_on_discount=True)
        if request.GET.get('status') == 'special':
            qs = qs.filter(is_special_offer=True)
        if request.GET.get('status') == 'soldout':
            qs = qs.filter(is_sold_out=True)
        if request.GET.get('pricing_type'):
            qs = qs.filter(pricing_type=request.GET['pricing_type'])

        # Price filters
        if request.GET.get('min_price'):
            try: val = Decimal(request.GET['min_price'])
            except: val = 0
            qs = qs.filter(Q(price_dbl__gte=val) | Q(price_adult__gte=val))
        if request.GET.get('max_price'):
            try: val = Decimal(request.GET['max_price'])
            except: val = 999999
            qs = qs.filter(Q(price_dbl__lte=val) | Q(price_adult__lte=val))

        # Destinations from ALL models (for the filter dropdown)
        all_models = [GlampingPage, CabinPage, HostelPage, CampsitePage, HotelRoomPage]
        destinations = set()
        for m in all_models:
            destinations.update(
                m.objects.live().public()
                .exclude(destination='').values_list('destination', flat=True).distinct()
            )
        unique_destinations = sorted(destinations)

        # Pagination
        paginator = Paginator(qs.order_by('-start_date'), 12)
        page = paginator.get_page(request.GET.get('page', 1))

        context.update({
            'accommodations_pag': page,
            'unique_destinations': unique_destinations,
            'active_filters': request.GET,
            'GLOBAL_ICON_CHOICES': blocks.GLOBAL_ICON_CHOICES,
        })

        return context
    @route(r'^(glamping|cabins|hostels|campsites|hotels)/$')
    def accommodations_by_type(self, request, type_slug=None):
        type_map = {
            'glamping': 'glamping',
            'cabins': 'cabin',
            'hostels': 'hostel',
            'campsites': 'campsite',
            'hotels': 'hotel',
        }
        if type_slug in type_map:
            new_get = request.GET.copy()
            new_get['type'] = type_map[type_slug]
            request.GET = new_get
        return self.render(request)
        
class GlampingPage(AbstractAccommodationPage):

    parent_page_types = ['accommodation.AccommodationsIndexPage']
    template = 'accommodation/accommodation_detail.html'

    class Meta:
        verbose_name = "Glamping"
        verbose_name_plural = "Glampings"

    # Optional: extra glamping-specific fields
    tent_type = models.CharField(
        max_length=100, blank=True,
        choices=[
            ('dome', 'Geodesic Dome'),
            ('safari', 'Safari Tent'),
            ('bell', 'Bell Tent'),
            ('yurt', 'Yurt'),
            ('treehouse', 'Treehouse'),
        ],
        help_text=_("Type of glamping unit")
    )
    has_private_bathroom = models.BooleanField(default=True)
    max_glampers_per_unit = models.PositiveIntegerField(default=4)

    # Override panels to add glamping extras at the top
    content_panels = AbstractAccommodationPage.content_panels + [
        MultiFieldPanel([
            FieldPanel('tent_type'),
            FieldPanel('has_private_bathroom'),
            FieldPanel('max_glampers_per_unit'),
        ], heading="Glamping Specifics", classname="collapsible collapsed"),
    ]

    def get_code_prefix(self):
        return "GL"

class CabinPage(AbstractAccommodationPage):
    parent_page_types = ['accommodation.AccommodationsIndexPage']
    template = 'accommodation/accommodation_detail.html'
    class Meta:
        verbose_name = "Cabin"
        verbose_name_plural = "Cabins"

    bedrooms = models.PositiveSmallIntegerField(default=1)
    has_fireplace = models.BooleanField(default=False)
    lake_view = models.BooleanField(default=False, verbose_name="Lake/Mountain View")

    content_panels = AbstractAccommodationPage.content_panels + [
        MultiFieldPanel([
            FieldPanel('bedrooms'),
            FieldPanel('has_fireplace'),
            FieldPanel('lake_view'),
        ], heading="Cabin Details", classname="collapsible collapsed"),
    ]

    def get_code_prefix(self):
        return "CB"

class HostelPage(AbstractAccommodationPage):
    parent_page_types = ['accommodation.AccommodationsIndexPage']
    template = 'accommodation/accommodation_detail.html'

    class Meta:
        verbose_name = "Hostel"
        verbose_name_plural = "Hostels"

    dorm_beds = models.PositiveSmallIntegerField(default=8, help_text="Total beds in dorms")
    has_private_rooms = models.BooleanField(default=False)
    common_kitchen = models.BooleanField(default=True)
    free_breakfast = models.BooleanField(default=False)

    content_panels = AbstractAccommodationPage.content_panels + [
        MultiFieldPanel([
            FieldPanel('dorm_beds'),
            FieldPanel('has_private_rooms'),
            FieldPanel('common_kitchen'),
            FieldPanel('free_breakfast'),
        ], heading="Hostel Facilities", classname="collapsible collapsed"),
    ]

    def get_code_prefix(self):
        return "HS"

class CampsitePage(AbstractAccommodationPage):
    parent_page_types = ['accommodation.AccommodationsIndexPage']
    template = 'accommodation/accommodation_detail.html'

    class Meta:
        verbose_name = "Campsite"
        verbose_name_plural = "Campsites"

    pitch_size_sqm = models.PositiveSmallIntegerField(default=50, help_text="Average pitch size in m²")
    electricity_hookups = models.BooleanField(default=False)
    car_accessible = models.BooleanField(default=True)
    shower_block = models.BooleanField(default=True)

    content_panels = AbstractAccommodationPage.content_panels + [
        MultiFieldPanel([
            FieldPanel('pitch_size_sqm'),
            FieldPanel('electricity_hookups'),
            FieldPanel('car_accessible'),
            FieldPanel('shower_block'),
        ], heading="Campsite Features", classname="collapsible collapsed"),
    ]

    def get_code_prefix(self):
        return "CS"

class HotelRoomPage(AbstractAccommodationPage):
    """Classic hotel room – most common"""
    parent_page_types = ['accommodation.AccommodationsIndexPage']
    template = 'accommodation/accommodation_detail.html'

    class Meta:
        verbose_name = "Hotel Room"
        verbose_name_plural = "Hotel Rooms"

    room_category = models.CharField(
        max_length=50,
        choices=[
            ('standard', 'Standard'),
            ('superior', 'Superior'),
            ('deluxe', 'Deluxe'),
            ('suite', 'Suite'),
            ('junior_suite', 'Junior Suite'),
        ],
        default='standard'
    )
    floor = models.PositiveSmallIntegerField(blank=True, null=True)
    view_type = models.CharField(max_length=50, blank=True)

    content_panels = AbstractAccommodationPage.content_panels + [
        MultiFieldPanel([
            FieldPanel('room_category'),
            FieldPanel('floor'),
            FieldPanel('view_type'),
        ], heading="Room Category", classname="collapsible collapsed"),
    ]

    def get_code_prefix(self):
        return "HR"  # Hotel Room

