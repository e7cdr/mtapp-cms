from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

class Partner(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=200, unique=True, help_text=_("Name of the partner company")),
        address=models.TextField(blank=True, help_text=_("Physical address of the partner")),
        notes=models.TextField(blank=True, help_text=_("Additional notes about the partner")),
        contact_person=models.CharField(max_length=200, blank=True, help_text=_("Main contact person")),
    )
    email = models.EmailField(unique=True, help_text=_("Primary email for communication"))
    phone = models.CharField(max_length=20, blank=True, help_text="e.g., +593-99-123-4567")
    website = models.URLField(blank=True, help_text=_("Partner's website, if available"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.safe_translation_getter('name', 'Unknown Partner')

    class Meta:
        ordering = ['created_at']