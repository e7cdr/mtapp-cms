from django.contrib import admin
from django.conf import settings
from django.urls import include, path, re_path
from django.conf.urls.i18n import i18n_patterns

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from django.views.static import serve
from .views import RobotsView
from django.contrib.sitemaps.views import sitemap
from .sitemaps import ImageSitemap, PageSitemap
from search import views as search_views
from accounts.views import captcha_refresh
from bookings.api_views import AvailableDatesView
from .api import api_router

sitemaps = {
    'pages': PageSitemap(),
    'images': ImageSitemap(),
}

urlpatterns = [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django_sitemap'),
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path('robots.txt', RobotsView.as_view(), name='robots'),
    path("documents/", include(wagtaildocs_urls)),
    path('api/available-dates/', AvailableDatesView.as_view(), name='available_dates_api'),
    path('bookings/', include('bookings.urls', namespace='bookings')),
    path('p-methods/', include('p_methods.urls', namespace='p_methods')),
    path('captcha/', include('captcha.urls')),
    path('api/v2/', api_router.urls),
    path('api/captcha-refresh/', captcha_refresh, name='captcha_refresh'),
]

# ─────────────────────────────────────────────────────────────
# DEVELOPMENT ONLY – static + media
# ─────────────────────────────────────────────────────────────
if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ─────────────────────────────────────────────────────────────
# PRODUCTION ONLY – media files with 1-year cache
# ─────────────────────────────────────────────────────────────
else:
    # Only runs when DEBUG=False (i.e. PythonAnywhere production)
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]

# ─────────────────────────────────────────────────────────────
# i18n + Wagtail pages
# ─────────────────────────────────────────────────────────────
urlpatterns = urlpatterns + i18n_patterns(
    path('i18n/', include('django.conf.urls.i18n')),
    path("search/", search_views.search, name="search"),
    path('profile/', include('profiles.urls')),
    path('accounts/', include('accounts.urls')),

    # Wagtail pages – must be last
    path("", include(wagtail_urls)),
)