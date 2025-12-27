# home/models.py
from django.db import models
from wagtailseo.models import SeoMixin
from wagtail.models import Page, Site
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, PageChooserPanel
from wagtailcache.cache import WagtailCacheMixin

from streams import blocks


class HomePage(WagtailCacheMixin, SeoMixin, Page):
    """Home page model."""
    templates = "home/home_page.html"
        

    banner_title = models.CharField(max_length=100, blank=False, null=True)
    banner_subtitle = RichTextField(features=["bold", "italic"], blank=True, null=True)
    banner_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    banner_cta = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
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
        [("carousel", blocks.FadeCarousel())],
        blank=True,
        null=True,
        max_num=1,
        use_json_field=True,
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
        use_json_field=True,
        block_counts={"ParallaxImageBlock": {"max_num": 1}},
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
        from django.apps import apps                     # ← lazy import here
        BlogIndexPage = apps.get_model('blog.BlogIndexPage')
        BlogDetailPage = apps.get_model('blog.BlogDetailPage')

        context = super().get_context(request)
        context['carousel'] = self.carousel

        try:
            context['blog_page'] = BlogIndexPage.objects.live().first()
        except:
            context['blog_page'] = None

        if self.include_latest_blog_posts:
            context['latest_blog_posts'] = BlogDetailPage.objects.live().public().order_by('-date_published').filter(locale=self.locale).specific()[:6]
        else:
            context['latest_blog_posts'] = None

        return context


class SitemapPage(Page):
    content_panels = Page.content_panels

    def get_context(self, request):
        context = super().get_context(request)

        site = Site.find_for_request(request)
        root = site.root_page.specific.localized
        context['pages'] = root.get_children().live().public()

        try:
            sitemap_page = SitemapPage.objects.live().public().first()
            context['sitemap_page'] = sitemap_page.localized if sitemap_page else None
        except:
            context['sitemap_page'] = None

        return context

    class Meta:
        verbose_name = "Sitemap"