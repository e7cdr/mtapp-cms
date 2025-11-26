from django.db import models
from wagtail.documents.models import AbstractDocument, Document

class CustomDocument(AbstractDocument):
    description = models.TextField(blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    admin_form_fields = Document.admin_form_fields + ('description',)

    def __str__(self):
        return f"{self.title} uploaded on {self.upload_date}" if self.upload_date else self.title