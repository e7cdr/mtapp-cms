
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from datetime import timedelta
import os
from pathlib import Path
from decouple import config
from django.conf import settings

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

# Sensitive keys from environment variables
SECRET_KEY = config('SECRET_KEY')
OPEN_EXCHANGE_RATES_API_KEY = config('OPEN_EXCHANGE_RATES_API_KEY')
GOOGLE_TRANSLATE_KEY = config('GOOGLE_TRANSLATE_KEY')

# Application definition

INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',

    # Third-party – put these early
    'import_export',                  # ← regular django-import-export

    # Wagtail core apps (order matters!)
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.contrib.settings',
    'wagtail.contrib.routable_page',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',                  # ← wagtail_import_export must be above this
    'wagtail',                        # or 'wagtail.core' in very old versions

    # Rest of Wagtail ecosystem
    'wagtail_localize',
    'wagtail_localize.locales',
    'wagtailseo',
    'wagtailcache',
    # 'wagtail.contrib.sitemaps',

    # Other third-party
    'modelcluster',
    'taggit',
    'rest_framework',
    "rest_framework.authtoken",
    'wagtail.api.v2',


    'axes',  # For login attempt locking
    'allauth',
    'allauth.account',
    'allauth.socialaccount',  # Optional: for social logins later
    'django_ratelimit',  # For form throttling
    "accounts",
    "home",
    "blog",
    "images",
    "documents",
    "search",
    "flex",
    "streams",
    "parler",
    "site_settings",
    "rosetta",
    "tours",
    "bookings",
    "partners",
    "p_methods",
    "profiles",
    'revenue_management',
    'captcha',
    # "staff_tools",
]



MIDDLEWARE = [  # Order matters
    'wagtailcache.cache.UpdateCacheMiddleware',
    "django.middleware.security.SecurityMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",  # CORRECT: Django's sites middleware
    "allauth.account.middleware.AccountMiddleware",
    "axes.middleware.AxesMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    'wagtailcache.cache.FetchFromCacheMiddleware',
]

ROOT_URLCONF = "mtapp.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'django.template.context_processors.i18n',
                "wagtail.contrib.settings.context_processors.settings",
                "site_settings.context_processors.navbar",
            ],
        },
    },
]

# Auth backends (include Axes for locking)
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # Axes first for locking
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Allauth settings
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'  # Users verify email before login
ACCOUNT_LOGIN_METHODS = {'email'}  # Login with email
SITE_ID = 1  # Required for allauth

# Axes settings (lock after 5 failed attempts for 15 mins; customize per your risk level)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)

# Ratelimit
RATELIMIT_ENABLE = True
RATELIMIT_VIEW = 'accounts.views.ratelimit_exceeded'  # Fallback 403 page
RATELIMIT_CACHE = 'default'  # Uses the shared cache above

# CAPTCHA: Reduce blurriness/distortion
CAPTCHA_NOISE = 0  # FIXED: 0 = clean (no lines/curves); 1 = minimal dots; 2 = default lines
CAPTCHA_HIGH_SECURITY = False  # Optional: Disables extra distortion if True
CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.math_challenge'  # Keep math; switch to 'word' for text if preferred
CAPTCHA_FONTS = ['/path/to/static/fonts/clean_font.ttf']  # Optional: Upload a bold, clear TTF (e.g., Arial Bold) to static/fonts/ for sharper text
CAPTCHA_FOREGROUND_COLOR = '#000000'  # Black text for contrast
CAPTCHA_BACKGROUND_COLOR = '#ffffff'  # White bg (less gray = crisper)
CAPTCHA_IMAGE_SIZE = (200, 35)  # Wider/shorter for easier reading (default 200x75)
CAPTCHA_TIMEOUT = 10  # Longer expiry = less re-solves
CAPTCHA_OUTPUT_FORMAT = '<div class="captcha-wrapper">%(image)s <input type="text" name="%(text_field)s" id="%(text_field_id)s">%(hidden_field)s</div>'  # Custom: Image + input side-by-side

WSGI_APPLICATION = "mtapp.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"

USE_I18N = True
USE_L10N = True
USE_TZ = True


# Wagtail internationalization settings
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES = [
    ('en', 'English'),
    ('es', 'Spanish'),
    ('fr', 'French'),
    ('is', 'Icelandic'),
    ('pl', 'Polski'),
]

LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]

WAGTAIL_LOCALIZE_TRANSLATE_UI = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES


STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    'compressor.finders.CompressorFinder',
]

STATICFILES_DIRS = [
    os.path.join(PROJECT_DIR, "static"),
]

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# Default storage settings
# See https://docs.djangoproject.com/en/4.2/ref/settings/#std-setting-STORAGES
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

ADMINS = [('e7c', 'evc1893@gmail.com')]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Django sets a maximum of 1000 fields per form by default, but particularly complex page models
# can exceed this limit within Wagtail's page editor.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10_000


# Wagtail settings

WAGTAIL_SITE_NAME = "mtapp"

# Search
# https://docs.wagtail.org/en/stable/topics/search/backends.html
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}

# Base URL to use when referring to full URLs within the Wagtail admin backend -
# e.g. in notification emails. Don't include '/admin' or a trailing slash

# Allowed file extensions for documents in the document library.
# This can be omitted to allow all files, but note that this may present a security risk
# if untrusted users are allowed to upload files -
# see https://docs.wagtail.org/en/stable/advanced_topics/deploying.html#user-uploaded-files
WAGTAILDOCS_EXTENSIONS = ['csv', 'docx', 'key', 'odt', 'pdf', 'pptx', 'rtf', 'txt', 'xlsx', 'zip']
WAGTAILDOCS_DOCUMENT_MODEL = 'documents.CustomDocument'



# Logging.debugger configuration

logs_dir = Path(BASE_DIR) / 'logs'
logs_dir.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {module} {message}',
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
            'filename': os.path.join(BASE_DIR, 'logs', 'full_error.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.server': {
            'handlers': ['console', 'file'],
            'level': 'INFO',          # This is the missing piece
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.template': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

WAGTAILIMAGES_FORMAT_CONVERSIONS = {
    'gif': 'gif',
    'webp': 'webp',
    'ico': 'ico',
    'jpg': 'jpg',
    'png': 'png',
}

WAGTAILIMAGES_EXTENSIONS = ['gif', 'ico', 'jpeg', 'png', 'svg', 'jpg']
WAGTAILIMAGES_DEFAULT_LAZY_ATTRIBUTES = {
    'loading': 'lazy',
    'decoding': 'async',
}

WAGTAILADMIN_RICH_TEXT_EDITORS = {
    'default': {
        'WIDGET': 'wagtail.admin.rich_text.DraftailRichTextArea',
        # since sub, super, and a couple more are not included by default, we need to add them in this config
        'OPTIONS': {'features': ['bold', 'italic', 'superscript', 'subscript', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ol', 'ul',
                        'hr', 'blockquote', 'link', 'embed', 'document-link', 'image', 'code']}
    },
    'minimal': {
        'OPTIONS': {
            'features': ['bold', 'italic', 'subscript', 'superscript', 'link']
        }
    }
}

# API

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 11,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],

}

SESSION_COOKIE_AGE = 30 * 60 

WAGTAILAPI_LIMIT_TO_REGISTERED_USERS = True

# Token for CSV export
WAGTAIL_API_TOKEN = "e721f0ae2b34243f890464bb23978fe639bb78e4"


INSTALLED_APPS += ['compressor']
STATICFILES_FINDERS += ['compressor.finders.CompressorFinder']

# django-compressor settings — MUST be like this
COMPRESS_ENABLED = True
COMPRESS_OFFLINE = True
COMPRESS_URL = STATIC_URL
COMPRESS_ROOT = STATIC_ROOT

# This makes the filename change when content changes
COMPRESS_OUTPUT_DIR = 'CACHE'
COMPRESS_TEMPLATE_FILTER = True
COMPRESS_PRECOMPILERS = ()

from django.views.static import serve as static_serve
from django.views.decorators.cache import cache_control

@cache_control(max_age=31536000, immutable=True)
def media_serve(request, path, document_root=None):
    return static_serve(request, path, document_root)