from django.db import models
from django.contrib.auth.models import User
from bookings.models import Booking
from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet


@register_snippet
class Commission(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='commissions',
        help_text=_("The booking associated with this commission.")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='commissions',
        help_text=_("The user who earned this commission.")
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("The commission amount in the booking's currency."),
        default=5.0
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', _('Pending')),
            ('PAID', _('Paid')),
            ('CANCELLED', _('Cancelled')),
        ],
        default='PENDING',
        help_text=_("The status of the commission.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Commission for {self.booking.book_id}: ${self.amount} ({self.status})"
    
        # Meta Options:
    # ordering: Sorts commissions by creation date (newest first).
    # indexes: Optimizes queries for filtering by user and date or booking and status.
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['booking', 'status']),
        ]