# bookings/forms/accommodation_booking_form.py
from datetime import date, timedelta
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page


class AccommodationBookingForm(forms.Form):
    # Hidden fields
    accommodation_id = forms.IntegerField(widget=forms.HiddenInput())

    # Dates
    check_in = forms.DateField(
        label=_("Check-in"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text=_("Arrival date")
    )
    check_out = forms.DateField(
        label=_("Check-out"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text=_("Departure date")
    )

    # Guests
    adults = forms.IntegerField(
        label=_("Adults"),
        min_value=1,
        max_value=20,
        initial=2,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    children = forms.IntegerField(
        label=_("Children (0–12 yrs)"),
        min_value=0,
        max_value=10,
        initial=0,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Dynamic child ages (will be validated in clean())
    child_ages = forms.JSONField(widget=forms.HiddenInput(), required=False)

    # Contact
    name = forms.CharField(
        max_length=200,
        label=_("Full Name"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Doe'})
    )
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'})
    )
    phone = forms.CharField(
        max_length=30,
        label=_("Phone"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+593 99 999 9999'})
    )
    notes = forms.CharField(
        label=_("Special Requests"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Late check-in, dietary needs...'})
    )

    def __init__(self, *args, accommodation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.accommodation = accommodation

        # Populate adults/children choices
        self.fields['adults'].widget.choices = [(i, f"{i} Adult{'s' if i > 1 else ''}") for i in range(1, 21)]
        self.fields['children'].widget.choices = [(i, f"{i} Child{'ren' if i != 1 else ''}") for i in range(0, 11)]

        if accommodation:
            today = date.today()
            self.fields['check_in'].widget.attrs['min'] = today.isoformat()
            self.fields['check_out'].widget.attrs['min'] = (today + timedelta(days=1)).isoformat()

    def clean_accommodation_id(self):
        aid = self.cleaned_data['accommodation_id']
        try:
            page = Page.objects.live().get(id=aid)
            self.accommodation = page.specific  # ← THIS IS CORRECT
        except Page.DoesNotExist:
            raise ValidationError(_("Invalid accommodation selected."))
        return aid

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        adults = cleaned_data.get('adults', 0)
        children = cleaned_data.get('children', 0)

        if check_in and check_out:
            if check_out <= check_in:
                raise ValidationError(_("Check-out must be after check-in."))

            nights = (check_out - check_in).days
            if nights < 1:
                raise ValidationError(_("Minimum stay is 1 night."))
            if nights > 90:
                raise ValidationError(_("Maximum stay is 90 nights."))

        # Validate child ages match number of children
        child_ages = cleaned_data.get('child_ages', [])
        if children > 0:
            if not isinstance(child_ages, list) or len(child_ages) != children:
                raise ValidationError(_("Please provide age for each child."))

        # Optional: capacity check
        if self.accommodation and adults + children > getattr(self.accommodation, 'max_capacity', 20):
            raise ValidationError(_(
                "This accommodation only supports up to {max} guests."
            ).format(max=getattr(self.accommodation, 'max_capacity', 20)))

        return cleaned_data

    def get_nights(self):
        if self.is_valid():
            return (self.cleaned_data['check_out'] - self.cleaned_data['check_in']).days
        return 0

    def get_total_guests(self):
        return (self.cleaned_data.get('adults', 0) or 0) + (self.cleaned_data.get('children', 0) or 0)
    
    