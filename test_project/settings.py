# Minimal settings used for testing.
from os import path

import warnings
warnings.filterwarnings(
    'error', r'DateTimeField received a naive datetime',
    RuntimeWarning, r'django\.db\.models\.fields'
)

CURRENT_DIR = path.abspath(path.dirname(__file__))
CALENDARTOOLS_DIR = path.abspath(path.dirname(path.dirname(__file__)))

APPEND_SLASH = True
DEBUG = TEMPLATE_DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    },
}

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'threaded_multihost.middleware.ThreadLocalMiddleware',
)

STATIC_ROOT      = ''
STATICFILES_DIRS = (path.join(CURRENT_DIR, 'static'),)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

USE_TZ = True
TIME_ZONE = 'Europe/Paris'

USE_I18N = True
USE_L10N = True
LANGUAGE_CODE = 'en-gb'
FORMAT_MODULE_PATH = 'calendartools.formats'
SITE_ID = 1

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',

    'event',
    'calendartools',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = [path.join(CALENDARTOOLS_DIR, 'templates'),
                 path.join(CURRENT_DIR, 'templates')]
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'calendartools.context_processors.current_datetime',
    'calendartools.context_processors.current_site',
)

ROOT_URLCONF = 'calendartools.urls'

SECRET_KEY = 'jxv_@c5ll0w@i@fk1k*73&821at1w68!j&5*95c98$wi=^!xdi'
