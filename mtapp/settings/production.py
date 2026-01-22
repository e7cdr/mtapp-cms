from .base import *
from decouple import config


DEBUG = False
ALLOWED_HOSTS = [
    'milanotravel.com.ec',
    'www.milanotravel.com.ec',
    'milanotravel.pythonanywhere.com',
    # Optional: catch any subdomains
    '.milanotravel.com.ec',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='www.milanotravel.com.ec'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}
SITE_URL = 'www.milanotravel.com.ec'

# EMAIL Backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='mail.milanotravel.com.ec')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'reservations@milanotravel.com.ec'

# Optional: Sessions on cache too (frees DB)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
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

# Google Cloud Storage (appears in your Google Drive if you want)
DEFAULT_FILE_STORAGE = 'storages.backends.googlecloud.GoogleCloudStorage'
# STATICFILES_STORAGE = 'storages.backends.googlecloud.GoogleCloudStorage'
GS_BUCKET_NAME = 'your-project-backups-and-media'
GS_PROJECT_ID = 'your-gcp-project-id'

# dbbackup → same bucket
DBBACKUP_STORAGE = 'storages.backends.googlecloud.GoogleCloudStorage'
DBBACKUP_STORAGE_OPTIONS = {
    'bucket_name': GS_BUCKET_NAME,
    'location': 'backups/',   # optional subfolder
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 2000,
        }
    }
}

WAGTAILADMIN_BASE_URL = "https://www.milanotravel.com.ec"

# wagtail-cache specific (uses the 'default' cache)
WAGTAIL_CACHE_BACKEND = 'default'

WHITENOISE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days for immutable files (CSS, JS, images, fonts)
WHITENOISE_IMMUTABLE_FILE_TEST = r'\.[0-9a-f]{8,}\.'

COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.rCSSMinFilter',
]
COMPRESS_JS_FILTERS = [
    'compressor.filters.jsmin.rJSMinFilter',
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",  # ← Only in prod
    },
}

WHITENOISE_MIMETYPES = {
    '.png': 'image/png',
    '.jpg': 'image/jpg',
}


try:
    from .local import *
except ImportError:
    pass

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
