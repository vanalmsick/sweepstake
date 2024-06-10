# -*- coding: utf-8 -*-
"""
Django settings for sweepstake project.

Generated by 'django-admin startproject' using Django 3.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import os
import pytz
from pathlib import Path
from urllib.parse import urlparse
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
print("Working dir:", BASE_DIR)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-t4@++_fy&@8e670&&s)6p+2glp-o&ms2&_&hc6b!z64q(4pueq")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

MAIN_HOST = os.environ.get("MAIN_HOST", "http://localhost")
HOSTS = os.environ.get("HOSTS", "http://localhost,http://127.0.0.1/,http://0.0.0.0/").split(",")
CSRF_TRUSTED_ORIGINS = HOSTS
ALLOWED_HOSTS = [urlparse(url).netloc for url in HOSTS]
CORS_ALLOWED_ORIGINS = HOSTS


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "celery",
    "general",
    "competition",
    "django_celery_beat",
]
AUTH_USER_MODEL = "general.CustomUser"


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = "sweepstake.urls"

MIGRATION_MODULES = {
    "general": "data.db_migrations.general",
    "competition": "data.db_migrations.competition",
    "preferences": "data.db_migrations.preferences",
    "django_celery_beat": "data.db_migrations.django_celery_beat",
    #    "django_celery_beat_periodictask": "data.db_migrations.django_celery_beat_periodictask",
    "sessions": "data.db_migrations.sessions",
    "auth": "data.db_migrations.auth",
    "authtoken": "data.db_migrations.authtoken",
    "admin": "data.db_migrations.admin",
    "contenttypes": "data.db_migrations.contenttypes",
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sweepstake.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": (
        {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "data/db.sqlite3",
            "OPTIONS": {
                "timeout": 20,  # seconds
            },
        }
        if os.environ.get("POSTGRESQL_HOST", None) is None
        else {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRESQL_DB", "postgres"),
            "USER": os.environ.get("POSTGRESQL_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRESQL_PASSWORD", "postgres"),
            "HOST": os.environ.get("POSTGRESQL_HOST", "localhost"),
            "PORT": "",
        }
    )
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en-uk"

TIME_ZONE = CELERY_TIMEZONE = os.environ.get("TIME_ZONE", "Europe/London")
TIME_ZONE_OBJ = pytz.timezone(TIME_ZONE)

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Celery & Redis Caching
CELERY_TASK_ALWAYS_EAGER = DEBUG  # true to run tasks synchronously for testing and development
CELERY_BROKER_URL = "redis://localhost:6379"
CELERY_RESULT_BACKEND = "redis://localhost:6379"
STATIC_PAGE_CACHE_TIME = int(os.environ.get("STATIC_PAGE_CACHE_TIME", 60 * 60))  # every hour
DYNAMIC_PAGE_CACHE_TIME = int(os.environ.get("STATIC_PAGE_CACHE_TIME", 60 * 5))  # 5 minutes
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://localhost:6379",
        "KEY_PREFIX": "sweepstake",
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

WHITENOISE_STATIC_PREFIX = "/static/"
STATIC_ROOT = BASE_DIR / "productionfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Error reporting with Sentry.io
if (sentry_sdk_url := os.environ.get("SENTRY_URL", None)) is not None:
    sentry_sdk.init(
        dsn=sentry_sdk_url,
        enable_tracing=True,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        integrations=[
            CeleryIntegration(monitor_beat_tasks=True),
        ],
    )
    SENTRY_SCRIPT_HEAD = """
        <script
          src="https://browser.sentry-cdn.com/8.7.0/bundle.tracing.replay.min.js"
          integrity="sha384-dJxmSf43HczZBLC024NWeK3CvBfqLuL4bPv3lAKeMZty0jA7AHnefU1jEzx7VbUo"
          crossorigin="anonymous"
        ></script>
    """
else:
    SENTRY_SCRIPT_HEAD = ""


# Emails
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", None)
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 25))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", None)
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", None)
EMAIL_USE_TLS = None if (use_ssl := os.environ.get("EMAIL_USE_TLS", None)) is None else bool(use_ssl)
EMAIL_USE_SSL = None if (use_ssl := os.environ.get("EMAIL_USE_SSL", None)) is None else bool(use_ssl)
EMAIL_FROM = os.environ.get("EMAIL_FROM", None)
EMAIL_REPLY_TO = None if (reply_email := os.environ.get("EMAIL_REPLY_TO", None)) is None else reply_email.split(",")
