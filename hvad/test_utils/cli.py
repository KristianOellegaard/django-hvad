# -*- coding: utf-8 -*-
import sys
import django
from hvad.test_utils.dj_database_url import config
import os

gettext = lambda s: s

PYTHON_VERSION = '%s.%s' % sys.version_info[:2]
DJANGO_VERSION = django.get_version()


def configure(**extra):
    from django.conf import settings
    os.environ['DJANGO_SETTINGS_MODULE'] = 'hvad.test_utils.cli'
    defaults = dict(
        CACHE_BACKEND = 'locmem:///',
        DEBUG = True,
        TEMPLATE_DEBUG = True,
        DATABASE_SUPPORTS_TRANSACTIONS = True,
        DATABASES = {'default': config(default='sqlite://localhost/hvad.db')},
        TEST_DATABASE_CHARSET = "utf8",
        TEST_DATABASE_COLLATION = "utf8_general_ci",
        SITE_ID = 1,
        USE_I18N = True,
        MEDIA_ROOT = '/media/',
        STATIC_ROOT = '/static/',
        MEDIA_URL = '/media/',
        STATIC_URL = '/static/',
        ADMIN_MEDIA_PREFIX = '/static/admin/',
        EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend',
        SECRET_KEY = 'key',
        TEMPLATE_LOADERS = (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
            'django.template.loaders.eggs.Loader',
        ),
        TEMPLATE_DIRS = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), 'project', 'templates'))
        ],
        MIDDLEWARE_CLASSES = [
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.common.CommonMiddleware',
            ('django.contrib.admindocs.middleware.XViewMiddleware'
             if django.VERSION >= (1, 7) else 'django.middleware.doc.XViewMiddleware'),
            'django.middleware.csrf.CsrfViewMiddleware',
        ],
        INSTALLED_APPS = [
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.admin',
            'django.contrib.sites',
            'django.contrib.staticfiles',
            'hvad',
            'hvad.test_utils.project.app',
            'hvad.test_utils.project.alternate_models_app',
        ],
        LANGUAGE_CODE = "en",
        LANGUAGES = (
            ('en', 'English'),
            ('ja', u'日本語'),
        ),
        JUNIT_OUTPUT_DIR = 'junit-dj%s-py%s' % (DJANGO_VERSION, PYTHON_VERSION),
        ROOT_URLCONF = 'hvad.test_utils.project.urls',
        PASSWORD_HASHERS = (
            'django.contrib.auth.hashers.MD5PasswordHasher',
        )
    )
    defaults.update(extra)
    settings.configure(**defaults)
    from django.contrib import admin
    if django.VERSION >= (1, 7):
        django.setup()
    admin.autodiscover()
