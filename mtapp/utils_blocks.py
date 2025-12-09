
from wagtail.blocks import (
    CharBlock,
    StructBlock,
    RichTextBlock,
    ChoiceBlock,
    IntegerBlock,
    DecimalBlock,
    FloatBlock,

)

ITINERARY_BLOCKS = [
    ('day', StructBlock([
        ('day_number', CharBlock(label="Day Number", help_text="e.g., 'Day 1'")),
        ('description', RichTextBlock(label="Description")),
    ]))
]

class PricingTierBlock(StructBlock):
    min_pax = IntegerBlock(required=True)
    max_pax = IntegerBlock(required=True, help_text="Do not leave it empty")

    price_adult = DecimalBlock(required=True, decimal_places=2)
    price_sgl_supplement = DecimalBlock(default=0, decimal_places=2)
    price_dbl_discount = DecimalBlock(default=0, decimal_places=2)
    price_tpl_discount = DecimalBlock(default=0, decimal_places=2)

    child_price_percent = FloatBlock(default=60.0, min_value=0, max_value=100)

    # INFANT FLEXIBILITY
    infant_price_type = ChoiceBlock(
        choices=[
            ('free', 'Free'),
            ('percent', 'Percentage of adult price'),
            ('fixed', 'Fixed amount per infant'),
        ],
        default='free',
    )
    infant_percent_of_adult = FloatBlock(
        default=10.0,
        min_value=0,
        max_value=100,
        required=False,
    )
    infant_fixed_amount = DecimalBlock(
        default=0,
        decimal_places=2,
        required=False,
    )

    class Meta:
        icon = 'currency'
        label = "Pricing Tier"
        # This makes the JS work on add/remove
        form_classname = 'pricing-tier-block'

