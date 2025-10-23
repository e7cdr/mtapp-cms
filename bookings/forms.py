# import json
# import logging
# from django import forms
# from datetime import timedelta
# from django.db.models import Sum
# from parler.forms import TranslatableModelForm
# from .models import Booking, Proposal, ExchangeRate
# from tours.models import FullTour, LandTour, DayTour
# from django.utils.translation import gettext_lazy as _
# from django.contrib.contenttypes.models import ContentType

# logger = logging.getLogger(__name__)

# class ProposalForm(TranslatableModelForm):
#     tour_type = forms.CharField(max_length=20, required=True)
#     tour_id = forms.IntegerField(min_value=1, required=True)
#     travel_date = forms.DateField(required=True)
#     end_date = forms.DateField(required=False)
#     number_of_adults = forms.IntegerField(min_value=1, required=True)
#     number_of_children = forms.IntegerField(min_value=0, required=False)
#     child_ages = forms.JSONField(required=False, initial=[])
#     customer_name = forms.CharField(max_length=200, required=False)
#     customer_email = forms.EmailField(required=False)
#     customer_phone = forms.CharField(max_length=20, required=False)
#     nationality = forms.CharField(max_length=100, required=False)
#     customer_address = forms.CharField(widget=forms.Textarea, required=False)
#     notes = forms.CharField(widget=forms.Textarea, required=False)
#     form_submission = forms.CharField(max_length=20, required=False, initial='pricing')
#     selected_configuration = forms.CharField(max_length=255, required=False)
#     currency = forms.ChoiceField(
#         choices=lambda: [(rate.currency_code, rate.currency_code) for rate in ExchangeRate.objects.all()] + [('USD', 'USD')],
#         required=True,
#         initial='USD',
#         help_text=_("Select the currency for pricing")
#     )

#     class Meta:
#         model = Proposal
#         fields = [
#             'tour_type', 'tour_id', 'customer_name', 'customer_email', 'customer_phone',
#             'customer_address', 'nationality', 'number_of_adults', 'number_of_children',
#             'travel_date', 'notes', 'child_ages', 'selected_configuration'
#         ]
#         translated_fields = ['customer_name', 'customer_address', 'nationality', 'notes']
#         widgets = {
#             'travel_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'text'}),
#             'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
#             'customer_email': forms.EmailInput(attrs={'class': 'form-control'}),
#             'customer_phone': forms.TextInput(attrs={'class': 'form-control'}),
#             'customer_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
#             'nationality': forms.TextInput(attrs={'class': 'form-control'}),
#             'number_of_adults': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
#             'number_of_children': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
#             'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
#             'child_ages': forms.HiddenInput(),
#             'selected_configuration': forms.HiddenInput()
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         form_submission = self.data.get('form_submission', 'pricing') if self.data else self.initial.get('form_submission', 'pricing')
#         if form_submission == 'pricing':
#             for field in ['customer_name', 'customer_email', 'customer_phone', 'customer_address', 'nationality', 'notes']:
#                 self.fields[field].required = False

#     def clean_child_ages(self):
#         number_of_children = int(self.data.get('number_of_children', 0))
#         child_ages = self.data.get('child_ages', '[]')
#         form_submission = self.data.get('form_submission', 'pricing')
#         tour_type = self.data.get('tour_type')
#         tour_id = self.data.get('tour_id')

#         logger.debug(f"clean_child_ages: number_of_children={number_of_children}, child_ages={child_ages}, form_submission={form_submission}")

#         # Fetch tour to get child_age_min and child_age_max
#         child_age_min = 7
#         child_age_max = 12
#         if tour_type and tour_id:
#             model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
#             model = model_map.get(tour_type.lower())
#             if model:
#                 try:
#                     tour = model.objects.get(pk=tour_id)
#                     child_age_min = getattr(tour, 'child_age_min', 7)
#                     child_age_max = getattr(tour, 'child_age_max', 12)
#                 except model.DoesNotExist:
#                     logger.warning(f"Tour not found: type={tour_type}, id={tour_id}")

#         if number_of_children == 0:
#             return []

#         try:
#             ages = json.loads(child_ages) if isinstance(child_ages, str) else child_ages
#             if not isinstance(ages, list):
#                 logger.warning(f"child_ages is not a list: {ages}")
#                 ages = [child_age_min] * number_of_children
#             ages = [int(age) if isinstance(age, (int, float, str)) and str(age).isdigit() else child_age_min for age in ages]
#             if form_submission == 'pricing':
#                 if len(ages) < number_of_children:
#                     ages.extend([child_age_min] * (number_of_children - len(ages)))
#                 ages = ages[:number_of_children]
#             elif form_submission == 'full':
#                 if len(ages) != number_of_children:
#                     raise forms.ValidationError(_('Number of child ages must match number of children.'))
#                 for age in ages:
#                     if not (0 <= age <= child_age_max):
#                         raise forms.ValidationError(_('Child ages must be between 0 and %s.') % child_age_max)
#             return ages
#         except json.JSONDecodeError as e:
#             logger.error(f"Invalid child_ages JSON: {child_ages}, error={e}")
#             return [child_age_min] * number_of_children

#     def clean(self):
#         cleaned_data = super().clean()
#         tour_type = cleaned_data.get('tour_type')
#         tour_id = cleaned_data.get('tour_id')
#         travel_date = cleaned_data.get('travel_date')
#         number_of_adults = cleaned_data.get('number_of_adults', 0)
#         number_of_children = cleaned_data.get('number_of_children', 0)
#         child_ages = cleaned_data.get('child_ages', [])
#         form_submission = self.data.get('form_submission', 'pricing')
#         selected_configuration = cleaned_data.get('selected_configuration', '0')

#         logger.debug(f"clean: tour_type={tour_type}, tour_id={tour_id}, travel_date={travel_date}, number_of_adults={number_of_adults}, number_of_children={number_of_children}, child_ages={child_ages}, form_submission={form_submission}, selected_configuration={selected_configuration}")

#         # Validate travel_date
#         if not travel_date:
#             self.add_error('travel_date', _('Travel date is required.'))

#         # Fetch tour details
#         child_age_min = 7
#         child_age_max = 12
#         max_children_per_room = 1
#         tour = None
#         if tour_type and tour_id:
#             model_map = {'full': FullTour, 'land': LandTour, 'day': DayTour}
#             model = model_map.get(tour_type.lower())
#             if model:
#                 try:
#                     tour = model.objects.get(pk=tour_id)
#                     child_age_min = getattr(tour, 'child_age_min', 7)
#                     child_age_max = getattr(tour, 'child_age_max', 12)
#                     max_children_per_room = getattr(tour, 'max_children_per_room', 1)
#                 except model.DoesNotExist:
#                     self.add_error('tour_id', _('Selected tour does not exist or is unavailable.'))

#         # Process child ages
#         if not isinstance(child_ages, list):
#             try:
#                 child_ages = json.loads(child_ages) if child_ages else []
#             except json.JSONDecodeError:
#                 child_ages = []
#         if number_of_children > 0:
#             if len(child_ages) < number_of_children:
#                 child_ages.extend([child_age_min] * (number_of_children - len(child_ages)))
#             child_ages = child_ages[:number_of_children]

#         infants = [age for age in child_ages if age < child_age_min]
#         valid_children = [age for age in child_ages if child_age_min <= age <= child_age_max]
#         extra_adults = [age for age in child_ages if age > child_age_max]

#         cleaned_data['number_of_adults'] = number_of_adults + len(extra_adults)
#         cleaned_data['infants'] = len(infants)
#         cleaned_data['valid_child_ages'] = valid_children
#         cleaned_data['child_ages'] = child_ages

#         # Validate selected_configuration
#         try:
#             idx = int(selected_configuration)
#             if idx < 0:
#                 cleaned_data['selected_configuration'] = '0'
#                 logger.warning(f"Negative selected_configuration: {selected_configuration}, resetting to 0")
#         except ValueError:
#             cleaned_data['selected_configuration'] = '0'
#             logger.warning(f"Non-integer selected_configuration: {selected_configuration}, resetting to 0")

#         # Full submission validation
#         if form_submission == 'full':
#             if not cleaned_data.get('customer_name'):
#                 self.add_error('customer_name', _('Customer name is required.'))
#             if not cleaned_data.get('customer_email'):
#                 self.add_error('customer_email', _('Email is required.'))
#             if number_of_children > 0:
#                 if len(child_ages) != number_of_children:
#                     self.add_error('child_ages', _('Number of child ages must match number of children.'))
#                 total_rooms = (cleaned_data['number_of_adults'] + 1) // 2
#                 if len(valid_children) > total_rooms * max_children_per_room:
#                     self.add_error('child_ages', _(
#                         'Maximum %s children aged %s–%s allowed for %s adults.') % (
#                             total_rooms * max_children_per_room, child_age_min, child_age_max, cleaned_data['number_of_adults']
#                         ))
#                 for age in child_ages:
#                     if age < 0 or age > child_age_max:
#                         self.add_error('child_ages', _(
#                             'Child ages must be between 0 and %s.') % child_age_max
#                         )

#         # Tour date validation
#         if tour_type and tour_id and tour and travel_date:
#             if tour_type == 'day' and travel_date != tour.date:
#                 self.add_error('travel_date', _('Travel date must be %s for this Day Tour.') % tour.date)
#             elif tour_type != 'day' and tour.start_date and tour.end_date:
#                 if not (tour.start_date <= travel_date <= tour.end_date):
#                     self.add_error('travel_date', _('Travel date must be between %s and %s.') % (tour.start_date, tour.end_date))
#                 duration_days = getattr(tour, 'duration_days', 0)
#                 end_date = travel_date + timedelta(days=duration_days - 1)
#                 if end_date > tour.end_date:
#                     self.add_error('travel_date', _('Selected date plus %s days exceeds tour end date %s.') % (duration_days, tour.end_date))

#         logger.debug(f"cleaned_data: {cleaned_data}")
#         return cleaned_data

#     def save(self, commit=True):
#         proposal = super().save(commit=False)
#         proposal.infants = self.cleaned_data.get('infants', 0)
#         proposal.children_ages = self.cleaned_data.get('child_ages', [])
#         proposal.content_type = self.get_content_type()
#         proposal.object_id = self.cleaned_data.get('tour_id')
#         proposal.currency = self.cleaned_data.get('currency')

#         if commit:
#             proposal.save()
#             self.save_m2m()
#             for lang_code, translation_data in self.get_translated_fields().items():
#                 self.instance.set_current_language(lang_code)
#                 for field_name, value in translation_data.items():
#                     setattr(self.instance, field_name, value)
#                 self.instance.save()

#         return proposal

#     def get_content_type(self):
#         model_map = {
#             'full': FullTour,
#             'land': LandTour,
#             'day': DayTour
#         }
#         model = model_map.get(self.cleaned_data.get('tour_type', '').lower())
#         if model:
#             return ContentType.objects.get_for_model(model)
#         return None

# class BookingForm(TranslatableModelForm):
#     TOUR_TYPE_CHOICES = [
#         ('full', _('Full Tour')),
#         ('land', _('Land Tour')),
#         ('day', _('Day Tour')),
#     ]
#     tour_type = forms.ChoiceField(choices=TOUR_TYPE_CHOICES, label=_("Tour Type"))
#     tour_id = forms.ChoiceField(label=_("Tour ID"), widget=forms.Select(attrs={'class': 'form-select'}))

#     class Meta:
#         model = Booking
#         fields = [
#             'customer_name', 'customer_email', 'customer_phone', 'customer_address',
#             'nationality', 'notes', 'tour_type', 'tour_id', 'number_of_adults',
#             'number_of_children', 'travel_date', 'payment_method',
#         ]
#         widgets = {
#             'travel_date': forms.DateInput(attrs={'type': 'text', 'class': 'form-control', 'id': 'id_travel_date'}),
#             'customer_address': forms.Textarea(attrs={'rows': 3}),
#             'notes': forms.Textarea(attrs={'rows': 3}),
#         }
#         labels = {
#             'customer_name': _("Customer Name"),
#             'customer_email': _("Email"),
#             'customer_phone': _("Phone"),
#             'customer_address': _("Address"),
#             'nationality': _("Nationality"),
#             'notes': _("Additional Notes"),
#             'number_of_adults': _("Number of Adults"),
#             'number_of_children': _("Number of Children"),
#             'travel_date': _("Travel Date"),
#             'payment_method': _("Payment Method"),
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         tour_type = self.data.get('tour_type') or self.initial.get('tour_type')
#         self.fields['tour_id'].choices = [('', _("Select a tour"))]
#         if tour_type:
#             model_map = {
#                 'full': FullTour,
#                 'land': LandTour,
#                 'day': DayTour,
#             }
#             model = model_map.get(tour_type)
#             if model:
#                 self.fields['tour_id'].choices = [
#                     ('', _("Select a tour")),
#                     *[(str(t.pk), f"{t.safe_translation_getter('title', 'Untitled')} ({t.code_id})")
#                       for t in model.objects.filter(available_slots__gt=0)]
#                 ]
#         if 'initial' in kwargs and 'tour_id' in kwargs['initial']:
#             self.fields['tour_id'].initial = str(kwargs['initial']['tour_id'])
#         if 'number_of_adults' not in self.initial:
#             self.initial['number_of_adults'] = 1

#     def clean(self):
#         cleaned_data = super().clean()
#         tour_type = cleaned_data.get('tour_type')
#         tour_id = cleaned_data.get('tour_id')
#         travel_date = cleaned_data.get('travel_date')
#         number_of_adults = cleaned_data.get('number_of_adults', 0)
#         number_of_children = cleaned_data.get('number_of_children', 0)

#         if not tour_type:
#             self.add_error('tour_type', _("Tour type is required."))
#         if not tour_id:
#             self.add_error('tour_id', _("Please select a tour."))
#         if not travel_date:
#             self.add_error('travel_date', _("Travel date is required."))
#         if number_of_adults is not None and number_of_adults < 1:
#             self.add_error('number_of_adults', _("At least one adult is required."))
#         if not cleaned_data.get('customer_name'):
#             self.add_error('customer_name', _("Customer name is required."))
#         if not cleaned_data.get('customer_email'):
#             self.add_error('customer_email', _("Email is required."))

#         if tour_type and tour_id and travel_date:
#             model_map = {
#                 'full': FullTour,
#                 'land': LandTour,
#                 'day': DayTour,
#             }
#             model = model_map.get(tour_type)
#             if model:
#                 try:
#                     tour = model.objects.get(pk=tour_id)
#                     content_type = ContentType.objects.get_for_model(model)
#                     if tour_type == 'day':
#                         if travel_date != tour.date:
#                             self.add_error('travel_date', _("Travel date must be %s for this Day Tour.") % tour.date)
#                     else:
#                         if not (tour.start_date <= travel_date <= tour.end_date):
#                             self.add_error('travel_date', _("Travel date must be between %s and %s.") % (tour.start_date, tour.end_date))
#                         duration_days = getattr(tour, 'duration_days', 0)
#                         end_date = travel_date + timedelta(days=duration_days - 1)
#                         if end_date > tour.end_date:
#                             self.add_error('travel_date', _("Selected date plus %s days exceeds tour end date %s.") % (duration_days, tour.end_date))
#                     bookings = Booking.objects.filter(
#                         content_type=content_type,
#                         object_id=tour.id,
#                         travel_date=travel_date,
#                         status__in=['PENDING', 'CONFIRMED']
#                     ).aggregate(total_adults=Sum('number_of_adults'), total_children=Sum('number_of_children'))
#                     total_bookings = (bookings['total_adults'] or 0) + (bookings['total_children'] or 0)
#                     requested_slots = number_of_adults + number_of_children
#                     if total_bookings + requested_slots > tour.max_capacity:
#                         self.add_error('travel_date', _("No available slots for %s. Maximum capacity reached.") % travel_date)
#                 except model.DoesNotExist:
#                     self.add_error('tour_id', _("Selected tour does not exist or is unavailable."))
#             else:
#                 self.add_error('tour_type', _("Invalid tour type."))
#         return cleaned_data

#     def save(self, commit=True):
#         instance = super().save(commit=False)
#         tour_type = self.cleaned_data['tour_type']
#         tour_id = self.cleaned_data['tour_id']
#         model_map = {
#             'full': FullTour,
#             'land': LandTour,
#             'day': DayTour,
#         }
#         model = model_map[tour_type]
#         instance.content_type = ContentType.objects.get_for_model(model)
#         instance.object_id = tour_id
#         instance.total_price = instance.calculate_total_price()
#         if commit:
#             instance.save()
#             self.save_m2m()
#         return instance
