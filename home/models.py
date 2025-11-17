from streams import blocks
from django.db import models

from wagtailseo.models import SeoMixin
from wagtail.models import Page, Locale, Site
from django.utils.translation import get_language  # For current language code from request
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, PageChooserPanel

class HomePage(SeoMixin, Page):
    """Home page model."""
    templates = "home/home_page.html"

    """Limit the number of HomePage instances to one."""
    max_count = 1

    """Title for the banner section on the home page. This field is required and cannot be blank."""
    banner_title = models.CharField(max_length=100, blank=False, null=True)
    banner_subtitle = RichTextField(features=["bold", "italic"], blank=True, null=True)
    banner_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True, # True Because HomePage is the first page, it can be created without an image.
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+", # No reverse relation from Image to HomePage.
    )
    banner_cta = models.ForeignKey(
        "wagtailcore.Page",
        null=True, # True because the button is optional.
        blank=True, # True because the button is optional.
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Choose a page to link to from the banner button.",
    )

    carousel = StreamField(
        [("carousel", blocks.CarouselBlock())], # A StreamField containing a single CarouselBlock.
        blank=True,
        null=True,
        max_num=1,
        use_json_field=True,
        help_text="Add images to the carousel. Each image can have an optional caption and link.",
    )

    content = StreamField(
        [
            ("explore_block", blocks.ExploreBlock()),
            ("video_text_content", blocks.Video_Text_Block()),
            ("text_band", blocks.TextBand_Block()),
            ("swipers", blocks.Swipers()),
            ("cta_2B", blocks.CTA_Block_2B()),


        ],
        null=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel('banner_title'),
        FieldPanel('banner_subtitle'),
        FieldPanel('banner_image'),
        PageChooserPanel('banner_cta'),
        FieldPanel('carousel'),
        FieldPanel('content'),
    ]

    promote_panels = SeoMixin.seo_panels

    class Meta:
        verbose_name = "Home Page"
        verbose_name_plural = "Home Pages"

    def get_context(self, request):
        """Add additional context variables to the template."""
        context = super().get_context(request)
        context['carousel'] = self.carousel # Access the StreamField directly. First 'For' loop in template will be {% for block in carousel %}

        return context
    


class SitemapPage(Page):
    content_panels = Page.content_panels

    def get_context(self, request):
        context = super().get_context(request)
        
        # Get site and its localized root (English Home for /en/)
        site = Site.find_for_request(request)
        root = site.root_page.specific.localized  # Key: .localized gets current locale version
        
        # Simplified query: Children of localized root (already English-scoped)
        context['pages'] = (
            root.get_children()
            .live()
            .public()
            # .in_menu()  # Comment out first to test all pages; uncomment for nav-only
        )
        
        # Debug: Console on load (remove after)
        language_code = get_language()
        print(f"Sitemap debug - Lang: {language_code}, Root title: {root.title}, Pages count: {context['pages'].count()}")
        if context['pages'].count() == 0:
            print("Debug tip: Check if root has published children in this locale.")
        
        return context

    class Meta:
        verbose_name = "Sitemap"