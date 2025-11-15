"""
The Flex app was created to manage flexible content types and streamfields.
It contains models and blocks that can be reused across different pages in the project (for example, blocks from streams/blocks.py).
This helps to keep the code DRY (Don't Repeat Yourself) and makes it easier to maintain and update the content structure of the website.
It also allows for more dynamic and customizable page layouts, as content editors can mix and match different blocks to create unique
pages without needing to create new models for each layout variation.

These blocks will appear in the StreamField options when creating or editing pages that use them (At the end of the admin page).

"""

from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page

from streams import blocks

# Create your models here.

class FlexPage(Page):
    """A generic flexible page model that can be extended by other apps."""

    template = "flex/flex_page.html"
    content = StreamField(
        [
            ("explore_block", blocks.ExploreBlock()),
            ("text_band", blocks.TextBand_Block()),
            ("flex_images", blocks.Flex_Images_Block()),
            ("video_text_block", blocks.Video_Text_Block()),
            ("cta_2B", blocks.CTA_Block_2B()),

        ],
        null=True,
        blank=True,
        help_text="""
        This is the page's body. Use the different blocks by clicking the Plus (+) icon. Carousel Block to add Cover Images.
        More than one images will incurred in the Slide effect. Text Band will add a text section with color background that
        occupies the whole width of the page. Explore Block will add a dedicated section to expand in detail any product, announce or service.
        More blocks are currently being developed. If you need a specific design, please contact developer and show them the design you would like
        to see implemented. Anything is possible!.
        """,
    )

    content_panels = Page.content_panels + [
        FieldPanel("content"),

    ]

    class Meta:
        verbose_name = "Flex Page"
        verbose_name_plural = "Flex Pages"
