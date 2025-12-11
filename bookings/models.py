import string
import secrets
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth.models import User  # or CustomUser if used

from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel
from rest_framework.fields import ReadOnlyField
from wagtail.api import APIField

from bookings.serializer import TourFieldSerializer
from mtapp.utils import generate_code_id
from decimal import Decimal, ROUND_HALF_UP  


@register_snippet
class Proposal(models.Model):
    prop_id = models.CharField(max_length=9, unique=True, editable=False, null=True, help_text=_("Proposal code so the user can track status."))  # Allow null for migration
    customer_name = models.CharField(max_length=200)
    customer_address = models.TextField(blank=True, help_text=_("Optional address for records"))
    nationality = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(blank=True, help_text=_("Additional customer requests or notes"))
    customer_phone = models.CharField(max_length=20, blank=True, help_text="e.g., +593-99-123-4567")
    customer_email = models.EmailField()
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('fulltourpage', 'landtourpage', 'daytourpage')},
        help_text=_("Type of tour (Full, Land, or Day).")
    )
    object_id = models.PositiveIntegerField()
    tour = GenericForeignKey('content_type', 'object_id')
    number_of_adults = models.PositiveIntegerField(default=1)
    number_of_children = models.PositiveIntegerField(default=0)
    number_of_infants = models.PositiveIntegerField(default=0)
    children_ages = models.JSONField(default=list, blank=True, help_text="List of ages for children")
    room_config = models.JSONField(default=dict)
    selected_config = models.JSONField(default=dict, blank=True, help_text="Selected room configuration from pricing options.")
    travel_date = models.DateField(help_text=_("Preferred start date for the tour"))
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    supplier_email = models.EmailField(blank=True, help_text=_("Supplier contact email"))
    payment_link = models.URLField(blank=True, help_text=_("Payment link for customer"))
    currency = models.CharField(max_length=3, default='USD', help_text=_("Currency used for pricing (ISO 4217 code)"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('User'),
        help_text=_('The user who created the proposal. Defaults to MTWEB for non-authenticated users.')
    )

    STATUS_CHOICES = [
        ('PENDING_SUPPLIER', _('Pending Supplier Confirmation')),
        ('PENDING_INTERNAL', _('Pending Internal Confirmation')),  # NEW: For company tours
        ('SUPPLIER_CONFIRMED', _('Supplier Confirmed')),  # Unified: Use this post-internal confirm too
        ('REJECTED', _('Rejected')),
        ('PAID', _('Paid')),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING_SUPPLIER',
    )

    panels = [
        FieldPanel('prop_id', read_only=True),  # Shows as read-only
        FieldPanel('customer_name'),
        FieldPanel('customer_email'),
        FieldPanel('customer_phone'),
        FieldPanel('customer_address'),
        FieldPanel('nationality'),
        FieldPanel('notes'),
        FieldPanel('number_of_adults'),
        FieldPanel('number_of_children'),
        FieldPanel('children_ages'),  # JSON editor in Wagtail
        FieldPanel('travel_date'),
        FieldPanel('estimated_price'),
        FieldPanel('currency'),
        FieldPanel('supplier_email'),
        FieldPanel('payment_link'),
        FieldPanel('room_config'),  # JSON editor
        FieldPanel('status'),
        FieldPanel('user'),
    ]

    api_fields = [
        APIField('prop_id'),
        APIField('customer_name'),
        APIField('customer_email'),
        APIField('customer_phone'),
        APIField('nationality'),
        APIField('customer_address'),
        APIField('notes'),
        APIField('number_of_adults'),
        APIField('number_of_children'),
        APIField('number_of_infants'),
        APIField('children_ages'),  # JSONField → auto as list
        APIField('room_config'),   # JSON → auto as dict
        APIField('selected_config'),
        APIField('travel_date'),
        APIField('estimated_price'),
        APIField('currency'),
        APIField('status'),
        APIField('supplier_email'),
        APIField('payment_link'),
        APIField('created_at'),
        APIField('updated_at'),
        APIField('user'),
        # Custom GenericFK
        APIField('tour.code_id', serializer=TourFieldSerializer()),
        APIField('tour.name', serializer=TourFieldSerializer()),
        APIField('tour.destination', serializer=TourFieldSerializer()),
        # # Human-readable choice
        APIField('status_display', serializer=ReadOnlyField(source='get_status_display')),
    ]

    def clean(self):
        if self.content_type_id and self.object_id:
            try:
                content_type = ContentType.objects.get(pk=self.content_type_id)
                valid_models = {'FullTourPage', 'LandTourPage', 'DayTourPage'}
                model_class = content_type.model_class()
                if model_class.__name__ not in valid_models:
                    raise ValidationError(
                        _("Invalid tour type. Must be one of: %(models)s") % {
                            'models': ', '.join(valid_models)
                        },
                        code='invalid_content_type'
                    )
                if not model_class.objects.filter(pk=self.object_id).exists():
                    raise ValidationError(
                        _("No %(model)s exists with ID %(id)s") % {
                            'model': model_class.__name__,
                            'id': self.object_id
                        },
                        code='invalid_object_id'
                    )
            except ContentType.DoesNotExist:
                raise ValidationError(_("Invalid content type."), code='invalid_content_type')
    
    def save(self, *args, **kwargs):
        if not self.prop_id:
            self.prop_id = generate_code_id("P")
            while Proposal.objects.filter(prop_id=self.prop_id).exists():
                self.prop_id = generate_code_id("P")

        if self.tour:
            child_age_min = self.tour.child_age_min
            self.number_of_infants = sum(1 for age in self.children_ages if age < child_age_min)

            if not self.estimated_price:
                self.estimated_price = self.calculate_estimated_price()

        super().save(*args, **kwargs)

        if self.content_type_id and self.object_id:
            tour_type_map = {
                'FullTourPage': 'fulltour',
                'LandTourPage': 'landtour',
                'DayTourPage': 'daytour',
            }
            content_type = ContentType.objects.get(pk=self.content_type_id)
            tour_type = tour_type_map.get(content_type.model_class().__name__)
            if tour_type:
                cache_key = f'pricing_{tour_type}_{self.object_id}'
                cache.delete(cache_key)

    def calculate_estimated_price(self):
        if self.estimated_price is not None:
            return self.estimated_price  # Use stored (from session/compute_pricing)
        
        if not self.content_type_id or not self.object_id:
            return Decimal('0.00')

        tour = self.tour
        if not tour:
            return Decimal('0.00')

        # Fallback base (no factors—compute_pricing handles them)
        price_adult = Decimal(str(getattr(tour, 'price_adult', '0')))
        price_chd = Decimal(str(getattr(tour, 'price_child', getattr(tour, 'price_chd', '0'))))
        price_inf = Decimal(str(getattr(tour, 'price_inf', '0')))

        if tour.pricing_type == 'Per_room' and self.selected_config:
            config = self.selected_config
            price_sgl = Decimal(str(getattr(tour, 'price_sgl', '0')))
            price_dbl = Decimal(str(getattr(tour, 'price_dbl', '0')))
            price_tpl = Decimal(str(getattr(tour, 'price_tpl', '0')))
            total_price = (
                (config.get('singles', 0) * price_sgl) +
                (config.get('doubles', 0) * price_dbl) +
                (config.get('triples', 0) * price_tpl) +
                (self.number_of_children * price_chd) +
                (self.number_of_infants * price_inf)
            )
        else:
            total_price = (
                (self.number_of_adults * price_adult) +
                (self.number_of_children * price_chd) +
                (self.number_of_infants * price_inf)
            )
        return total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def __str__(self):
        status_label = dict(self.STATUS_CHOICES).get(self.status, self.status)
        return _("Proposal %(prop_id)s for %(name)s - %(tour)s (%(status)s)") % {
            'prop_id': self.prop_id,
            'name': self.customer_name or 'Unknown',
            'tour': self.tour,
            'status': status_label,
        }

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'travel_date', 'status'])
        ]

@register_snippet
class Booking(models.Model):
    book_id = models.CharField(max_length=9, unique=True, editable=False, null=True, help_text=_("Booking code so the user can track status."))  # Allow null for migration
    customer_name = models.CharField(max_length=200)
    customer_address = models.TextField(blank=True, help_text=_("Optional address for records"))
    nationality = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(blank=True, help_text=_("Additional customer requests or notes"))
    customer_phone = models.CharField(max_length=20, blank=True, help_text="e.g., +593-99-123-4567")
    customer_email = models.EmailField()
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('fulltourpage', 'landtourpage', 'daytourpage', '')},
        help_text=_("Type of tour (Full, Land, or Day) or Accommodation.")
    )
    object_id = models.PositiveIntegerField()
    tour = GenericForeignKey('content_type', 'object_id')
    number_of_adults = models.PositiveIntegerField(default=1)
    number_of_children = models.PositiveIntegerField(default=0)
    children_ages = models.JSONField(default=list, blank=True, help_text="List of ages for children")
    booking_date = models.DateTimeField(default=timezone.now)
    travel_date = models.DateField(help_text=_("Preferred start date for the tour"))
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_status = models.CharField(max_length=20, default='UNPAID', choices=[
        ('UNPAID', _('Unpaid')),
        ('PAID', _('Paid')),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    STATUS_CHOICES = [
        ('PENDING_SUPPLIER', _('Pending Supplier Confirmation')),
        ('PENDING_INTERNAL', _('Pending Internal Confirmation')),  # NEW: For company tours
        ('CONFIRMED', _('Confirmed')),  # Unified: Use this post-internal confirm too
        ('REJECTED', _('Rejected')),
        ('PAID', _('Paid')),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('CASH', _('Cash')),
        ('CREDIT_CARD', _('Credit Card')),
        ('BANK_TRANSFER', _('Bank Transfer')),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
    )
    proposal = models.ForeignKey(Proposal, null=True, blank=True, on_delete=models.SET_NULL)
    configuration_details = models.JSONField(default=dict)  # Dict, e.g., {'id': 's1d1t0', 'rooms': [...], 'total': 5327.0}
    currency = models.CharField(max_length=3, default='USD', help_text=_("Currency used for pricing (ISO 4217 code)"))
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('User'),
        help_text=_('The user who created the proposal. Defaults to MTWEB for non-authenticated users.')
    )

    panels = [
    FieldPanel('book_id', read_only=True),  # Shows as read-only
    FieldPanel('customer_name'),
    FieldPanel('customer_email'),
    FieldPanel('customer_phone'),
    FieldPanel('customer_address'),
    FieldPanel('nationality'),
    FieldPanel('notes'),
    FieldPanel('number_of_adults'),
    FieldPanel('number_of_children'),
    FieldPanel('children_ages'),  # JSON editor in Wagtail
    FieldPanel('travel_date'),
    FieldPanel('total_price'),
    FieldPanel('payment_status'),
    FieldPanel('currency'),
    FieldPanel('status'),
    FieldPanel('user'),
        ]
    
    api_fields = [
        APIField('book_id'),
        APIField('customer_name'),
        APIField('customer_email'),
        APIField('customer_phone'),
        APIField('nationality'),
        APIField('customer_address'),
        APIField('notes'),
        APIField('number_of_adults'),
        APIField('number_of_children'),
        APIField('children_ages'),
        APIField('travel_date'),
        APIField('total_price'),
        APIField('currency'),
        APIField('status'),
        APIField('payment_status'),
        APIField('payment_method'),
        APIField('configuration_details'),  # JSON → auto dict
        APIField('booking_date'),
        APIField('created_at'),
        APIField('updated_at'),
        APIField('user'),
        APIField('proposal'),  # Exports as prop_id if you add __str__ or customize
        # Custom
        APIField('tour', serializer=TourFieldSerializer(source='tour', read_only=True)),
        APIField('status_display', serializer=ReadOnlyField(source='get_status_display')),        
        APIField('payment_status_display', serializer=ReadOnlyField(source='get_payment_status_display')),
    ]

    def clean(self):
        if self.content_type_id and self.object_id:
            try:
                content_type = ContentType.objects.get(pk=self.content_type_id)
                valid_models = {'FullTourPage', 'LandTourPage', 'DayTourPage'}
                model_class = content_type.model_class()
                if model_class.__name__ not in valid_models:
                    raise ValidationError(
                        _("Invalid tour type. Must be one of: %(models)s") % {
                            'models': ', '.join(valid_models)
                        },
                        code='invalid_content_type'
                    )
                if not model_class.objects.filter(pk=self.object_id).exists():
                    raise ValidationError(
                        _("No %(model)s exists with ID %(id)s") % {
                            'model': model_class.__name__,
                            'id': self.object_id
                        },
                        code='invalid_object_id'
                    )
            except ContentType.DoesNotExist:
                raise ValidationError(_("Invalid content type."), code='invalid_content_type')

    def save(self, *args, **kwargs):
        from revenue_management.models import Commission  # Avoid circular import

        if not self.book_id:
            self.book_id = generate_code_id("MT")
            while Booking.objects.filter(book_id=self.book_id).exists():
                self.book_id = generate_code_id("MT")

        if not self.total_price:
            self.total_price = self.calculate_total_price()

        # Set user from related Proposal if not set and Proposal exists
        if not self.user and self.proposal:
            self.user = self.proposal.user

        super().save(*args, **kwargs)

        # Create or update Commission record
        if self.user and self.total_price and self.tour:
            commission_rate = getattr(self.tour, 'rep_comm', Decimal('5.0'))  # Default to 5%
            commission_amount = (self.total_price * (commission_rate / Decimal('100.0'))).quantize(Decimal('0.01'))
            Commission.objects.update_or_create(
                booking=self,
                defaults={
                    'user': self.user,
                    'amount': commission_amount,
                    'status': 'PENDING' if self.payment_status == 'PAID' else 'CANCELLED',
                }
            )

        if self.content_type_id and self.object_id:
            tour_type_map = {
                'FullTourPage': 'fulltour',
                'LandTourPage': 'landtour',
                'DayTourPage': 'daytour',
            }
            content_type = ContentType.objects.get(pk=self.content_type_id)
            tour_type = tour_type_map.get(content_type.model_class().__name__)
            if tour_type:
                cache_key = f'pricing_{tour_type}_{self.object_id}'
                cache.delete(cache_key)

        if not self.configuration_details:
            self.configuration_details = self.proposal.room_config if self.proposal else {}


    def __str__(self):
        status_label = dict(self.STATUS_CHOICES).get(self.status, self.status)
        return _("Booking %(book_id)s for %(name)s - %(tour)s (%(status)s)") % {
            'book_id': self.book_id,
            'name': self.customer_name or 'Unknown',
            'tour': self.tour,
            'status': status_label,
        }

    class Meta:
        ordering = ['-booking_date']
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'travel_date', 'status'])
        ]

class ProposalConfirmationToken(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='confirmation_tokens')
    token = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    def generate_token(self):
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(32))

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
            while ProposalConfirmationToken.objects.filter(token=self.token).exists():
                self.token = self.generate_token()
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=48)
        super().save(*args, **kwargs)

    def is_valid(self):
        return (
            self.used_at is None and
            timezone.now() <= self.expires_at and
            self.proposal.status == 'PENDING_SUPPLIER'
        )

    def __str__(self):
        return f"Token for Proposal {self.proposal.id} ({'Valid' if self.is_valid() else 'Invalid'})"

    class Meta:
        indexes = [
            models.Index(fields=['token']),
        ]

class ExchangeRate(models.Model):
    currency_code = models.CharField(max_length=3, unique=True, help_text=_("ISO 4217 currency code (e.g., EUR, GBP)"))
    rate_to_usd = models.DecimalField(max_digits=10, decimal_places=6, help_text=_("Exchange rate relative to 1 USD"))
    last_updated = models.DateTimeField(auto_now=True, help_text=_("When the rate was last updated"))

    class Meta:
        verbose_name = _("Exchange Rate")
        verbose_name_plural = _("Exchange Rates")

    def __str__(self):
        return f"{self.currency_code}: {self.rate_to_usd}"
    
@register_snippet
class AccommodationBooking(models.Model):
    # Generic relation to ANY accommodation page (Glamping, Cabin, HotelRoom, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    accommodation = GenericForeignKey('content_type', 'object_id')

    # Booking details
    check_in = models.DateField()
    check_out = models.DateField()
    adults = models.PositiveSmallIntegerField()
    children = models.PositiveSmallIntegerField(default=0)
    child_ages = models.JSONField(default=list, blank=True, null=True,)

    # Customer
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=30, blank=True, null=True,)
    notes = models.TextField(blank=True)

    # Pricing & Status
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING_PAYMENT', 'Pending Payment'),
            ('PAID', 'Paid'),
            ('SUPPLIER_NOTIFIED', 'Supplier Notified'),
            ('COMPLETED', 'Completed'),
            ('CANCELLED', 'Cancelled'),
        ],
        default='PENDING_PAYMENT'
    )
    supplier_notified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['check_in', 'check_out']),
        ]

    def __str__(self):
        return f"{self.accommodation} • {self.check_in} → {self.check_out}"

    def get_nights(self):
        return (self.check_out - self.check_in).days

    @property
    def accommodation_page(self):
        """Easy access to the actual page (GlampingPage, CabinPage, etc.)"""
        return self.accommodation.specific