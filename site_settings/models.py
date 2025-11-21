from django.db import models
from wagtail.models import Orderable
from wagtail.fields import RichTextField
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting


@register_setting # Decorator to register the setting with Wagtail
class FooterLinks(BaseGenericSetting): # Inherit from BaseGenericSetting to create a generic setting
    """Model to store footer social media links."""
    x_tw = models.URLField(blank=True, null=True, verbose_name="X URL")
    facebook = models.URLField(blank=True, null=True, verbose_name="Facebook URL")
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram URL")
    tik_tok = models.URLField(blank=True, null=True, verbose_name="TikTok URL")
    youtube = models.URLField(blank=True, null=True, verbose_name="YouTube URL")
    whatsapp = models.URLField(blank=True, null=True, verbose_name="WhatsApp URL", max_length=310)

    panels = [
        FieldPanel('x_tw'),
        FieldPanel('facebook'),
        FieldPanel('instagram'),
        FieldPanel('tik_tok'),
        FieldPanel('youtube'),
        FieldPanel('whatsapp'),

    ]

    class Meta:
        verbose_name = "Footer Links"

    def __str__(self):
        return "Footer Links Settings"


# Inline model – one row per footer link
class FooterMenuLink(Orderable):
    setting = ParentalKey("BrandSettings", related_name="footer_menu_links")
    page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    custom_url = models.URLField(
        blank=True,
        help_text="Use this if you want an external link instead of a Wagtail page"
    )
    title_override = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional: override the page title (e.g. 'Get in Touch')"
    )

    panels = [
        FieldPanel("page"),
        FieldPanel("custom_url"),
        FieldPanel("title_override"),
    ]

    def __str__(self):
        return self.title_override or (self.page.title if self.page else "External link")

    @property
    def url(self):
        return self.custom_url or (self.page.localized.url if self.page else "#")

    @property
    def title(self):
        return self.title_override or (self.page.localized.title if self.page else "Link")


@register_setting
class BrandSettings(BaseGenericSetting, ClusterableModel):
    """Model to store brand settings like logo and company name."""
    company_name = models.CharField(max_length=300, blank=False, null=False, default='Milano Travel')
    logo = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Company Logo"
    )
    address = RichTextField(blank=True, null=True, default="Honorato Vasquez")
    telephone = models.CharField(max_length=20, blank=False, null=False, default='+593')
    search_suggestion = RichTextField(blank=True, null=True, default="Don't know what to look for? Try >>[Insert Link]")
    footer_background = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Footer Background"
    )

    panels = [
        FieldPanel('logo'),
        FieldPanel('footer_background'),
        FieldPanel('company_name'),
        FieldPanel('address'),
        FieldPanel('telephone'),
        FieldPanel('search_suggestion'),
        InlinePanel("footer_menu_links", label="Footer Menu Links"),  # ← NEW
    ]

    class Meta:
        verbose_name = "Brand Settings" 

    def __str__(self):
        return self.company_name