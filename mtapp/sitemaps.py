from wagtail.models import Page
from wagtail.images import get_image_model
from django.contrib.sitemaps import Sitemap

class PageSitemap(Sitemap):
    changefreq = "weekly"  # How often pages change: daily/weekly/monthly/always/never
    priority = 0.9  # 0.0 to 1.0; higher = more important

    def items(self):
        # Only live, public pages (excludes drafts)
        return Page.objects.live().public()

    def location(self, obj):
        return obj.full_url  # Full URL, e.g., https://yoursite.com/blog/post-1

    def lastmod(self, obj):
        return obj.latest_revision_created_at  # Last publish date

    # def changefreq(self, obj):
    #     # Customize per page type, e.g., blog posts change more often
    #     if obj.specific_class and issubclass(obj.specific_class, BlogPage):
    #         return "daily"
    #     return super().changefreq

class ImageSitemap(Sitemap):
    # ... similar setup, but items() returns Image objects
    def items(self):
        return get_image_model().objects.all()

    def location(self, obj):
        return obj.file.url