
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from datetime import timedelta
import os
from pathlib import Path
from decouple import config
from django.conf import settings

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

SITE_URL = 'www.milanotravel.com.ec'

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
    "django.middleware.security.SecurityMiddleware",
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


# Wagtail internationalization settings
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES = [
    ('en', 'English'),
    ('es', 'Spanish'),
    ('fr', 'French'),
    ('is', 'Icelandic'),
    ('pl', 'Polski'),
]

USE_TZ = True


STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
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
WAGTAILADMIN_BASE_URL = "https://www.milanotravel.com.ec"

# Allowed file extensions for documents in the document library.
# This can be omitted to allow all files, but note that this may present a security risk
# if untrusted users are allowed to upload files -
# see https://docs.wagtail.org/en/stable/advanced_topics/deploying.html#user-uploaded-files
WAGTAILDOCS_EXTENSIONS = ['csv', 'docx', 'key', 'odt', 'pdf', 'pptx', 'rtf', 'txt', 'xlsx', 'zip']


logs_dir = Path(BASE_DIR) / 'logs'
logs_dir.mkdir(exist_ok=True)

# Logging.debugger configuration

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',  # Low for full errors
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.request': {  # For 500s
            'handlers': ['console'],
            'level': 'DEBUG',  # Temp DEBUG for tracebacks
            'propagate': True,
        },
        'django.template': {  # For static/template errors
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'mtapp.tours.models': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'wagtail_localize': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'wagtail': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.core.mail': {  # NEW: Catches SMTP connect/send details
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'smtplib': {  # NEW: Low-level SMTP server responses
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}


WAGTAILIMAGES_FORMAT_CONVERSIONS = {
    'gif': 'gif',
    'webp': 'webp',
    'ico': 'ico',
    'jpg': 'jpg',
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

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'default',  # Uses your main DB
        'TIMEOUT': 300,  # 5 min default; tune for ratelimit
        'OPTIONS': {
            'MAX_ENTRIES': 1000,  # Soft limit; evict old if full
            'CULL_FREQUENCY': 3,  # Check for eviction 1/3 of time
        },
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

WAGTAILAPI_LIMIT_TO_REGISTERED_USERS = True

# Token for CSV export
WAGTAIL_API_TOKEN = "e721f0ae2b34243f890464bb23978fe639bb78e4"


