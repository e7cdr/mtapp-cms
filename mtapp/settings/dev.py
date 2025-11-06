# print("=== LOADING DEV SETTINGS ===")
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-%4-1ofw63^adyqklvg$q(zup=h)ddc#9xt&6cq!=0$8m85#(yx"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

SITE_URL = 'http://127.0.0.1:8000'

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

try:
    from .local import *
except ImportError:
    pass


if not settings.DEBUG:  # Or check os.environ.get('DJANGO_ENV') != 'development'
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='mail.milanotravel.com.ec')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = 'info@milanotravel.com.ec'
if settings.DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 1025
    EMAIL_HOST_USER = ''  # Not needed
    EMAIL_HOST_PASSWORD = ''  # Not needed
    EMAIL_USE_TLS = False  # Not needed for MailHog
    DEFAULT_FROM_EMAIL = 'dev@milanotravel.com.ec'

# Disable HTTPS redirects for local development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0  # Disables HSTS
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
