# import string
# import secrets
# import requests
# from decimal import Decimal
# from django.db import models
# from django.conf import settings
# from django.utils import timezone
# from django.core.cache import cache
# from mtapp.utils import generate_code_id
# from tours.models import FullTour LandTour
# from django.core.exceptions import ValidationError
# from django.utils.translation import gettext_lazy as _
# from django.contrib.contenttypes.models import ContentType
# from parler.models import TranslatableModel, TranslatedFields
# from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.auth.models import User  # or CustomUser if used


# class Proposal(TranslatableModel):
#     prop_id = models.CharField(max_length=9, unique=True, editable=False, null=True, help_text=_("Proposal code so the user can track status."))  # Allow null for migration
#     translations = TranslatedFields(
#         customer_name=models.CharField(max_length=200),
#         customer_address=models.TextField(blank=True, help_text=_("Optional address for records")),
#         nationality=models.CharField(max_length=100, null=True, blank=True),
#         notes=models.TextField(blank=True, help_text=_("Additional customer requests or notes")),
#     )
#     customer_phone = models.CharField(max_length=20, blank=True, help_text="e.g., +593-99-123-4567")
#     customer_email = models.EmailField()
#     content_type = models.ForeignKey(
#         ContentType,
#         on_delete=models.CASCADE,
#         limit_choices_to={'model__in': ('fulltour', 'landtour', 'daytour')},
#         help_text=_("Type of tour (Full, Land, or Day).")
#     )
#     object_id = models.PositiveIntegerField()
#     tour = GenericForeignKey('content_type', 'object_id')
#     number_of_adults = models.PositiveIntegerField(default=1)
#     number_of_children = models.PositiveIntegerField(default=0)
#     children_ages = models.JSONField(default=list, blank=True, help_text="List of ages for children")
#     room_config = models.JSONField(default=dict)  # Dict, e.g., {'id': 's1d1t0', 'rooms': [...], 'total': 5327.0}
#     travel_date = models.DateField(help_text=_("Preferred start date for the tour"))
#     estimated_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
#     supplier_email = models.EmailField(blank=True, help_text=_("Supplier contact email"))
#     payment_link = models.URLField(blank=True, help_text=_("Payment link for customer"))
#     currency = models.CharField(max_length=3, default='USD', help_text=_("Currency used for pricing (ISO 4217 code)"))
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     user = models.ForeignKey(
#         User,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         verbose_name=_('User'),
#         help_text=_('The user who created the proposal. Defaults to MTWEB for non-authenticated users.')
#     )

#     STATUS_CHOICES = [
#         ('PENDING_SUPPLIER', _('Pending Supplier Confirmation')),
#         ('SUPPLIER_CONFIRMED', _('Supplier Confirmed')),
#         ('REJECTED', _('Rejected')),
#         ('PAID', _('Paid')),
#     ]
#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default='PENDING_SUPPLIER',
#     )

#     def clean(self):
#         if self.content_type_id and self.object_id:
#             try:
#                 content_type = ContentType.objects.get(pk=self.content_type_id)
#                 valid_models = {'FullTour', 'LandTour', 'DayTour'}
#                 model_class = content_type.model_class()
#                 if model_class.__name__ not in valid_models:
#                     raise ValidationError(
#                         _("Invalid tour type. Must be one of: %(models)s") % {
#                             'models': ', '.join(valid_models)
#                         },
#                         code='invalid_content_type'
#                     )
#                 if not model_class.objects.filter(pk=self.object_id).exists():
#                     raise ValidationError(
#                         _("No %(model)s exists with ID %(id)s") % {
#                             'model': model_class.__name__,
#                             'id': self.object_id
#                         },
#                         code='invalid_object_id'
#                     )
#             except ContentType.DoesNotExist:
#                 raise ValidationError(_("Invalid content type."), code='invalid_content_type')

#     def calculate_estimated_price(self):
#         if not self.content_type_id or not self.object_id:
#             return 0
#         tour_type_map = {
#             'FullTour': 'fulltour',
#             'LandTour': 'landtour',
#             'DayTour': 'daytour',
#         }
#         try:
#             content_type = ContentType.objects.get(pk=self.content_type_id)
#             model_name = content_type.model_class().__name__
#             tour_type = tour_type_map.get(model_name)
#             if not tour_type:
#                 return 0
#             response = requests.get(
#                 f"{settings.SITE_URL}/api/tours/dynamic-pricing/{tour_type}/{self.object_id}/",
#                 params={'travel_date': self.travel_date.strftime('%Y-%m-%d')},
#                 timeout=5
#             )
#             response.raise_for_status()
#             prices = response.json()
#             price_adult = Decimal(str(prices['adult']))
#             price_child = Decimal(str(prices['child']))
#         except (requests.RequestException, ValueError, ContentType.DoesNotExist, KeyError):
#             tour = self.tour
#             if not tour:
#                 return 0
#             if isinstance(tour, FullTour):
#                 price_adult = tour.price_dbl_regular
#                 price_child = tour.price_chd_regular
#             elif isinstance(tour, LandTour):
#                 price_adult = tour.price_dbl
#                 price_child = tour.price_chd
#             else:  # DayTour
#                 price_adult = tour.price_adult
#                 price_child = tour.price_child
#         return (self.number_of_adults * price_adult) + (self.number_of_children * price_child)

#     def save(self, *args, **kwargs):
#         if not self.prop_id:
#             self.prop_id = generate_code_id("MT")
#             while Proposal.objects.filter(prop_id=self.prop_id).exists():
#                 self.prop_id = generate_code_id("MT")
#         super().save(*args, **kwargs)

#         if not self.estimated_price:
#             self.estimated_price = self.calculate_estimated_price()
#         super().save(*args, **kwargs)
#         if self.content_type_id and self.object_id:
#             tour_type_map = {
#                 'FullTour': 'fulltour',
#                 'LandTour': 'landtour',
#                 'DayTour': 'daytour',
#             }
#             content_type = ContentType.objects.get(pk=self.content_type_id)
#             tour_type = tour_type_map.get(content_type.model_class().__name__)
#             if tour_type:
#                 cache_key = f'pricing_{tour_type}_{self.object_id}'
#                 cache.delete(cache_key)

#     def __str__(self):
#         return _("Proposal for %(name)s - %(tour)s") % {
#             'name': self.safe_translation_getter('customer_name', 'Unknown'),
#             'tour': self.tour
#         }

#     class Meta:
#         ordering = ['-created_at']
#         indexes = [
#             models.Index(fields=['content_type', 'object_id', 'travel_date', 'status'])
#         ]

# class Booking(TranslatableModel):
#     book_id = models.CharField(max_length=9, unique=True, editable=False, null=True, help_text=_("Booking code so the user can track status."))  # Allow null for migration
#     translations = TranslatedFields(
#         customer_name=models.CharField(max_length=200),
#         customer_address=models.TextField(blank=True, help_text=_("Optional address for records")),
#         nationality=models.CharField(max_length=100, null=True, blank=True),
#         notes=models.TextField(blank=True, help_text=_("Additional customer requests or notes")),
#     )
#     customer_phone = models.CharField(max_length=20, blank=True, help_text="e.g., +593-99-123-4567")
#     customer_email = models.EmailField()
#     content_type = models.ForeignKey(
#         ContentType,
#         on_delete=models.CASCADE,
#         limit_choices_to={'model__in': ('fulltour', 'landtour', 'daytour')},
#         help_text=_("Type of tour (Full, Land, or Day).")
#     )
#     object_id = models.PositiveIntegerField()
#     tour = GenericForeignKey('content_type', 'object_id')
#     number_of_adults = models.PositiveIntegerField(default=1)
#     number_of_children = models.PositiveIntegerField(default=0)
#     children_ages = models.JSONField(default=list, blank=True, help_text="List of ages for children")
#     booking_date = models.DateTimeField(default=timezone.now)
#     travel_date = models.DateField(help_text=_("Preferred start date for the tour"))
#     total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
#     payment_status = models.CharField(max_length=20, default='UNPAID', choices=[
#         ('UNPAID', _('Unpaid')),
#         ('PAID', _('Paid')),
#     ])
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     STATUS_CHOICES = [
#         ('PENDING', _('Pending')),
#         ('CONFIRMED', _('Confirmed')),
#         ('CANCELLED', _('Cancelled')),
#     ]
#     PAYMENT_METHOD_CHOICES = [
#         ('CASH', _('Cash')),
#         ('CREDIT_CARD', _('Credit Card')),
#         ('BANK_TRANSFER', _('Bank Transfer')),
#     ]

#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default='PENDING',
#     )
#     payment_method = models.CharField(
#         max_length=50,
#         choices=PAYMENT_METHOD_CHOICES,
#         blank=True,
#     )
#     proposal = models.ForeignKey(Proposal, null=True, blank=True, on_delete=models.SET_NULL)
#     configuration_details = models.JSONField(default=dict)  # Dict, e.g., {'id': 's1d1t0', 'rooms': [...], 'total': 5327.0}
#     currency = models.CharField(max_length=3, default='USD', help_text=_("Currency used for pricing (ISO 4217 code)"))
#     user = models.ForeignKey(
#         User,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         verbose_name=_('User'),
#         help_text=_('The user who created the proposal. Defaults to MTWEB for non-authenticated users.')
#     )
#     def clean(self):
#         if self.content_type_id and self.object_id:
#             try:
#                 content_type = ContentType.objects.get(pk=self.content_type_id)
#                 valid_models = {'FullTour', 'LandTour', 'DayTour'}
#                 model_class = content_type.model_class()
#                 if model_class.__name__ not in valid_models:
#                     raise ValidationError(
#                         _("Invalid tour type. Must be one of: %(models)s") % {
#                             'models': ', '.join(valid_models)
#                         },
#                         code='invalid_content_type'
#                     )
#                 if not model_class.objects.filter(pk=self.object_id).exists():
#                     raise ValidationError(
#                         _("No %(model)s exists with ID %(id)s") % {
#                             'model': model_class.__name__,
#                             'id': self.object_id
#                         },
#                         code='invalid_object_id'
#                     )
#             except ContentType.DoesNotExist:
#                 raise ValidationError(_("Invalid content type."), code='invalid_content_type')

#     def calculate_total_price(self):
#         if not self.content_type_id or not self.object_id:
#             return 0
#         tour_type_map = {
#             'FullTour': 'fulltour',
#             'LandTour': 'landtour',
#             'DayTour': 'daytour',
#         }
#         try:
#             content_type = ContentType.objects.get(pk=self.content_type_id)
#             model_name = content_type.model_class().__name__
#             tour_type = tour_type_map.get(model_name)
#             if not tour_type:
#                 return 0
#             response = requests.get(
#                 f"{settings.SITE_URL}/api/tours/dynamic-pricing/{tour_type}/{self.object_id}/",
#                 params={'travel_date': self.travel_date.strftime('%Y-%m-%d')},
#                 timeout=5
#             )
#             response.raise_for_status()
#             prices = response.json()
#             price_adult = Decimal(str(prices['adult']))
#             price_child = Decimal(str(prices['child']))
#         except (requests.RequestException, ValueError, ContentType.DoesNotExist, KeyError):
#             tour = self.tour
#             if not tour:
#                 return 0
#             if isinstance(tour, FullTour):
#                 price_adult = tour.price_dbl_regular
#                 price_child = tour.price_chd_regular
#             elif isinstance(tour, LandTour):
#                 price_adult = tour.price_dbl
#                 price_child = tour.price_chd
#             else:  # DayTour
#                 price_adult = tour.price_adult
#                 price_child = tour.price_child
#         return (self.number_of_adults * price_adult) + (self.number_of_children * price_child)

#     def save(self, *args, **kwargs):
#         from revenue_management.models import Commission  # Avoid circular import

#         if not self.book_id:
#             self.book_id = generate_code_id("AL")
#             while Booking.objects.filter(book_id=self.book_id).exists():
#                 self.book_id = generate_code_id("AL")

#         if not self.total_price:
#             self.total_price = self.calculate_total_price()

#         # Set user from related Proposal if not set and Proposal exists
#         if not self.user and self.proposal:
#             self.user = self.proposal.user

#         super().save(*args, **kwargs)

#         # Create or update Commission record
#         if self.user and self.total_price and self.tour:
#             commission_rate = getattr(self.tour, 'rep_comm', Decimal('5.0'))  # Default to 10%
#             commission_amount = (self.total_price * (commission_rate / Decimal('100.0'))).quantize(Decimal('0.01'))
#             Commission.objects.update_or_create(
#                 booking=self,
#                 defaults={
#                     'user': self.user,
#                     'amount': commission_amount,
#                     'status': 'PENDING' if self.payment_status == 'PAID' else 'CANCELLED',
#                 }
#             )

#         if self.content_type_id and self.object_id:
#             tour_type_map = {
#                 'FullTour': 'fulltour',
#                 'LandTour': 'landtour',
#                 'DayTour': 'daytour',
#             }
#             content_type = ContentType.objects.get(pk=self.content_type_id)
#             tour_type = tour_type_map.get(content_type.model_class().__name__)
#             if tour_type:
#                 cache_key = f'pricing_{tour_type}_{self.object_id}'
#                 cache.delete(cache_key)

#         if not self.configuration_details:
#             self.configuration_details = self.proposal.room_config if self.proposal else {}

#     def __str__(self):
#         return _("Booking for %(name)s - %(tour)s") % {
#             'name': self.safe_translation_getter('customer_name', 'Unknown'),
#             'tour': self.tour
#         }

#     class Meta:
#         ordering = ['-booking_date']
#         indexes = [
#             models.Index(fields=['content_type', 'object_id', 'travel_date', 'status'])
#         ]

# class ProposalConfirmationToken(models.Model):
#     proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='confirmation_tokens')
#     token = models.CharField(max_length=32, unique=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     used_at = models.DateTimeField(null=True, blank=True)
#     expires_at = models.DateTimeField()

#     def generate_token(self):
#         characters = string.ascii_letters + string.digits
#         return ''.join(secrets.choice(characters) for _ in range(32))

#     def save(self, *args, **kwargs):
#         if not self.token:
#             self.token = self.generate_token()
#             while ProposalConfirmationToken.objects.filter(token=self.token).exists():
#                 self.token = self.generate_token()
#         if not self.expires_at:
#             self.expires_at = timezone.now() + timezone.timedelta(hours=48)
#         super().save(*args, **kwargs)

#     def is_valid(self):
#         return (
#             self.used_at is None and
#             timezone.now() <= self.expires_at and
#             self.proposal.status == 'PENDING_SUPPLIER'
#         )

#     def __str__(self):
#         return f"Token for Proposal {self.proposal.id} ({'Valid' if self.is_valid() else 'Invalid'})"

#     class Meta:
#         indexes = [
#             models.Index(fields=['token']),
#         ]

# class ExchangeRate(models.Model):
#     currency_code = models.CharField(max_length=3, unique=True, help_text=_("ISO 4217 currency code (e.g., EUR, GBP)"))
#     rate_to_usd = models.DecimalField(max_digits=10, decimal_places=6, help_text=_("Exchange rate relative to 1 USD"))
#     last_updated = models.DateTimeField(auto_now=True, help_text=_("When the rate was last updated"))

#     class Meta:
#         verbose_name = _("Exchange Rate")
#         verbose_name_plural = _("Exchange Rates")

#     def __str__(self):
#         return f"{self.currency_code}: {self.rate_to_usd}"