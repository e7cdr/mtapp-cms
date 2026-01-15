from django.http import HttpResponse


def test_hook(request):
    return HttpResponse("🎉 HOOK WORKS! wagtail_hooks.py is loaded.")

