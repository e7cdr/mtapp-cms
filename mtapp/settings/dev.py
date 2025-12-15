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
WAGTAILADMIN_BASE_URL = "127.0.0.1:8000"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# dev.py — ADD THESE LINES

if DEBUG:
    # === DISABLE ALL CACHING IN DEVELOPMENT ===
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
    
    # Disable Wagtail page cache
    WAGTAIL_CACHE = False
    

    
    # Whitenoise — no cache
    WHITENOISE_AUTOREFRESH = True
    WHITENOISE_MAX_AGE = 0
    
    # Compressor — off
    COMPRESS_ENABLED = False

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

WAGTAIL_CACHE_BACKEND = 'default'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",  # ← THIS WINS IN DEV
    },
}

# DEFAULT_FILE_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
COMPRESS_OFFLINE = False
COMPRESS_ENABLED = False

# WHITENOISE_MAX_AGE = 60 * 60 
# WHITENOISE_IMMUTABLE_FILE_TEST = lambda path, url: True  # Treat all static/media as immutable


CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',  # Local Redis; adjust for prod (e.g., REDIS_URL env var)
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'debug.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',   # ← This catches everything by default
    },
    'loggers': {
        # Django core
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',   # Keeps server GET/POST lines
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',  # 404s, 500s, etc.
            'propagate': False,
        },
        # Your app — this is the key line
        'bookings': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',   # ← Now all logger.debug() in bookings/ will show
            'propagate': False,
        },
        # Optional: catch-all for any other app
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}