# -*- coding: utf-8 -*-
import time

from django import forms
from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice


TOTP_SESSION_KEY = 'kleides-mfa-totp-key'


class BaseVerifyForm(forms.Form):
    def __init__(
            self, device, plugin, request, unverified_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unverified_user = unverified_user
        self.plugin = plugin
        self.device = device
        self.request = request

    def get_user(self):
        if self.is_valid():
            return self.unverified_user
        return None

    def get_device(self):
        if self.is_valid():
            return self.device
        return None


class DeviceVerifyForm(BaseVerifyForm):
    otp_token = forms.CharField(label=_('Token'))

    error_messages = {
        'invalid': _('The token is not valid for this device.'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['otp_token'].widget.attrs.update({
            'autocomplete': 'off', 'autofocus': 'autofocus'})

    def clean(self):
        cleaned_data = super().clean()
        token = cleaned_data.get('otp_token')
        if not token:  # token is a required field.
            return cleaned_data

        # Note that tokens can become invalid once verified.
        if not self.device.verify_token(token):
            raise forms.ValidationError(self.error_messages['invalid'])
        return cleaned_data


class BaseDeviceForm(forms.ModelForm):
    def __init__(self, plugin, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin = plugin
        self.request = request
        if 'name' in self.fields:
            self.fields['name'].initial = self.plugin.name
            self.fields['name'].required = False
            self.fields['name'].widget.attrs['placeholder'] = _(
                'Friendly name')

    def clean_name(self):
        if self.cleaned_data.get('name'):
            return self.cleaned_data['name']
        return self.plugin.name


class DeviceCreateForm(BaseDeviceForm):
    error_messages = {
        'invalid': _('Unable to validate the token with the device.'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # WARNING: The form associates the user with the potential new device
        # instance to allow device functions dependent on the user to be used.
        # The plugin author must take care to only use functions that will not
        # save the instance as this may circumvent the verification process.
        self.instance.user = self.request.user
        self.instance.confirmed = False

    def _post_clean(self):
        super()._post_clean()
        if self.instance.pk is not None:
            raise ValueError(
                'Plugin {} saved the device before completing verification. '
                'The device will be unconfirmed and unusable. '
                'Please review {} {!r}.'.format(
                    self.plugin, self.instance.persistent_id, self.instance))
        self.instance.confirmed = True


class DeviceUpdateForm(BaseDeviceForm):
    pass


class TOTPDeviceCreateForm(DeviceCreateForm):
    otp_token = forms.CharField(label=_('Token'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['otp_token'].widget.attrs.update({
            'autocomplete': 'off', 'autofocus': 'autofocus'})
        # Store the TOTP key in the session, rotate the key on unbound forms.
        if self.is_bound and TOTP_SESSION_KEY in self.request.session:
            self.instance.key = self.request.session[TOTP_SESSION_KEY]
        else:
            self.request.session[TOTP_SESSION_KEY] = self.instance.key
        # If alternate TOTPDevice settings are needed set them here.
        # self.instance.digits = 8  # increase token length.
        # self.instance.tolerance = 2  # for users that are veeeeery slow.

    def clean(self):
        cleaned_data = super().clean()
        try:
            token = int(cleaned_data.get('otp_token'))
        except (TypeError, ValueError):
            verified = False
        else:
            # django-otp setting.
            OTP_TOTP_SYNC = getattr(settings, 'OTP_TOTP_SYNC', True)
            # Device verification using the current instance.
            totp = TOTP(
                self.instance.bin_key, self.instance.step, self.instance.t0,
                self.instance.digits, self.instance.drift)
            totp.time = time.time()

            verified = totp.verify(
                token, self.instance.tolerance, self.instance.last_t)
            if verified:
                # Device is verified, update attributes and prepare the
                # instance to be saved.
                self.instance.last_t = totp.t()
                if OTP_TOTP_SYNC:
                    self.instance.drift = totp.drift
        if not verified:
            raise forms.ValidationError(self.error_messages['invalid'])
        try:
            return cleaned_data
        finally:
            if TOTP_SESSION_KEY in self.request.session:  # pragma: no cover
                del self.request.session[TOTP_SESSION_KEY]

    class Meta:
        model = TOTPDevice
        fields = ('name', 'otp_token',)


class RecoveryDeviceForm(DeviceUpdateForm):
    token_amount = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.instance = self.request.user.staticdevice_set.get()
        except self.request.user.staticdevice_set.model.DoesNotExist:
            pass

    def save(self, *args, **kwargs):
        instance, created = self.request.user.staticdevice_set.get_or_create(
            defaults={'name': self.plugin.name})
        instance.token_set.all().delete()
        for i in range(self.token_amount):
            instance.token_set.create(token=StaticToken.random_token())
        return instance

    class Meta:
        model = StaticDevice
        fields = ()


if apps.is_installed('otp_yubikey'):  # pragma: no branch
    from otp_yubikey.models import RemoteYubikeyDevice, ValidationService

    class YubikeyDeviceCreateForm(DeviceCreateForm):
        service = forms.ModelChoiceField(
            label=_('Service'), queryset=ValidationService.objects.all(),
            empty_label=None)
        otp_token = forms.CharField(label=_('Token'))

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['otp_token'].widget.attrs.update({
                'autocomplete': 'off', 'autofocus': 'autofocus'})
            try:
                self.fields['service'].initial = (
                    self.fields['service'].queryset.get().pk)
                self.fields['service'].widget = forms.HiddenInput()
            except ValidationService.MultipleObjectsReturned:
                # Multiple is good, none is bad.
                pass

        def clean(self):
            cleaned_data = super().clean()
            token = self.cleaned_data.get('otp_token')
            service = self.cleaned_data.get('service')
            verified = False
            if token and service:
                self.instance.service = service
                self.instance.public_id = token[:-32]
                verified = self.instance.verify_token(token)
            if not verified:
                raise forms.ValidationError(self.error_messages['invalid'])
            return cleaned_data

        class Meta:
            model = RemoteYubikeyDevice
            fields = ('service', 'name', 'otp_token',)
