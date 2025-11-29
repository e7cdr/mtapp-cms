import json
import logging
from django import forms
from datetime import timedelta
from django.db.models import Sum
from .models import Booking, Proposal, ExchangeRate
from tours.models import DayTourPage, FullTourPage, LandTourPage
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from captcha.fields import CaptchaField

logger = logging.getLogger(__name__)

class ProposalForm(forms.ModelForm):  # Changed to ModelForm
    tour_type = forms.CharField(max_length=20, required=True)
    tour_id = forms.IntegerField(min_value=1, required=True)
    travel_date = forms.DateField(required=True)
    end_date = forms.DateField(required=False)
    number_of_adults = forms.IntegerField(min_value=1, required=True)
    number_of_children = forms.IntegerField(min_value=0, required=False)
    child_ages = forms.JSONField(required=False, initial=[])
    customer_name = forms.CharField(max_length=200, required=False)
    customer_email = forms.EmailField(required=False)
    customer_phone = forms.CharField(max_length=20, required=False)
    nationality = forms.CharField(max_length=100, required=False)
    customer_address = forms.CharField(widget=forms.Textarea, required=False)
    notes = forms.CharField(widget=forms.Textarea, required=False)
    form_submission = forms.CharField(max_length=20, required=False, initial='pricing')
    selected_configuration = forms.CharField(max_length=255, required=False)
    currency = forms.ChoiceField(
        choices=lambda: [(rate.currency_code, rate.currency_code) for rate in ExchangeRate.objects.all()] + [('USD', 'USD')],
        required=True,
        initial='USD',
        help_text=_("Select the currency for pricing")
    )
    captcha = CaptchaField()

    class Meta:
        model = Proposal
        fields = [
            'tour_type', 'tour_id', 'customer_name', 'customer_email', 'customer_phone',
            'customer_address', 'nationality', 'number_of_adults', 'number_of_children',
            'travel_date', 'notes', 'child_ages', 'selected_configuration', 'selected_config',
            'captcha',
        ]
        widgets = {
            'travel_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'text'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'number_of_adults': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'number_of_children': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'child_ages': forms.HiddenInput(),
            'selected_configuration': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        self.tour = kwargs.pop('tour', None)
        super().__init__(*args, **kwargs)

        # Determine if this tour allows pricing
        self.collect_price = getattr(self.tour, 'collect_price', True) if self.tour else True
        self.is_inquiry_only = not self.collect_price

        # Get current mode (from POST or initial)
        form_submission = (
            self.data.get('form_submission', 'pricing') if self.data
            else self.initial.get('form_submission', 'pricing')
        )

        if self.is_inquiry_only:
            # INQUIRY-ONLY MODE: Remove pricing fields, force contact required
            for field_name in ['currency', 'selected_configuration', 'selected_config']:
                self.fields.pop(field_name, None)

            # Make contact fields REQUIRED
            required_fields = [
                'customer_name', 'customer_email', 'customer_phone',
                'nationality'
            ]
            for field in required_fields:
                if field in self.fields:
                    self.fields[field].required = True

            # Ensure travel date and pax are required
            self.fields['travel_date'].required = True
            self.fields['number_of_adults'].required = True

        else:
            # NORMAL PRICING MODE
            if form_submission == 'pricing':
                for field in ['customer_name', 'customer_email', 'customer_phone',
                            'nationality']:
                    self.fields[field].required = False


    def clean_child_ages(self):
        number_of_children = self.cleaned_data.get('number_of_children', 0) or 0  # Guard None → 0
        if number_of_children == 0:
            return []

        # Collect from dynamic selects (child_age_1, etc.)
        child_ages = []
        for i in range(1, number_of_children + 1):
            age_str = self.data.get(f'child_age_{i}', '')
            try:
                age = int(age_str) if age_str else self.tour.child_age_min if hasattr(self, 'tour') else 7
                max_age = self.tour.child_age_max if hasattr(self, 'tour') else 12
                if not (0 <= age <= max_age):
                    raise ValueError('Age out of range')
                child_ages.append(age)
            except (ValueError, TypeError):
                raise forms.ValidationError(_('Invalid age for child {}. Must be 0-{}').format(i, max_age))

        # Fallback to comma if no selects
        if not child_ages:
            ages_str = self.data.get('child_ages', '[]')
            try:
                ages = json.loads(ages_str) if ages_str else []
                child_ages = [int(age) for age in ages[:number_of_children] if str(age).isdigit()]
                if len(child_ages) < number_of_children:
                    child_ages.extend([self.tour.child_age_min if hasattr(self, 'tour') else 7] * (number_of_children - len(child_ages)))
            except (json.JSONDecodeError, ValueError):
                child_ages = [self.tour.child_age_min if hasattr(self, 'tour') else 7] * number_of_children

        if len(child_ages) != number_of_children:
            raise forms.ValidationError(_('Number of child ages must match number of children.'))

        return child_ages


    def clean(self):
        cleaned_data = super().clean()
        tour_type = cleaned_data.get('tour_type')
        tour_id = cleaned_data.get('tour_id')
        travel_date = cleaned_data.get('travel_date')
        number_of_adults = cleaned_data.get('number_of_adults', 0) or 0  # Guard None → 0
        number_of_children = cleaned_data.get('number_of_children', 0) or 0  # Guard None → 0

        if not tour_type:
            self.add_error('tour_type', _("Tour type is required."))
        if not tour_id:
            self.add_error('tour_id', _("Please select a tour."))
        if not travel_date:
            self.add_error('travel_date', _("Travel date is required."))
        if number_of_adults < 1:
            self.add_error('number_of_adults', _("At least one adult is required."))
        if not cleaned_data.get('customer_name'):
            self.add_error('customer_name', _("Customer name is required."))
        if not cleaned_data.get('customer_email'):
            self.add_error('customer_email', _("Email is required."))

        if tour_type and tour_id and travel_date:
            model_map = {
                'full': "FullTourPage",
                'land': LandTourPage,
                'day': "DayTourPage",
            }
            model = model_map.get(tour_type)
            if model:
                try:
                    tour = model.objects.get(pk=tour_id)
                    content_type = ContentType.objects.get_for_model(model)
                    if tour_type == 'day':
                        if travel_date != tour.date:
                            self.add_error('travel_date', _("Travel date must be %s for this Day Tour.") % tour.date)
                    else:
                        if not (tour.start_date <= travel_date <= tour.end_date):
                            self.add_error('travel_date', _("Travel date must be between %s and %s.") % (tour.start_date, tour.end_date))
                        duration_days = getattr(tour, 'duration_days', 0)
                        end_date = travel_date + timedelta(days=duration_days - 1)
                        if end_date > tour.end_date:
                            self.add_error('travel_date', _("Selected date plus %s days exceeds tour end date %s.") % (duration_days, tour.end_date))
                    bookings = Booking.objects.filter(
                        content_type=content_type,
                        object_id=tour.id,
                        travel_date=travel_date,
                        status__in=['PENDING', 'CONFIRMED']
                    ).aggregate(total_adults=Sum('number_of_adults'), total_children=Sum('number_of_children'))
                    total_bookings = (bookings['total_adults'] or 0) + (bookings['total_children'] or 0)
                    requested_slots = number_of_adults + number_of_children
                    if total_bookings + requested_slots > tour.max_capacity:
                        self.add_error('travel_date', _("No available slots for %s. Maximum capacity reached.") % travel_date)
                except model.DoesNotExist:
                    self.add_error('tour_id', _("Selected tour does not exist or is unavailable."))
            else:
                self.add_error('tour_type', _("Invalid tour type."))
            # Explicit defaults for DB constraints
        cleaned_data['number_of_children'] = cleaned_data.get('number_of_children', 0) or 0
        # Similarly for other potential None fields
        cleaned_data['number_of_adults'] = cleaned_data.get('number_of_adults', 1) or 1
        return cleaned_data

    def save(self, commit=True):
        proposal = super().save(commit=False)
        proposal.infants = self.cleaned_data.get('infants', 0)
        proposal.children_ages = self.cleaned_data.get('child_ages', [])
        proposal.content_type = self.get_content_type()
        proposal.object_id = self.cleaned_data.get('tour_id')
        proposal.currency = self.cleaned_data.get('currency')

        if commit:
            proposal.save()
            self.save_m2m()
            for lang_code, translation_data in self.get_translated_fields().items():
                self.instance.set_current_language(lang_code)
                for field_name, value in translation_data.items():
                    setattr(self.instance, field_name, value)
                self.instance.save()

        return proposal

    def get_content_type(self):
        model_map = {'full': FullTourPage, 'land': LandTourPage, 'day': DayTourPage}
        model = model_map.get(self.cleaned_data.get('tour_type', '').lower())
        if model:
            return ContentType.objects.get_for_model(model)
        return None
    
    def clean_travel_date(self):
        travel_date = self.cleaned_data.get('travel_date')
        if not travel_date:
            return travel_date

        tour = getattr(self, 'tour', None)  # Safely get the tour instance passed in __init__
        if tour and hasattr(tour, 'blackout_dates') and travel_date in tour.blackout_dates:
            raise forms.ValidationError(_("This date is blacked out and unavailable."))

        return travel_date
    
    

