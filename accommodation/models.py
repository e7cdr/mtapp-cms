from venv import logger
from django.db import models

from django.forms import ValidationError
from wagtail.models import Page

from mtapp.utils import generate_code_id
from streams import blocks
from tours.models import DESTINATION_CHOICES


class BaseDistribution(Page):
    # Common content fields
    name = models.CharField(max_length=200, help_text=_("e.g., 'Cuenca Cultural Getaway'"))
    destination = models.CharField(
        max_length=100,
        choices=DESTINATION_CHOICES,
        default="Ecuador",
        help_text=_("Select the destination country.")
    )
    description = models.TextField(help_text=_("Description of the tour."))
    location = models.CharField(max_length=30, help_text=_('Location inside the country'))
    cover_page_content = models.TextField(blank=True, help_text=_("Content for the tour's cover page."))
    general_info = models.TextField(blank=True, help_text=_("General info like cancellation policy, inclusions."))
    final_message = models.TextField(blank=True, help_text=_("Final message from the travel company."))
    courtesies = models.TextField(default="Tour guiado por la ciudad", help_text=_("Tour inclusions"), blank=True)
    is_company_acc = models.BooleanField(
        default=False,
        help_text=_("If True, skip supplier confirmation and go direct to payment (company-run tour).")
    )

    amenity = StreamField([
        ('include', ListBlock(ChoiceBlock(choices=blocks.GLOBAL_ICON_CHOICES)))
    ], blank=True, use_json_field=True, help_text=_("Add as many amenities."))

    no_inclusions = models.TextField(default="Ticket aéreo", help_text=_("Not included"), blank=True)
    additional_notes = models.TextField(
        default="Sujeto a disponibilidad. Consultar suplementos para festivos.", blank=True
    )

    # Flags: TODO Custom validation, if sold out, none of the others can be on
    is_on_discount = models.BooleanField(default=False)
    is_special_offer = models.BooleanField(default=False)
    is_sold_out = models.BooleanField(default=False)
    is_all_inclusive = models.BooleanField(default=False)
    price_subtext = models.CharField(default="Estimated", help_text="Estimated. IVA not included", max_length=30)

    # Codes
    ref_code = models.CharField(max_length=20, blank=True, null=True)
    code_id = models.CharField(max_length=15, editable=False)

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
        Document, on_delete=models.SET_NULL, null=True, blank=True,
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
        help_text="Comma-separated days (0=Sunday, 1=Monday..., 6=Saturday), e.g., '0,1,2,3'"
    )

    # Supplier & Pricing (common)
    pricing_type = models.CharField(
        max_length=20,
        choices=[('Per_room', 'Per Room'), ('Per_person', 'Per Person')],
        default='Per_person'
    )
    max_children_per_room = models.PositiveIntegerField(default=1)
    child_age_min = models.PositiveIntegerField(default=7)
    child_age_max = models.PositiveIntegerField(default=12)
    price_sgl = models.DecimalField(max_digits=10, decimal_places=2)
    price_dbl = models.DecimalField(max_digits=10, decimal_places=2)
    price_tpl = models.DecimalField(max_digits=10, decimal_places=2)

    price_adult = models.DecimalField(max_digits=10, decimal_places=2)
    price_chd = models.DecimalField(max_digits=10, decimal_places=2)
    price_inf = models.DecimalField(max_digits=10, decimal_places=2)
    seasonal_factor = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
    demand_factor = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    yt_vid = models.URLField(default='www.none.com', help_text=_("This video will be shown in the Tours Watch Video."))
    max_capacity = models.PositiveIntegerField(default=20)
    available_slots = models.PositiveIntegerField(default=20)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Shared panels (extend in children)
    content_panels = Page.content_panels + [

        MultiFieldPanel([
            FieldPanel('name'),
            FieldPanel('destination'),
            FieldPanel('description'),
            FieldPanel('location'),
            FieldPanel('cover_page_content'),
            FieldPanel('general_info'),
            FieldPanel('final_message'),
            FieldPanel('courtesies'),
            FieldPanel('amenity'),
            FieldPanel('no_inclusions'),
            FieldPanel('additional_notes'),
        ], heading="Content Fields"),
        MultiFieldPanel([
            FieldPanel('is_on_discount'),
            FieldPanel('is_special_offer'),
            FieldPanel('is_all_inclusive'),
            FieldPanel('is_sold_out'),
        ], heading="Current State"),

        MultiFieldPanel([
            FieldPanel('image'),
            FieldPanel('cover_image'),
            FieldPanel('logo_image'),
            FieldPanel('pdf_file'),
            FieldPanel('pdf_images'),
            FieldPanel('yt_vid'),
        ], heading="Media"),
        MultiFieldPanel([
                FieldPanel('pricing_type'),
                MultiFieldPanel([
                    FieldPanel('price_sgl'),
                    FieldPanel('price_dbl'),
                    FieldPanel('price_tpl'),
        ], heading="Prices Per Room"),
                MultiFieldPanel([
                    FieldPanel('price_adult'),
                    FieldPanel('price_chd'),
                    FieldPanel('price_inf'),
                    FieldPanel('max_children_per_room'),
        ], heading="Prices Per Person (If per room, DON't fill ADULT PRICE)"),
            MultiFieldPanel([
                FieldPanel('price_subtext'),
                FieldPanel('seasonal_factor'),
                FieldPanel('demand_factor'),
            ],heading="Factors"),
        ], heading="Price & Comm"),


        FieldPanel('ref_code'),
        FieldPanel('code_id', read_only=True),
        FieldPanel('supplier_email'),
        FieldPanel('is_company_acc'),
        MultiFieldPanel([
            FieldPanel('max_capacity'),
            FieldPanel('available_slots'),
            FieldPanel('itinerary'),
            FieldPanel('start_date'),
            FieldPanel('end_date'),
            FieldPanel('available_days'),
            FieldPanel('child_age_min'),
            FieldPanel('child_age_max'),
        ], heading="Tour Configuration"),

    ]


    template = "tours/tour_detail.html"


    class Meta:
        abstract = True  # Key: No DB table
        unique_together = [('locale', 'code_id', 'ref_code')]


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
        return context

    def clean(self):
        super().clean()
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
                    super().save(update_fields=['pdf_images'])
                logger.info(f"Generated {len(self.pdf_images)} images for tour {self.id}")
            except Exception as e:
                logger.error(f"Failed to convert PDF for tour {self.id}: {str(e)}")
                self.pdf_images = []
                super().save(update_fields=['pdf_images'])
        else:
            self.pdf_images = []
            super().save(update_fields=['pdf_images'])

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

    def __str__(self):
        return self.title or self.name or 'Untitled Acc'

