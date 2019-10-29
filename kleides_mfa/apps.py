# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig, apps
from django.contrib.auth import get_user_model

from .registry import registry
from . import settings


def is_authenticated(user):
    '''
    User.is_authenticated property that ensures user used 2 step
    authentication.
    '''
    return bool(user.is_verified)


def is_verified(user):
    '''
    User.is_verified property.
    '''
    # Warning: The django-otp version is a function instead of a propertry.
    # otp_device may not be set (django startup check, no middleware).
    return bool(getattr(user, 'otp_device', None) is not None)


def is_single_factor_authenticated(user):
    '''
    User.is_single_factor_authenticated property.
    Always returns True for authenticated users.
    '''
    return bool(not user.is_anonymous)


class KleidesMfaConfig(AppConfig):
    name = 'kleides_mfa'
    verbose_name = 'Kleides Multi Factor Authentication'

    def ready(self):
        # Monkey patch user authentication properties.
        User = get_user_model()
        User.is_verified = property(is_verified)
        User.is_authenticated = property(is_authenticated)
        User.is_single_factor_authenticated = property(
            is_single_factor_authenticated)

        # Check if known devices are installed and register them as plugins.
        if apps.is_installed('django_otp.plugins.otp_totp'):
            from .forms import TOTPDeviceCreateForm, DeviceVerifyForm
            from django_otp.plugins.otp_totp.models import TOTPDevice
            registry.register(
                'TOTP', TOTPDevice, create_form=TOTPDeviceCreateForm,
                verify_form=DeviceVerifyForm)

        if apps.is_installed('django_otp.plugins.otp_static'):
            from .forms import RecoveryDeviceForm, DeviceVerifyForm
            from django_otp.plugins.otp_static.models import StaticDevice
            registry.register(
                'Recovery code', StaticDevice,
                device_list_javascript='js/kleides_mfa/recovery-code.js',
                device_list_template=(
                    'kleides_mfa/device_recovery-code_list.html'),
                create_form=RecoveryDeviceForm,
                update_form=RecoveryDeviceForm,
                verify_form=DeviceVerifyForm)

        if settings.PATCH_ADMIN:
            from django.contrib import admin
            from .admin import AdminSiteMfaRequiredMixin
            MfaAdminSite = type(
                str('MfaAdminSite'),
                (AdminSiteMfaRequiredMixin, admin.AdminSite), {})
            setattr(admin, 'AdminSite', MfaAdminSite)
            admin.site.__class__ = MfaAdminSite
