"""
The Flex app was created to manage flexible content types and streamfields.
It contains models and blocks that can be reused across different pages in the project (for example, blocks from streams/blocks.py).
This helps to keep the code DRY (Don't Repeat Yourself) and makes it easier to maintain and update the content structure of the website.
It also allows for more dynamic and customizable page layouts, as content editors can mix and match different blocks to create unique 
pages without needing to create new models for each layout variation.

These blocks will appear in the StreamField options when creating or editing pages that use them (At the end of the admin page).

"""

from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page

from streams import blocks

# Create your models here.

class FlexPage(Page):
    """A generic flexible page model that can be extended by other apps."""

    template = "flex/flex_page.html"
    page_image = models.ForeignKey(
        'wagtailimages.Image',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+"
    )

    content = StreamField(
        [
            ("explore_block", blocks.ExploreBlock()),
            ("carousel", blocks.CarouselBlock()),
            ("text_band", blocks.TextBand_Block()),
            # ("call_to_action", CallToActionBlock()),
            # ("testimonial", TestimonialBlock()),
            # ("faq", FAQBlock()),
        ],
        null=True,
        blank=True,
    )

    subtitle = models.CharField(max_length=100, null=True, blank=True) # 

    content_panels = Page.content_panels + [
        FieldPanel("page_image"),
        FieldPanel("content"),

    ]

    class Meta:
        verbose_name = "New Page"
        verbose_name_plural = "New Pages"
