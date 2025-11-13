from .base import *
from decouple import config


DEBUG = True
LOGGING['loggers']['django.request']['level'] = 'DEBUG'
ALLOWED_HOSTS = [config('ALLOWED_HOSTS')]
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='mail.milanotravel.com.ec')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'reservations@milanotravel.com.ec'

# Optional: Sessions on cache too (frees DB)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'


# 5. Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS in production
SECURE_SSL_REDIRECT = True  # if behind proxy, see below
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # Enforce HTTPS for 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SILENCED_SYSTEM_CHECKS = [
    'django_ratelimit.E003',
    'django_ratelimit.W001',
]

try:
    from .local import *
except ImportError:
    pass