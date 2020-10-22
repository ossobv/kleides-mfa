# -*- coding: utf-8 -*-
from django.apps import AppConfig, apps
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


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


def create_yubikey_validationservice(app_config, using='default', **kwargs):
    '''
    Make sure at least one ValidationService exists.
    '''
    from otp_yubikey.models import ValidationService
    if (app_config.label == 'otp_yubikey'
            and ValidationService.objects.using(using).all().count() == 0):
        ValidationService.objects.using(using).get_or_create(defaults={
            'name': 'YubiCloud', 'use_ssl': True,
            'param_sl': '', 'param_timeout': ''})


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
        from django.contrib.auth.models import AnonymousUser
        AnonymousUser.is_verified = property(is_verified)
        AnonymousUser.is_authenticated = property(is_authenticated)
        AnonymousUser.is_single_factor_authenticated = property(
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

        if apps.is_installed('otp_yubikey'):
            from .forms import DeviceVerifyForm, YubikeyDeviceCreateForm
            from otp_yubikey.models import RemoteYubikeyDevice
            registry.register(
                'Yubikey', RemoteYubikeyDevice,
                create_form_class=YubikeyDeviceCreateForm,
                verify_form_class=DeviceVerifyForm)
            post_migrate.connect(
                create_yubikey_validationservice,
                dispatch_uid='kleides_mfa.apps.KleidesMfaConfig')

        if (apps.is_installed('django.contrib.admin')
                and settings.PATCH_ADMIN):  # pragma: no branch
            from django.contrib import admin
            from .admin import AdminSiteMfaRequiredMixin
            MfaAdminSite = type(
                str('MfaAdminSite'),
                (AdminSiteMfaRequiredMixin, admin.AdminSite), {})
            setattr(admin, 'AdminSite', MfaAdminSite)
            admin.site.__class__ = MfaAdminSite
