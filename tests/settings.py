# kleides-mfa test project

from __future__ import absolute_import, division, print_function, unicode_literals

from os.path import abspath, dirname, join


def project_path(path):
    return abspath(join(dirname(__file__), path))


DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': project_path('kleides-mfa.db'),
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.messages',

    'django_extensions',

    'django_otp',
    'django_otp.plugins.otp_email',
    'django_otp.plugins.otp_hotp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'otp_u2f',

    'kleides_mfa',
    'crispy_forms',
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

ROOT_URLCONF = 'tests.urls'

CRISPY_TEMPLATE_PACK = 'bootstrap4'

OTP_TOTP_ISSUER = 'Kleides MFA'

ALLOWED_HOSTS = [
    'localhost.osso.ninja',
]
STATIC_URL = '/static/'
STATIC_ROOT = project_path('../static/')

LOGIN_URL = 'kleides_mfa:login'
LOGIN_REDIRECT_URL = 'kleides_mfa:index'
