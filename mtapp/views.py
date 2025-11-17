from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

@method_decorator(cache_page(60 * 60 * 24), name='dispatch')  # Cache for 24h
class RobotsView(TemplateView):
    template_name = 'robots.txt'
    content_type = 'text/plain'  # Forces plain text response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sitemap_url'] = self.request.build_absolute_uri('/sitemap.xml')
        return context
    
    