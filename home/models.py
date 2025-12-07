from blog.models import BlogDetailPage, BlogIndexPage
from streams import blocks
from django.db import models

from wagtailseo.models import SeoMixin
from wagtail.models import Page, Site
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, PageChooserPanel
from wagtailcache.cache import WagtailCacheMixin

class HomePage(WagtailCacheMixin, SeoMixin, Page):
    """Home page model."""
    templates = "home/home_page.html"

    """Limit the number of HomePage instances to one."""
    max_count = 1

    """Title for the banner section on the home page. This field is required and cannot be blank."""
    banner_title = models.CharField(max_length=100, blank=False, null=True)
    banner_subtitle = RichTextField(features=["bold", "italic"], blank=True, null=True)
    banner_image = models.ForeignKey(
        'wagtailimages.Image',
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

    include_latest_blog_posts = models.BooleanField(
        default=False,
        help_text="If checked, latest blog posts will be included in home page.",
        verbose_name="Include Blog Posts Component",
    )
    carousel = StreamField(
        [("carousel", blocks.FadeCarousel())], # A StreamField containing a single CarouselBlock.
        blank=True,
        null=True,
        max_num=1,
        use_json_field=True,
        help_text="Add images to the fade carousel. Each image can have an optional caption and link.",
    )

    content = StreamField(
        [
            ("explore_block", blocks.ExploreBlock()),
            ("video_text_content", blocks.Video_Text_Block()),
            ("text_band", blocks.TextBand_Block()),
            ("swipers", blocks.Swipers()),
            ("cta_2B", blocks.CTA_Block_2B()),
            ("ParallaxImageBlock", blocks.ParallaxImageBlock()),
            ("gridded_images", blocks.GriddedImages()),
            ('faq', blocks.FAQBlock()),


        ],
        null=True,
        blank=True,
        block_counts={
        "ParallaxImageBlock": {
            "max_num": 1,
            # "min_num": 1,   # uncomment if you want it required
        },
        # you can add more limits here, e.g.
        # "swipers": {"max_num": 3},
    },
    )

    content_panels = Page.content_panels + [
        FieldPanel('banner_title'),
        FieldPanel('banner_subtitle'),
        FieldPanel('banner_image'),
        PageChooserPanel('banner_cta'),
        FieldPanel('carousel'),
        FieldPanel('content'),
        FieldPanel('include_latest_blog_posts'),
    ]

    promote_panels = SeoMixin.seo_panels

    class Meta:
        verbose_name = "Home Page"
        verbose_name_plural = "Home Pages"

    def get_context(self, request):
        context = super().get_context(request)

        context['carousel'] = self.carousel
        try:
                context['blog_page'] = BlogIndexPage.objects.live().first()
                # or: BlogIndexPage.objects.get()  # will raise if not exist
        except BlogIndexPage.DoesNotExist:
                context['blog_page'] = None
        # Only fetch blog posts if the checkbox is checked
        if self.include_latest_blog_posts:
            context['latest_blog_posts'] = BlogDetailPage.objects.live().public().order_by('-date_published')[:6]
        else:
            context['latest_blog_posts'] = None  # or just don't set it

        return context


class SitemapPage(Page):
    content_panels = Page.content_panels

    def get_context(self, request):
            context = super().get_context(request)

            # Get site and localized root
            site = Site.find_for_request(request)
            root = site.root_page.specific.localized

            # All top-level pages for the sitemap tree
            context['pages'] = root.get_children().live().public()

            # NEW: Make the Sitemap page itself available in context everywhere
            # This finds the current locale's SitemapPage (or falls back gracefully)
            try:
                sitemap_page = SitemapPage.objects.live().public().first()
                if sitemap_page:
                    context['sitemap_page'] = sitemap_page.localized  # respects /en/, /es/, etc.
            except:
                context['sitemap_page'] = None

            return context

    class Meta:
        verbose_name = "Sitemap"