from django.db import models
from django.contrib.auth.models import User
from wagtail.snippets.models import register_snippet

@register_snippet
class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'is_staff': True})
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    

    class Meta:
        ordering = ['-created_at']