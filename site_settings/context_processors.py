from wagtail.models import Page
from tours.models import LandTourPage

def navbar(request):

    return {
        "navbar_menu": Page.objects.live().in_menu().public(),
        
    }