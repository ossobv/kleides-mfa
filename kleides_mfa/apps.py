# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig, apps

from .registry import registry


class KleidesMfaConfig(AppConfig):
    name = 'kleides_mfa'
    verbose_name = 'Kleides Multi Factor Authentication'

    def ready(self):
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
