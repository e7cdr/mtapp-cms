from django import forms
from .models import StaffTask, TourAvailability, CommunicationLog
from bookings.models import Booking
from tours.models import FullTour, LandTour, DayTour
from partners.models import Partner
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from parler.forms import TranslatableModelForm

class StaffTaskForm(TranslatableModelForm):
    class Meta:
        model = StaffTask
        fields = ['title', 'description', 'due_date', 'priority', 'status', 'related_booking', "assigned_to"]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'title': _("Task Title"),
            'description': _("Description"),
            'due_date': _("Due Date"),
            'priority': _("Priority"),
            'status': _("Status"),
            'related_booking': _("Related Booking"),
            'assigned_to': _("User")
        }

class BookingUpdateForm(TranslatableModelForm):
    class Meta:
        model = Booking
        fields = ['status', 'payment_method', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'status': _("Status"),
            'payment_method': _("Payment Method"),
            'notes': _("Notes"),
        }

class TourAvailabilityForm(TranslatableModelForm):
    TOUR_TYPE_CHOICES = [
        ('full', _('Full Tour')),
        ('land', _('Land Tour')),
        ('day', _('Day Tour')),
    ]
    tour_type = forms.ChoiceField(choices=TOUR_TYPE_CHOICES, label=_("Tour Type"))
    tour_id = forms.ChoiceField(label=_("Select Tour"), choices=[])

    class Meta:
        model = TourAvailability
        fields = ['tour_type', 'tour_id', 'current_slots', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'current_slots': _("Current Slots"),
            'notes': _("Notes"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'tour_type' in self.data:
            tour_type = self.data.get('tour_type')
            if tour_type == 'full':
                self.fields['tour_id'].choices = [
                    (t.pk, f"{t.safe_translation_getter('title', 'Untitled')} ({t.code_id})")
                    for t in FullTour.objects.all()
                ]
            elif tour_type == 'land':
                self.fields['tour_id'].choices = [
                    (t.pk, f"{t.safe_translation_getter('title', 'Untitled')} ({t.code_id})")
                    for t in LandTour.objects.all()
                ]
            elif tour_type == 'day':
                self.fields['tour_id'].choices = [
                    (t.pk, f"{t.safe_translation_getter('title', 'Untitled')} ({t.code_id})")
                    for t in DayTour.objects.all()
                ]
        else:
            self.fields['tour_id'].choices = []

    def save(self, commit=True):
        instance = super().save(commit=False)
        tour_type = self.cleaned_data['tour_type']
        tour_id = self.cleaned_data['tour_id']
        if tour_type == 'full':
            instance.content_type = ContentType.objects.get_for_model(FullTour)
            instance.object_id = tour_id
        elif tour_type == 'land':
            instance.content_type = ContentType.objects.get_for_model(LandTour)
            instance.object_id = tour_id
        elif tour_type == 'day':
            instance.content_type = ContentType.objects.get_for_model(DayTour)
            instance.object_id = tour_id
        if commit:
            instance.save()
        return instance

class PartnerForm(TranslatableModelForm):
    class Meta:
        model = Partner
        fields = ['name', 'contact_person', 'email', 'phone', 'address', 'website', 'notes']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'name': _("Partner Name"),
            'contact_person': _("Contact Person"),
            'email': _("Email"),
            'phone': _("Phone"),
            'address': _("Address"),
            'website': _("Website"),
            'notes': _("Notes"),
        }

class CommunicationForm(TranslatableModelForm):
    class Meta:
        model = CommunicationLog
        fields = ['entity_type', 'entity_id', 'method', 'message', 'follow_up_needed', 'follow_up_date']
        widgets = {
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'message': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'entity_type': _("Entity Type"),
            'entity_id': _("Entity"),
            'method': _("Method"),
            'message': _("Message"),
            'follow_up_needed': _("Follow-up Needed"),
            'follow_up_date': _("Follow-up Date"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'entity_type' in self.data:
            entity_type = self.data.get('entity_type')
            if entity_type == 'booking':
                self.fields['entity_id'].choices = [
                    (b.pk, f"{b.safe_translation_getter('customer_name', 'Unknown')} ({b.pk})")
                    for b in Booking.objects.all()
                ]
            elif entity_type == 'partner':
                self.fields['entity_id'].choices = [
                    (p.pk, p.safe_translation_getter('name', 'Unknown'))
                    for p in Partner.objects.all()
                ]
        else:
            self.fields['entity_id'].choices = []

class FullTourForm(TranslatableModelForm):
    class Meta:
        model = FullTour
        fields = [
            'title', 'destination', 'description', 'duration_days', 'nights', 'hotel',
            'flight_details', 'price_dbl_regular', 'price_chd_regular',
            'available_slots', 'amenities', 'courtesies'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'flight_details': forms.Textarea(attrs={'rows': 3}),
            'courtesies': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'title': _("Title"),
            'destination': _("Destination"),
            'description': _("Description"),
            'duration_days': _("Duration (Days)"),
            'nights': _("Nights"),
            'hotel': _("Hotel"),
            'flight_details': _("Flight Details"),
            'price_dbl_regular': _("Price (Double, Regular)"),
            'price_chd_regular': _("Price (Child, Regular)"),
            'available_slots': _("Available Slots"),
            'amenities': _("Amenities"),
            'courtesies': _("Courtesies"),
        }

class LandTourForm(TranslatableModelForm):
    class Meta:
        model = LandTour
        fields = [
            'title', 'destination', 'description', 'duration_days', 'nights', 'hotel',
            'price_dbl', 'price_chd', 'available_slots', 'amenities', 'courtesies'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'courtesies': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'title': _("Title"),
            'destination': _("Destination"),
            'description': _("Description"),
            'duration_days': _("Duration (Days)"),
            'nights': _("Nights"),
            'hotel': _("Hotel"),
            'price_dbl': _("Price (Double)"),
            'price_chd': _("Price (Child)"),
            'available_slots': _("Available Slots"),
            'amenities': _("Amenities"),
            'courtesies': _("Courtesies"),
        }
class DayTourForm(TranslatableModelForm):
    class Meta:
        model = DayTour
        fields = [
            'title', 'destination', 'description', 'date', 'duration_hours',
            'price_adult', 'price_child', 'available_slots', 'amenities', 'courtesies'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'courtesies': forms.Textarea(attrs={'rows': 3}),
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'title': _("Title"),
            'destination': _("Destination"),
            'description': _("Description"),
            'date': _("Date"),
            'duration_hours': _("Duration (Hours)"),
            'price_adult': _("Price (Adult)"),
            'price_child': _("Price (Child)"),
            'available_slots': _("Available Slots"),
            'amenities': _("Amenities"),
            'courtesies': _("Courtesies"),
        }