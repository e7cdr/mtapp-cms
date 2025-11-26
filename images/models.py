from django.db import models

from wagtail.images.models import AbstractImage, AbstractRendition, Image


class CustomImage(AbstractImage):
    caption = models.CharField(max_length=255, blank=True)
    photographer = models.CharField(max_length=100, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    admin_form_fields = Image.admin_form_fields + ('caption', 'photographer')

    def __str__(self):
        return f"{self.caption} by {self.photographer}" if self.caption else "Untitled Image"
    
class CustomRendition(AbstractRendition):
    image = models.ForeignKey(
        CustomImage, on_delete=models.CASCADE, related_name='renditions'
    )
    
    class Meta:
        unique_together = (('image', 'filter_spec', 'focal_point_key'),)