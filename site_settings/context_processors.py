from wagtail.models import Page

def navbar(request):

    return {
        "navbar_menu": Page.objects.live().in_menu().public(),

    }