from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms import ValidationError
from tours.models import FullTour, LandTour, DayTour
from parler.models import TranslatableModel, TranslatedFields
from django.contrib.auth.models import User 
from django.utils.translation import gettext_lazy as _




'''
Performance:
The clean() method queries the database (model_class.objects.get(pk=self.object_id)) for every validation. 
For bulk operations, this could be slow. You might optimize by caching or skipping in certain contexts (e.g., migrations).

Error Messages:
Customize the ValidationError messages if needed for user-friendliness.
'''

class TourAvailability(TranslatableModel):
    translations = TranslatedFields(
        notes=models.TextField(blank=True, help_text=_("Notes on availability changes")),
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('tours.fulltour', 'tours.landtour', 'tours.daytour')}
    )
    object_id = models.PositiveIntegerField()
    tour = GenericForeignKey('content_type', 'object_id')
    current_slots = models.PositiveIntegerField(help_text=_("Current available slots"))
    last_updated = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.content_type:
            raise ValidationError(_("Content type must be specified."))
        
        valid_models = {'FullTour', 'LandTour', 'DayTour'}
        model_class = self.content_type.model_class()
        
        if model_class.__name__ not in valid_models:
            raise ValidationError(
                _("Invalid tour type. Must be one of: %(models)s") % {
                    'models': ', '.join(valid_models)
                }
            )
        
        try:
            model_class.objects.get(pk=self.object_id)
        except model_class.DoesNotExist:
            raise ValidationError(
                _("No %(model)s exists with ID %(id)s") % {
                    'model': model_class.__name__,
                    'id': self.object_id
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.tour:
            self.tour.available_slots = self.current_slots
            self.tour.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return _("Availability for %(tour)s - %(slots)s slots") % {
            'tour': self.tour,
            'slots': self.current_slots
        }

    class Meta:
        verbose_name_plural = "Tour Availabilities"

# Signal to update TourAvailability when a Booking is confirmed
# @receiver(post_save, sender='bookings.Booking')
def update_tour_availability(sender, instance, created, **kwargs):
    if instance.status == 'CONFIRMED' and created:
        tour = instance.tour
        total_people = instance.number_of_adults + instance.number_of_children
        availability, _ = TourAvailability.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(tour),
            object_id=tour.pk,
            defaults={'current_slots': tour.available_slots}
        )
        availability.current_slots = max(0, availability.current_slots - total_people)
        availability.set_current_language('en')
        availability.notes = _("Updated due to booking %(id)s for %(people)s people") % {
            'id': instance.pk,
            'people': total_people
        }
        availability.save()


class CommunicationLog(TranslatableModel):
    translations = TranslatedFields(
        message=models.TextField(help_text=_("Details of the communication")),
    )
    BOOKING_TYPE = 'booking'
    PARTNER_TYPE = 'partner'
    ENTITY_CHOICES = [
        (BOOKING_TYPE, _('Booking')),
        (PARTNER_TYPE, _('Partner')),
    ]
    entity_type = models.CharField(max_length=20, choices=ENTITY_CHOICES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    entity_id = models.PositiveIntegerField()
    entity = GenericForeignKey('content_type', 'entity_id')
    staff_name = models.CharField(max_length=200, help_text=_("Staff member who made the contact"))
    METHOD_CHOICES = [
        ('EMAIL', _('Email')),
        ('PHONE', _('Phone')),
        ('IN_PERSON', _('In Person')),
    ]
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    contact_date = models.DateTimeField(auto_now_add=True)
    follow_up_needed = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)

    def send_email(self):
        if self.method == 'EMAIL' and self.entity_type == self.BOOKING_TYPE:
            booking = self.entity
            send_mail(
                subject=_("Booking Update from Milano Travel - %(id)s") % {'id': booking.pk},
                message=self.safe_translation_getter('message', 'No message'),
                from_email='no-reply@milanotravel.com',
                recipient_list=[booking.customer_email],
                fail_silently=False,
            )
        elif self.method == 'EMAIL' and self.entity_type == self.PARTNER_TYPE:
            partner = self.entity
            send_mail(
                subject=_("Partner Update from Milano Travel - %(name)s") % {
                    'name': partner.safe_translation_getter('name', 'Unknown')
                },
                message=self.safe_translation_getter('message', 'No message'),
                from_email='no-reply@milanotravel.com',
                recipient_list=[partner.email],
                fail_silently=False,
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.method == 'EMAIL':
            self.send_email()

    def __str__(self):
        return _("%(staff)s - %(entity)s on %(date)s") % {
            'staff': self.staff_name,
            'entity': self.entity,
            'date': self.contact_date
        }

    class Meta:
        ordering = ['-contact_date']

class Report(TranslatableModel):
    translations = TranslatedFields(
        title=models.CharField(max_length=200),
    )
    REPORT_TYPES = [
        ('BOOKINGS', _('Bookings Summary')),
        ('REVENUE', _('Revenue Report')),
        ('AVAILABILITY', _('Tour Availability')),
    ]
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    data = models.JSONField(help_text=_("Stores report data in JSON format"))
    start_date = models.DateField()
    end_date = models.DateField()
    generated_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, help_text=_("Staff member who generated the report"))

    def generate_report_data(self):
        from bookings.models import Booking
        if self.report_type == 'BOOKINGS':
            bookings = Booking.objects.filter(travel_date__range=[self.start_date, self.end_date])
            self.data = {
                'total_bookings': bookings.count(),
                'by_status': {
                    'Pending': bookings.filter(status='PENDING').count(),
                    'Confirmed': bookings.filter(status='CONFIRMED').count(),
                    'Cancelled': bookings.filter(status='CANCELLED').count(),
                }
            }
        elif self.report_type == 'REVENUE':
            bookings = Booking.objects.filter(
                travel_date__range=[self.start_date, self.end_date],
                status='CONFIRMED'
            )
            self.data = {
                'total_revenue': float(sum(b.total_price or 0 for b in bookings)),
                'by_tour_type': {
                    'FullTour': float(sum(b.total_price or 0 for b in bookings if isinstance(b.tour, FullTour))),
                    'LandTour': float(sum(b.total_price or 0 for b in bookings if isinstance(b.tour, LandTour))),
                    'DayTour': float(sum(b.total_price or 0 for b in bookings if isinstance(b.tour, DayTour))),
                }
            }
        elif self.report_type == 'AVAILABILITY':
            availabilities = TourAvailability.objects.filter(last_updated__range=[self.start_date, self.end_date])
            self.data = {
                'total_tours': availabilities.count(),
                'average_slots': sum(a.current_slots for a in availabilities) / max(1, availabilities.count()),
            }
        self.save()

    def __str__(self):
        return _("%(title)s (%(type)s) - %(date)s") % {
            'title': self.safe_translation_getter('title', 'Untitled'),
            'type': self.get_report_type_display(),
            'date': self.generated_date
        }

    class Meta:
        ordering = ['-generated_date']

class StaffTask(TranslatableModel):
    translations = TranslatedFields(
        title=models.CharField(max_length=200, help_text=_("e.g., 'Confirm Booking #123'")),
        description=models.TextField(blank=True),
    )
    PRIORITY_CHOICES = [
        ('LOW', _('Low')),
        ('MEDIUM', _('Medium')),
        ('HIGH', _('High')),
    ]
    STATUS_CHOICES = [
        ('OPEN', _('Open')),
        ('IN_PROGRESS', _('In Progress')),
        ('COMPLETED', _('Completed')),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    assigned_to = models.ForeignKey('auth.User', on_delete=models.CASCADE, help_text=_("Staff member assigned"))
    due_date = models.DateField()
    related_booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return _("%(title)s - %(user)s (%(status)s)") % {
            'title': self.safe_translation_getter('title', 'Untitled'),
            'user': self.assigned_to,
            'status': self.get_status_display()
        }

    class Meta:
        ordering = ['due_date']

class DashboardData(TranslatableModel):
    translations = TranslatedFields(
        metric=models.CharField(
            max_length=50,
            unique=True,
            help_text=_("e.g., 'Total Bookings This Month', 'Pending Tasks'")
        ),
    )
    value = models.CharField(max_length=200, help_text=_("String representation of the metric value"))
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return _("%(metric)s: %(value)s") % {
            'metric': self.safe_translation_getter('metric', 'Unknown'),
            'value': self.value
        }

    class Meta:
        verbose_name_plural = "Dashboard Data"

class AutomatedAlert(TranslatableModel):
    translations = TranslatedFields(
        message=models.TextField()
    )
    ALERT_TYPES = [
        ('LOW_AVAILABILITY', _('Low Tour Availability')),
        ('OVERDUE_TASK', _('Overdue Staff Task')),
        ('BOOKING_ISSUE', _('Booking Issue')),
    ]
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    triggered_date = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    related_object_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('related_object_type', 'related_object_id')

    def __str__(self):
        return _("%(type)s - %(message)s (%(status)s)") % {
            'type': self.get_alert_type_display(),
            'message': self.safe_translation_getter('message', 'No message'),
            'status': _('Resolved') if self.is_resolved else _('Active')
        }

    class Meta:
        ordering = ['-triggered_date']
