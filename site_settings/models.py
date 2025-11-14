from django.db import models
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField


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

@register_setting
class BrandSettings(BaseGenericSetting):
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
    panels = [
        FieldPanel('company_name'),
        FieldPanel('logo'),
        FieldPanel('address'),
        FieldPanel('telephone'),
    ]

    class Meta:
        verbose_name = "Brand Settings"

    def __str__(self):
        return self.company_name