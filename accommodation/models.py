from django.db import models

from wagtail.models import Page


class BaseDistribution(Page):
    distribution = ListBlock
