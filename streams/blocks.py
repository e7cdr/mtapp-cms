"""
Note: This blocks.py is different from the wagtails.core blocks.py. In this file, we define custom blocks for our project so
that we can use them in our StreamField models (basically, blocks that can be reused in different pages). This way, we can keep
our code DRY (Don't Repeat Yourself). i.e., if we want to change the way a certain block looks, we only have to change it here,
and it will be reflected everywhere it's used. Also, if we have, for example, a title, text, and image block that we use in multiple
pages, we can define it once here and use it in all those pages without redefining it each time. The only thing we need to do is import
this file in the models.py file where we want to use these blocks. And we're good to go!!
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.admin.panels import PageChooserPanel
from django.contrib.sites.shortcuts import get_current_site  # NEW: For safe site resolution
from site_settings.models import FooterLinks
from mtapp.choices import colors, swipers, position, GLOBAL_ICON_CHOICES


GLOBAL_ICON_CHOICES = sorted(GLOBAL_ICON_CHOICES, key=lambda x: x[1].lower())

def create_icons_list(icon_choices=None):
    """
    Factory: Creates Icons_List with optional filtered choices.
    Defaults to GLOBAL_ICON_CHOICES if none provided.
    """
    icon_choices = icon_choices or GLOBAL_ICON_CHOICES

    class IconsList(blocks.StructBlock):
        icon = blocks.ChoiceBlock(
            choices=icon_choices,  # Injected filtered list
            required=True,
            help_text="Select an icon (filtered for this page).",
        )
        name = blocks.CharBlock(
            required=True,
            max_length=50,
            help_text="Hover text for the amenity.",
        )
        # Add other fields if needed (e.g., link)

        class Meta:
            template = "streams/icon_items.html"  # Your per-item template
            icon = "list-ul"
            label = "Icon Item"

    return IconsList

# For generic use elsewhere (full choices):
Icons_List = create_icons_list()  # Exports the default version

class ExploreBlock(blocks.StructBlock):
    """A Block component to present products or announces with image"""
    title = blocks.RichTextBlock(required=True, help_text='Add title i.e.: Explore this awesome tour')
    image = ImageChooserBlock(
        required=True
    )
    image_alt_text = blocks.CharBlock(required=True, help="Alternative text. This won't appear to the user but it is used for better SEO.")
    image_link = blocks.PageChooserBlock(required=False, help_text="Link to redirect the user. The more internal links to other part of the page, the better for SEO.")
    body = blocks.ListBlock(
    blocks.StructBlock([
        ('icon_alt_text', blocks.CharBlock(required=True, default="Icon")),
        ('icon_1', ImageChooserBlock(required=True, help_text="56px x 56px")),
        ('subtitle_1', blocks.CharBlock(required=True, max_length=60, help_text="Subtitle below the top left icon")),
        ('text_1', blocks.RichTextBlock(required=True, max_length=300)),
        ('icon_2', ImageChooserBlock(required=True, help_text="56px x 56px")),
        ('subtitle_2', blocks.CharBlock(required=True, max_length=60, help_text="Subtitle below the top right icon")),
        ('text_2', blocks.RichTextBlock(required=True, max_length=300)),
        ('icon_3', ImageChooserBlock(required=True, help_text="56px x 56px")),
        ('subtitle_3', blocks.CharBlock(required=True, max_length=60, help_text="Subtitle below the bottom left icon")),
        ('text_3', blocks.RichTextBlock(required=True, max_length=300)),
        ('icon_4', ImageChooserBlock(required=True, help_text="56px x 56px")),
        ('subtitle_4', blocks.CharBlock(required=True, max_length=60, help_text="Subtitle below the bottom right icon")),
        ('text_4', blocks.RichTextBlock(required=True, max_length=300)),
    ]),
    )
    def clean(self, value):
        if value.get('image_link') == '':
            value['image_link'] = None
        return super().clean(value)
    
    class Meta: #noqa
        template = "streams/explore_block.html"
        icon = "view"
        label = "Explore Block"
        help_text = "A Block component to present products or announces with circular image."

class Video_Text_Block(blocks.StructBlock):
    """ A Video block with texts below"""
    title = blocks.RichTextBlock(required=True, help_text='Add title i.e.: Explore this awesome tour')
    video = blocks.URLBlock(required=True, help_text="Youtube EMBED link. i.e.: https://www.youtube.com/embed/_lw9r4T1PEc?si=43WbnkOeB1LsVgwL. Go to Share and click on <>EMBED")

    body = blocks.ListBlock(
    blocks.StructBlock([
        ('icon_1', ImageChooserBlock(required=True, help_text="100px x 100px")),
        ('subtitle_1', blocks.CharBlock(required=True, max_length=60, help_text="Subtitle below the top left icon")),
        ('text_1', blocks.RichTextBlock(required=True, max_length=300)),
        ('icon_2', ImageChooserBlock(required=True, help_text="100px x 100px")),
        ('subtitle_2', blocks.CharBlock(required=True, max_length=60, help_text="Subtitle below the top right icon")),
        ('text_2', blocks.RichTextBlock(required=True, max_length=300)),
    ]),
    )

    class Meta: #noqa
        template = "streams/video_text_content.html"
        icon = "media"
        label = "Video with Text Blocks"

class Cards_Block(blocks.StructBlock):
    image = ImageChooserBlock(required=True, help_text="Product image")
    title = blocks.CharBlock(required=True, help_text='Add title i.e.: Explore this awesome tour', max_length=35)
    sub_title = blocks.RichTextBlock(required=True, help_text='Add subtitle i.e.: Explore this awesome tour', max_length=45)
    card_description = blocks.RichTextBlock(required=True, help_text='Add description i.e.: Explore this awesome tour', max_length=76)

    amenities = blocks.ListBlock(
        Icons_List,  # Your global version: create_icons_list() with full choices
        max_num=5,
        required=False,
        help_text="Add up to 5 amenities.",
    )

    price = blocks.FloatBlock(
        required=True,
        help_text="Estimated price",
        decimal_places=2,
    )
    price_subtext = blocks.CharBlock(required=False, help_text="Estimated. IVA not included")
    button_title = blocks.CharBlock(required=True, help_text="i.e.: Book, Buy, Contact")
    button_link = blocks.URLBlock(required=True, help_text="URL to redirect when clicking the button.")

    tags = blocks.ListBlock(
        blocks.StructBlock([
            ('top_tag_1', blocks.CharBlock(help_text="Yellow Tag")),
            ('top_tag_2', blocks.CharBlock(help_text="Red Tag")),
            ('center_right_tag_1', blocks.CharBlock(help_text="Country tag")),
            ('center_right_tag_2', blocks.CharBlock(help_text="Destination inside the country tag")),
        ], max_num=1)
    )

    class Meta:
        template = "streams/cards.html"
        icon = "form"
        label = "Empty card"

# Subclass for HomePage: Overrides amenities with filtered icons
class HomeCardsBlock(Cards_Block):
    amenities = blocks.ListBlock(
        create_icons_list(
            icon_choices=[
                ('fa-swimming-pool', 'Swimming Pool'),
                ('fa-wifi', 'Free WiFi'),
                ('fa-parking', 'Parking'),
                ('fa-spa', 'Spa'),
            ]
        ),
        max_num=5,
        required=False,
        help_text="Add up to 5 amenities (Home-specific icons).",
    )

    class Meta:
        label = "Home Card"  # Optional: Distinguishes in admin dropdown

class TextBand_Block(blocks.StructBlock):
    '''Three bands with text. #1 and #3 with background color. #2 with cover image'''
    band_title = blocks.CharBlock(required=False, max_length=36)
    textbox_1 = blocks.RichTextBlock(required=True, features="minimal")
    textbox_2 = blocks.RichTextBlock(required=True, features="minimal")
    background_image = ImageChooserBlock(required=False)
    background_color = blocks.ChoiceBlock(choices=colors, default='--yellow-dark-100')

    class Meta:  # noqa
        template = "streams/text_bands.html"
        icon = "doc-full"
        label = "Text Band"

class Itinerary_Block(blocks.StructBlock):

    itinerary = blocks.ListBlock(
        blocks.StructBlock([
            ('day', blocks.IntegerBlock(required=True)),
            ('description', blocks.RichTextBlock(required=True, max_length=300, help_text="Day description")),
            ('hightlight', blocks.RichTextBlock(required=True, max_length=300)),
        ], max_num=1)
    )

class Flex_Images_Block(blocks.StructBlock):
    image_caption = blocks.ListBlock(
        blocks.StructBlock([
            ('image', ImageChooserBlock(required=True)),
            ('caption', blocks.CharBlock(required=True, max_length=300, help_text="Image caption")),
        ],)
    )
    class Meta:
        template = "streams/flex_images.html"
        icon = "image"
        label = "Flex images"

class CTA_Block_2B(blocks.StructBlock):
    """A text box with title, subtitle above title, description and two buttons that send user to another page"""
    image_position = blocks.ChoiceBlock(choices=position, default='bottom', help_text="Text box background color")
    image = ImageChooserBlock(required=False, help_text="This image will appear below the CTA")
    caption = blocks.CharBlock(required=False, help_text="Caption at the base of the image", max_length=33)
    include_cta = blocks.BooleanBlock(required=False, help_text="By checking the box, a Call To Action with buttons and a bullet point list will be available")
    background_color = blocks.ChoiceBlock(choices=colors, default='--yellow-dark-100', help_text="Text box background color")
    cta_title = blocks.CharBlock(required=False, help_text="The main title.", max_length=33)
    cta_description = blocks.RichTextBlock(required=False, help_text="Describe in detail your Call To Action",)
    button_1_text = blocks.CharBlock(required=False, help_text="Button text.", max_length=33)
    button_link_1 = blocks.PageChooserBlock(required=False, help_text="Optional link to send the user by clicking the left button")
    button_2_text = blocks.CharBlock(required=False, help_text="The main title.", max_length=33)
    button_link_2 = blocks.PageChooserBlock(required=False, help_text="Optional link to send the user by clicking the right button")
    list = blocks.ListBlock(
        blocks.StructBlock([
            ('element', blocks.CharBlock(required=False, max_length=33, help_text="Bullet point list element")),
        ])
    )


    class Meta:
        template = "streams/cta.html"
        icon = "doc-full"
        label = "CTA 2 Buttons"
        help_text = "A text box with title, subtitle above title, description and two buttons that send user to another page"

class Swipers(blocks.StructBlock):
    """Swiper design with different variations"""
    swiper_title = blocks.CharBlock(required=False, help_text="The main title.", max_length=33)
    variations = blocks.ChoiceBlock(choices=swipers, default='basic')
    images = blocks.ListBlock(
        blocks.StructBlock([
            ('image', ImageChooserBlock(required=False,)),
            ('caption', blocks.CharBlock(required=False, max_length=40 , help_text="Optional caption for the image")),
            ('yt_vid', blocks.CharBlock(required=False, max_length=40 , help_text="Youtube video ID. This will only work for COLLAGE AND THUMBNAIL Variation", verbose_name="Youtube Video ID")),
            ('link', blocks.PageChooserBlock(required=False, help_text="Optional link for the image. If provided, the image will be clickable.")),
        ]),
        ) 
   
    class Meta:
        template = "streams/swipers.html"
        icon = "image"
        label = "Swiper"
        help_text = "Swiper with more than one variation to choose from. Only Collage and Thumbnail variation support Embed Youtube Videos"

class FadeCarousel(blocks.StructBlock):
    """Fade Swiper or carousel with fade effect"""
    fade_title = blocks.CharBlock(required=False, help_text="The main title.", max_length=33)
    fade_subtitle = blocks.CharBlock(required=False, help_text="The subtitle.", max_length=33)
    height = blocks.IntegerBlock(default=50, help_text="Image height in 'rem' units.", verbose_name="Image Height")
    images = blocks.ListBlock(
        blocks.StructBlock([
            ('image', ImageChooserBlock(required=False)),
            ('caption', blocks.CharBlock(required=False, max_length=40 , help_text="Optional caption for the image")),
            ('yt_vid', blocks.CharBlock(required=False, max_length=40 , help_text="Youtube video ID. This will only work for COLLAGE AND THUMBNAIL Variation")),
            ('link', blocks.PageChooserBlock(required=False, help_text="Optional link for the image. If provided, the image will be clickable.")),
        ]),
        ) 
    search_bar = blocks.BooleanBlock(required=False, default=False)

    class Meta:
        template = "streams/fade_carousel.html"
        icon = "image"
        label = "Fade Carousel"
        help_text = "Fade Carousel intended to be used as initial cover pages"

class ParallaxImageBlock(blocks.StructBlock):
    """
    A full-width parallax background image section.
    """
    max_count = 1
    image = ImageChooserBlock(required=True, help_text="Upload a high-res landscape image (1920x1080+ recommended).")
    overlay_title = blocks.CharBlock(
        required=False, 
        help_text="Optional large title overlay (e.g., 'Discover Colombia').",
        classname="title"
    )
    overlay_subtitle = blocks.TextBlock(
        required=False, 
        help_text="Optional subtitle or CTA (e.g., 'Scroll to explore adventures').",
        classname="subtitle"
    )
    overlay_link = blocks.URLBlock(
        required=False, 
        help_text="Optional link for subtitle (e.g., to a tour page)."
    )
    section_height = blocks.CharBlock(
        default="80vh",
        help_text="Height of the section (e.g., '80vh', '600px').",
        classname="fullwidth"
    )
    parallax_speed = blocks.CharBlock(
        default="0.5",
        help_text="Parallax intensity (0.1 = subtle, 1 = strong; use CSS transform for JS version).",
        classname="fullwidth"
    )

    class Meta:
        template = "streams/parallax_image_block.html"
        icon = "image"
        label = "Parallax Image Section"

class GriddedImages(blocks.StructBlock):
    """Gridded images. Please add a Minimum of 4 images to appreaciate the full and correct effect of the component"""

    images = blocks.ListBlock(
        blocks.StructBlock([
            ('image', ImageChooserBlock()),
            ('caption', blocks.CharBlock(required=False, max_length=30 , help_text="Optional caption for the image. Add one for Better SEO")),
            ('link', blocks.PageChooserBlock(required=False, help_text="Although optional, we recommend to add internal links for better SEO")),
        ]),
        ) 
   
    class Meta:
        help_text = "Please add a Minimum of 4 images to appreaciate the full and correct effect of the component"
        template = "streams/gridded_images.html"
        icon = "image"
        label = "Gridded Images"

class TourTeaserBlock(blocks.StructBlock):
    tour = blocks.PageChooserBlock(
        required=True,
        page_type=["tours.LandTourPage", "tours.FullTourPage", "tours.DayTourPage"],  # ← THIS IS THE FIX
        help_text="Choose any tour: Land, Full, or Day tour"
    )
    custom_title = blocks.CharBlock(required=False, help_text="Override tour name")
    cta_text = blocks.CharBlock(default="Book this tour", required=False)

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context=parent_context)
        tour = value["tour"].specific

        context.update({
            "tour_url": tour.url,
            "tour_title": value["custom_title"] or getattr(tour, "name", tour.title),
            "cta_text": value["cta_text"],
        })

        # Price logic (safe)
        try:
            if tour.collect_price and hasattr(tour, "active_prices"):
                price = None
                prices = tour.active_prices
                if tour.pricing_type == "Per_person":
                    price = prices.get("adult") or prices.get("chd")
                elif tour.pricing_type in ["Per_room", "Combined"]:
                    price = prices.get("dbl") or prices.get("adult")
                context["price"] = f"From ${price}" if price else "Contact us"
            else:
                context["price"] = "Inquiry only"
        except:
            context["price"] = "View tour"

        return context

    class Meta:
        template = "blog/blocks/tour_teaser.html"
        icon = "pick"

# ------------------------------------------------------------------
# SIDEBAR – Fully customizable via Wagtail editor!
# ------------------------------------------------------------------

class SidebarWidgetBlock(blocks.StructBlock):
    """One widget for the sidebar – you can add as many as you want"""
    title = blocks.CharBlock(required=True, help_text="e.g. On this page, Share, About the author")
    
    widget_type = blocks.ChoiceBlock(
        choices=[
            ('toc', 'Table of Contents (auto-generated)'),
            ('share', 'Share Buttons'),
            ('author', 'Author Card'),
            ('newsletter', 'Newsletter Signup'),
            ('related', 'Related Posts'),
            ('custom', 'Custom Content'),
        ],
        default='custom',
        help_text="Auto TOC is smart – it reads H2/H3 from the article body"
    )

    # Only used for certain types
    content = blocks.RichTextBlock(required=False, features=['bold', 'italic', 'link'])
    image = ImageChooserBlock(required=False)
    name = blocks.CharBlock(required=False, help_text="Author name")
    role = blocks.CharBlock(required=False, help_text="e.g. Travel Expert in Poland")
    social_twitter = blocks.CharBlock(required=False)
    social_instagram = blocks.CharBlock(required=False)

    class Meta:
        template = "streams/sidebar_widget.html"
        icon = "cogs"

class FAQItemBlock(blocks.StructBlock):
    question = blocks.CharBlock(required=True, label="Question")
    answer = blocks.RichTextBlock(
        required=True,
        features=['bold', 'italic', 'link'],
        label="Answer"
    )

    class Meta:
        icon = "help"
        template = "streams/faq_item.html"  # one item

class FAQBlock(blocks.StreamBlock):
    """Multiple FAQs — cleaner than ListBlock + StructBlock"""
    item = FAQItemBlock()

    class Meta:
        template = "streams/faq_block.html"
        icon = "list-ul"
        label = "FAQ Section"

class WrappedRichTextBlock(blocks.StructBlock):
    """
    A rich text section wrapped in a container for easier CSS targeting.
    Optionally add a custom CSS class for more styling control.
    """
    content = blocks.RichTextBlock(
        label="Rich Text Content"
    )
    custom_class = blocks.CharBlock(
        required=False,
        help_text="Optional extra CSS class(es) for this section (space-separated)",
        label="Custom CSS Class"
    )

    class Meta:
        icon = 'pilcrow'  # or 'doc-full' for a paragraph-like icon
        template = 'streams/wrapped_richtext.html'  # we'll create this next
        label = 'Rich Text Section'