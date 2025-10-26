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
# from wagtail.blocks import CharBlock, StructBlock, ListBlock, PageChooserBlock



GLOBAL_ICON_CHOICES = [
    ('fa-swimming-pool', 'Swimming Pool'),
    ('fa-wifi', 'Free WiFi'),
    ('fa-parking', 'Parking'),
    ('fa-spa', 'Spa'),
    ('fa-utensils', 'Restaurant'),
    ('fa-bed', 'Comfortable Beds'),
    ('fa-concierge-bell', 'Concierge Service'),
    ('fa-dumbbell', 'Fitness Center'),
    ('fa-shuttle-van', 'Airport Shuttle'),
    ('fa-hot-tub', 'Hot Tub'),
    ('fa-coffee', 'Breakfast Included'),
    ('fa-tv', 'In-Room TV'),
    ('fa-snowflake', 'Air Conditioning'),
    ('fa-smoking-ban', 'Non-Smoking Rooms'),
    ('fa-paw', 'Pet Friendly'),
    ('fa-child', 'Family Friendly'),
    ('fa-wheelchair', 'Accessibility Features'),
    ('fa-glass-martini', 'Bar'),
    ('fa-bicycle', 'Bicycle Rental'),
    ('fa-hiking', 'Hiking Trails'),
    ('fa-tree', 'Garden'),
    ('fa-water', 'Beach Access'),
    ('fa-shower', 'Private Bathroom'),
    ('fa-laptop', 'Business Center'),
    ('fa-car', 'Car Rental'),
    ('fa-taxi', 'Taxi Service'),
    ('fa-sun', 'Outdoor Terrace'),
    ('fa-umbrella-beach', 'Beach Umbrellas'),
    ('fa-fish', 'Fishing'),
    ('fa-golf-ball', 'Golf Course'),
    ('fa-horse', 'Horseback Riding'),
    ('fa-spa', 'Massage Services'),
    ('fa-tshirt', 'Laundry Service'),
    ('fa-concierge-bell', '24-Hour Front Desk'),
    ('fa-bell', 'Room Service'),
    ('fa-lock', 'Safe Deposit Box'),
    ('fa-shopping-bag', 'Gift Shop'),
    ('fa-camera', 'Photography Tours'),
    ('fa-binoculars', 'Sightseeing Tours'),
    ('fa-map', 'Guided Tours'),
    ('fa-bus', 'Public Transport Access'),
    ('fa-bath', 'Bathtub'),
    ('fa-leaf', 'Eco-Friendly'),
    ('fa-plug', 'Electric Vehicle Charging'),
    ('fa-smoking', 'Smoking Area'),
    ('fa-wine-glass', 'Wine Tasting'),
    ('fa-theater-masks', 'Entertainment Shows'),
    ('fa-briefcase', 'Conference Rooms'),
    ('fa-sun', 'Sun Deck'),
    ('fa-umbrella', 'Poolside Bar'),
]
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

class CarouselBlock(blocks.StructBlock):
    caption = blocks.CharBlock(required=False, help_text="Title for the image")  # Optional caption
    carousel = blocks.ListBlock(
        blocks.StructBlock([
            ('image', ImageChooserBlock()),
            ('caption', blocks.CharBlock(required=False, max_length=40 , help_text="Optional caption for the image")),
            ('link', blocks.PageChooserBlock(required=False, help_text="Optional link for the image. If provided, the image will be clickable.")),
        ]),
        )

    class Meta:
        template = "streams/carousel.html"
        label = "Carousel"
        icon = 'image'

class ExploreBlock(blocks.StructBlock):
    """A Block component to present products or announces with image"""
    title = blocks.RichTextBlock(required=True, help_text='Add title i.e.: Explore this awesome tour')
    image = ImageChooserBlock(
        required=True
    )

    body = blocks.ListBlock(
    blocks.StructBlock([
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

    class Meta: #noqa
        template = "streams/explore_block.html"
        icon = "view"
        label = "Explore Block"

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
        label = "Video Block"

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

colors = [
    ('--cyan-dark-10', 'Cyan'),
    ('--yellow-dark-20', 'Yellow'),
    ('--red-dark-10', 'Red'),
    ('--green2-dark-20', 'Green'),
    ('--yellow-dark-100', 'Black'),
]

class TextBand_Block(blocks.StructBlock):
    '''Three bands with text. #1 and #3 with background color. #2 with cover image'''
    band_title = blocks.CharBlock(required=True, max_length=36)
    textbox_1 = blocks.RichTextBlock(required=True, features=["bold", "italic", "link"])
    textbox_2 = blocks.RichTextBlock(required=True, features=["bold", "italic", "link"])
    background_image = ImageChooserBlock(required=False)
    background_color = blocks.ChoiceBlock(choices=colors, default='--yellow-dark-100')


    class Meta: #noqa
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