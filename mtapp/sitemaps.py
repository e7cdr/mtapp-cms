from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from django.urls import reverse
from wagtail.models import Page
from wagtail.images import get_image_model


class PageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Page.objects.live().public()

    def location(self, obj):
        # This is the ONLY way that works reliably in sitemap context
        return obj.relative_url(Site.objects.get_current())

    def lastmod(self, obj):
        return obj.last_published_at


class ImageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return get_image_model().objects.all()

    def location(self, obj):
        # Images don't have relative_url() → use the file URL directly
        return obj.file.url  # This is already absolute: /media/images/photo.jpg