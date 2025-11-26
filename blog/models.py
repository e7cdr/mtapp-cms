# blog/models.py
import readtime
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.search import index
from wagtail.snippets.models import register_snippet
from wagtailseo.models import SeoMixin
from wagtail.contrib.routable_page.models import RoutablePageMixin, route

from modelcluster.fields import ParentalKey
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase, Tag as TaggitTag

from wagtail.images import get_image_model
from wagtail.images.blocks import ImageChooserBlock
from wagtail import blocks

from wagtail_localize.fields import TranslatableField, SynchronizedField

from streams.blocks import TourTeaserBlock
from taggit.models import Tag
from django.db.models import Count


# ------------------------------------------------------------------
# Snippets
# ------------------------------------------------------------------
@register_snippet
class BlogCategory(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.ForeignKey('wagtailimages.Image', null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='+')

    panels = [FieldPanel('name'), FieldPanel('slug'), FieldPanel('icon')]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:50]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Blog Category"
        ordering = ['name']


@register_snippet
class BlogTag(TaggitTag):
    class Meta:
        verbose_name = "Blog Tag"
        verbose_name_plural = "Blog Tags"


class BlogDetailPageTag(TaggedItemBase):
    content_object = ParentalKey('BlogDetailPage', related_name='tagged_items', on_delete=models.CASCADE)


# ------------------------------------------------------------------
# THE MAGIC PAGE: BlogIndexPage with ALL routes
# ------------------------------------------------------------------
class BlogIndexPage(RoutablePageMixin, SeoMixin, Page):
    intro = RichTextField(blank=True, help_text="Shown on the main blog page")
    posts_per_page = models.PositiveIntegerField(default=12)

    subpage_types = ['blog.BlogDetailPage']
    max_count = 1

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('posts_per_page'),
    ]

    translated_fields = [
        TranslatableField('title'),
        TranslatableField('intro'),
        TranslatableField('seo_title'),
        TranslatableField('search_description'),
    ]

    # ------------------------------------------------------------------
    # Helper: pagination
    # ------------------------------------------------------------------
    def paginate(self, request, queryset):
        paginator = Paginator(queryset.order_by('-date_published'), self.posts_per_page)
        page = request.GET.get('page')
        try:
            return paginator.page(page)
        except PageNotAnInteger:
            return paginator.page(1)
        except EmptyPage:
            return paginator.page(paginator.num_pages)

    # ------------------------------------------------------------------
    # 1. Main blog index → /blog/
    # ------------------------------------------------------------------
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        
        posts = BlogDetailPage.objects.descendant_of(self).live().public().order_by('-date_published')

        # === FILTERS ===
        selected_category = None
        selected_tag = None
        selected_country = None

        # Category filter
        category_slug = request.GET.get('category')
        if category_slug:
            try:
                selected_category = BlogCategory.objects.get(slug=category_slug)
                posts = posts.filter(category=selected_category)
            except BlogCategory.DoesNotExist:
                pass

        # Tag filter
        tag_slug = request.GET.get('tag')
        if tag_slug:
            posts = posts.filter(tags__slug=tag_slug)
            selected_tag = tag_slug.replace('-', ' ').title()

        # Country filter
        country = request.GET.get('country')
        if country and country != 'all':
            posts = posts.filter(source_country=country)
            selected_country = country

        # Pagination
        context['posts'] = self.paginate(request, posts)
        context['selected_category'] = selected_category
        context['selected_tag'] = selected_tag
        context['selected_country'] = selected_country

        # For sidebar
        context['categories'] = BlogCategory.objects.annotate(
            count=models.Count('posts')
        ).filter(count__gt=0)
        
        context['popular_tags'] = Tag.objects.filter(
            blog_blogdetailpagetag_items__content_object__live=True
        ).annotate(
            post_count=Count('blog_blogdetailpagetag_items')
        ).order_by('-post_count')[:12]
        context['source_countries'] = dict(BlogDetailPage._meta.get_field('source_country').choices)

        return context

    # ------------------------------------------------------------------
    # 2. Tag view → /blog/tag/poland-travel/
    # ------------------------------------------------------------------
    @route(r'^tag/(?P<tag_slug>[\w-]+)/?$')
    def tag_view(self, request, tag_slug):
        posts = BlogDetailPage.objects.live().public().filter(tags__slug=tag_slug)
        return self.render(
            request,
            context_overrides={
                'current_tag': tag_slug.replace('-', ' ').title(),
                'posts': self.paginate(request, posts),
            },
            template="blog/blog_tag_index_page.html",
        )

    # ------------------------------------------------------------------
    # 3. Category view → /blog/category/winter-escape/
    # ------------------------------------------------------------------
    @route(r'^category/(?P<category_slug>[\w-]+)/?$')
    def category_view(self, request, category_slug):
        try:
            category = BlogCategory.objects.get(slug=category_slug)
        except BlogCategory.DoesNotExist:
            from django.http import Http404
            raise Http404("Category not found")

        posts = BlogDetailPage.objects.live().public().filter(category=category)
        return self.render(
            request,
            context_overrides={
                'current_category': category,
                'posts': self.paginate(request, posts),
            },
            template="blog/blog_category_index_page.html",
        )

    # ------------------------------------------------------------------
    # 4. Source-country hubs → /blog/from-poland/  etc.
    # ------------------------------------------------------------------
    SOURCE_COUNTRY_ROUTES = {
        'from-poland': 'poland',
        'from-iceland': 'iceland',
        'desde-colombia': 'colombia',
        'desde-republica-dominicana': 'dominican_republic',
    }

    @route(r'^(from-poland|from-iceland|desde-colombia|desde-republica-dominicana)/?$')
    def source_country_view(self, request, country_slug):
        country_key = self.SOURCE_COUNTRY_ROUTES[country_slug]
        pretty_name = dict(BlogDetailPage._meta.get_field('source_country').choices)[country_key]

        posts = BlogDetailPage.objects.live().public().filter(source_country=country_key)

        return self.render(
            request,
            context_overrides={
                'current_country': pretty_name,
                'country_slug': country_slug,
                'posts': self.paginate(request, posts),
            },
            template="blog/blog_source_country_index_page.html",
        )


# ------------------------------------------------------------------
# Individual blog post
# ------------------------------------------------------------------
class BlogDetailPage(SeoMixin, Page):
    intro = RichTextField(help_text="150–200 word teaser")
    body = StreamField([
        ('content', blocks.RichTextBlock(features=['bold', 'italic', 'h3', 'h4', 'ol', 'ul', 'hr', 'link', 'document-link', 'image', 'embed'])),
        ('tour_teaser', TourTeaserBlock()),
        ('faq', blocks.ListBlock(blocks.StructBlock([('q', blocks.CharBlock()), ('a', blocks.RichTextBlock())]), template="streams/faq.html")),
        ('cta', blocks.StructBlock([('text', blocks.CharBlock()), ('button', blocks.CharBlock())], template="streams/cta.html")),
    ], use_json_field=True, collapsed=False)

    banner_image = models.ForeignKey(get_image_model(), null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    date_published = models.DateField(default=timezone.now)
    source_country = models.CharField(max_length=100, choices=[
        ('poland', 'Poland'), ('iceland', 'Iceland'),
        ('dominican_republic', 'República Dominicana'), ('colombia', 'Colombia'),
        ('general', 'General')
    ], blank=True)
    category = models.ForeignKey(BlogCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='posts')
    tags = ClusterTaggableManager(through=BlogDetailPageTag, blank=True)

    @property
    def read_time(self):
        return readtime.of_html(self.body.render_as_block() or "")

    def get_read_time_display(self):
        rt = self.read_time
        minutes = rt.minutes if rt.minutes > 0 else 1
        return f"{minutes} min read"

    search_fields = Page.search_fields + [
        index.SearchField('intro'), index.SearchField('body'),
        index.FilterField('date_published'), index.FilterField('source_country'),
    ]

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('banner_image'),
        FieldPanel('body'),
        MultiFieldPanel([
            FieldPanel('date_published'),
            FieldPanel('source_country'),
            FieldPanel('category'),
            FieldPanel('tags'),
        ], "Metadata"),
    ]

    parent_page_types = ['blog.BlogIndexPage']

    translated_fields = [
        TranslatableField('title'),
        TranslatableField('intro'),
        TranslatableField('body'),
        TranslatableField('seo_title'),
        TranslatableField('search_description'),
    ]

    # These stay the same across languages (you don’t want separate banners per language usually)
    synchronized_fields = [
        SynchronizedField('banner_image'),
        SynchronizedField('date_published'),
        SynchronizedField('source_country'),
        SynchronizedField('category'),
        SynchronizedField('tags'),
    ]

    # Optional but recommended: make slug translatable too
    # (so /from-poland/ becomes /z-polski/ in Polish version)
    translate_fields = translated_fields + [TranslatableField('slug')]

    def get_jsonld_schema(self):
        # Safe for both RichTextField and CharField/TextField
        description = ""
        if self.intro:
            if hasattr(self.intro, 'source'):
                description = self.intro.source  # RichTextField
            else:
                description = str(self.intro)    # CharField/TextField

        return {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": self.title,
            "image": (
                self.banner_image.get_rendition("fill-1200x630").url
                if self.banner_image else ""
            ),
            "datePublished": self.date_published.isoformat(),
            "author": {"@type": "Organization", "name": "Milano Travel"},
            "publisher": {"@type": "Organization", "name": "Milano Travel"},
            "description": description,
        }
    
    # blog/models.py — add this method to BlogDetailPage class

    def get_faq_schema(self):
        """
        Works with ListBlock + StructBlock — 100% safe
        """
        faqs = []
        for block in self.body:
            if block.block_type == "faq":
                # ← matches your StreamField name
                # block.value is ListValue → iterate directly
                for item in block.value:
                    question = item.get("q") or item.get("question", "")
                    answer = item.get("a") or item.get("answer")
                    if question and answer:
                        answer_text = (
                            "".join(answer.__html__().splitlines())
                            if hasattr(answer, "__html__")
                            else str(answer)
                        )
                        faqs.append({
                            "@type": "Question",
                            "name": question,
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": answer_text.strip()
                            }
                        })
        
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faqs
        } if faqs else None
    
