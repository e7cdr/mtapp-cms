from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from django.conf.urls.i18n import i18n_patterns
from django.contrib.sitemaps.views import sitemap

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from .views import RobotsView

from .sitemaps import ImageSitemap, PageSitemap
from search import views as search_views
from accounts.views import captcha_refresh
from bookings.api_views import AvailableDatesView
from .api import api_router


sitemaps = {
    'pages': PageSitemap, 
    'images': ImageSitemap, # You can add more dict entries for images/videos
}

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    # path('test-hook/', test_hook, name='test-hook'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', RobotsView.as_view(), name='robots'),
    path("documents/", include(wagtaildocs_urls)),
    path('api/available-dates/', AvailableDatesView.as_view(), name='available_dates_api'),
    path('bookings/', include('bookings.urls', namespace='bookings')),
    path('p-methods/', include('p_methods.urls', namespace='p_methods')),
    path('captcha/', include('captcha.urls')),
    path('api/v2/', api_router.urls),    
    path('api/captcha-refresh/', captcha_refresh, name='captcha_refresh'),
    ]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + i18n_patterns (
    path('i18n/', include('django.conf.urls.i18n')),
    path("search/", search_views.search, name="search"),
    path('profile/', include('profiles.urls')),
    path('accounts/', include('accounts.urls')),




    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
)
