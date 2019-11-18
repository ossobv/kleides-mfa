# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from binascii import unhexlify

from django.test import TestCase
from mock import patch
from yubiotp.otp import YubiKey
from otp_yubikey.models import (
    RemoteYubikeyDevice, ValidationService, default_id)

from kleides_mfa.forms import YubikeyDeviceCreateForm
from kleides_mfa.registry import registry

from .factories import UserFactory


class DjangoOtpYubikeyTestCase(TestCase):
    def login(self, user, redirect_to='/list/'):
        response = self.client.post(
            '/login/',
            {'username': user.username, 'password': user.raw_password},
            follow=True)
        self.assertRedirects(response, redirect_to)
        return response

    @patch.object(RemoteYubikeyDevice, 'verify_token')
    def test_yubikey(self, mock_verify_token):
        user = UserFactory()
        self.login(user)

        # Test bad/missing input.
        mock_verify_token.return_value = False
        service = ValidationService.objects.latest('pk')
        response = self.client.post(
            '/yubikey/create/', {'name': 'Keychain'})
        self.assertContains(
            response, 'This field is required.')
        self.assertTrue(
            response.context['form'].fields['service'].widget.is_hidden)
        # Test field visibility with multiple services.
        ValidationService.objects.create(
            name='YubiCustom', param_sl='', param_timeout='')
        response = self.client.post(
            '/yubikey/create/', {
                'service': service.pk, 'otp_token': 'XXX',
                'name': 'Keychain'})
        self.assertContains(
            response, 'Unable to validate the token with the device.')
        self.assertFalse(
            response.context['form'].fields['service'].widget.is_hidden)

        # Test success.
        mock_verify_token.return_value = True
        yubikey = YubiKey(unhexlify(default_id()), 6, 0)
        registration_token = yubikey.generate()
        response = self.client.post(
            '/yubikey/create/', {
                'service': service.pk, 'otp_token': registration_token,
                'name': 'Keychain'})
        self.assertRedirects(response, '/list/')
        device = user.remoteyubikeydevice_set.get()
        self.assertTrue(device.confirmed)
        self.assertEqual(device.name, 'Keychain')

        # Test update.
        response = self.client.post(
            '/yubikey/update/{}/'.format(device.pk), {'name': 'Acme Inc.'})
        self.assertRedirects(response, '/list/')
        device = user.remoteyubikeydevice_set.get()
        self.assertEqual(device.name, 'Acme Inc.')

        self.client.logout()

        # Login without Yubikey.
        verify_url = '/yubikey/verify/{}/'.format(device.pk)
        response = self.login(user, '{}?next=/list/'.format(verify_url))

        context_user = response.context['user']
        self.assertTrue(context_user.is_anonymous)

        # User is forced to use 2 step authentication.
        mock_verify_token.return_value = False
        response = self.client.get('/list/')
        self.assertRedirects(response, '/login/?next=/list/')
        response = self.client.post('/yubikey/delete/{}/'.format(device.pk))
        self.assertRedirects(
            response, '/login/?next=/yubikey/delete/{}/'.format(device.pk))

        response = self.client.post(verify_url, {'otp_token': ''})
        self.assertContains(
            response, 'This field is required.')

        # Token reuse is not allowed so now the registration token is invalid.
        response = self.client.post(
            verify_url, {'otp_token': registration_token})
        self.assertContains(
            response, 'The token is not valid for this device.')

        # Complete authentication with a new token.
        mock_verify_token.return_value = True
        response = self.client.post(
            verify_url, {'otp_token': yubikey.generate()}, follow=True)
        self.assertRedirects(response, '/list/')

        context_user = response.context['user']
        self.assertTrue(context_user.is_authenticated)
        self.assertTrue(context_user.is_verified)

        # Verify that the authentication method matches.
        self.assertEqual(
            registry.user_authentication_method(context_user), 'yubikey')

        response = self.client.post(
            '/yubikey/delete/{}/'.format(device.pk), follow=True)
        self.assertContains(
            response,
            'The Yubikey &quot;Acme Inc.&quot; was deleted successfully.')
