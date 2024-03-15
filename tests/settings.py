# -*- coding: utf-8 -*-
# kleides-mfa test project
from os.path import abspath, dirname, join

import django


def project_path(path):
    return abspath(join(dirname(__file__), path))


DEBUG = True

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.messages',

    'django_otp',
    'django_otp.plugins.otp_email',
    'django_otp.plugins.otp_hotp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'otp_yubikey',

    'kleides_mfa',
    'tests.apps.TestAdminConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'kleides_mfa.middleware.KleidesAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

if (4, 1) < django.VERSION < (5, 0):
    FORM_RENDERER = 'django.forms.renderers.DjangoDivFormRenderer'
else:
    FORM_RENDERER = 'django.forms.renderers.DjangoTemplates'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [
            project_path('templates'),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

SECRET_KEY = 'XXX'

USE_TZ = True

ROOT_URLCONF = 'tests.urls'

OTP_TOTP_ISSUER = 'Kleides MFA'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'testserver',
]
STATIC_URL = '/static/'
STATIC_ROOT = project_path('../static/')

LOGIN_URL = 'kleides_mfa:login'
LOGIN_REDIRECT_URL = 'kleides_mfa:index'

KLEIDES_MFA_PATCH_ADMIN = False
