# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig, apps
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _


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
        from . import settings
        from .registry import registry

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
                'TOTP', TOTPDevice, create_form_class=TOTPDeviceCreateForm,
                verify_form_class=DeviceVerifyForm)

        if apps.is_installed('django_otp.plugins.otp_static'):
            from .forms import RecoveryDeviceForm, DeviceVerifyForm
            from django_otp.plugins.otp_static.models import StaticDevice
            message = _('Your recovery codes have been generated, save them '
                        'somewhere safe! Any old codes you have will no '
                        'longer be usable.')
            delete_message = _('Your recovery codes have been disabled!')
            registry.register(
                'Recovery code', StaticDevice,
                device_list_javascript='js/kleides_mfa/recovery-code.js',
                device_list_template=(
                    'kleides_mfa/device_recovery-code_list.html'),
                create_form_class=RecoveryDeviceForm,
                update_form_class=RecoveryDeviceForm,
                verify_form_class=DeviceVerifyForm,
                create_message=message, update_message=message,
                delete_message=delete_message)

        if settings.PATCH_ADMIN:
            from django.contrib import admin
            from .admin import AdminSiteMfaRequiredMixin
            MfaAdminSite = type(
                str('MfaAdminSite'),
                (AdminSiteMfaRequiredMixin, admin.AdminSite), {})
            setattr(admin, 'AdminSite', MfaAdminSite)
            admin.site.__class__ = MfaAdminSite
