# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from base64 import b32decode
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase
from django.test.utils import override_settings

from django_otp.oath import TOTP

from .factories import UserFactory


class DjangoOtpTotpTestCase(TestCase):
    def totp_from_form(self, form):
        url = urlsplit(form.instance.config_url)
        params = parse_qs(url.query)
        return TOTP(
            b32decode(params['secret'][0]),
            step=int(params['period'][0]),
            digits=int(params['digits'][0]), t0=0, drift=0)

    def login(self, user, redirect_to='/list/'):
        response = self.client.post(
            '/login/',
            {'username': user.username, 'password': user.raw_password},
            follow=True)
        self.assertRedirects(response, redirect_to)
        return response

    @override_settings(OTP_TOTP_SYNC=True, OTP_TOTP_THROTTLE_FACTOR=0)
    def test_totp(self):
        user = UserFactory()
        self.login(user)

        response = self.client.post(
            '/totp/create/', {'otp_token': 'XXX', 'name': 'My Phone'})
        self.assertContains(
            response, 'Unable to validate the token with the device.')
        response = self.client.post(
            '/totp/create/', {'otp_token': '123456', 'name': 'My Phone'})
        self.assertContains(
            response, 'Unable to validate the token with the device.')

        # User takes the TOTP config and applies it to his device.
        response = self.client.get('/totp/create/')
        totp = self.totp_from_form(response.context['form'])

        # Confirm the user can generate tokens and the device is configured.
        registration_token = totp.token()
        response = self.client.post(
            '/totp/create/', {
                'otp_token': registration_token, 'name': 'My Phone'})
        self.assertRedirects(response, '/list/')
        device = user.totpdevice_set.get()
        self.assertTrue(device.confirmed)
        self.assertEqual(device.name, 'My Phone')

        response = self.client.post(
            '/totp/update/{}/'.format(device.pk), {'name': 'Acme ID'})
        self.assertRedirects(response, '/list/')
        device = user.totpdevice_set.get()
        self.assertEqual(device.name, 'Acme ID')

        self.client.logout()

        # Login without TOTP.
        verify_url = '/totp/verify/{}/'.format(device.pk)
        self.login(user, '{}?next=/list/'.format(verify_url))

        # User is forced to use 2 step authentication.
        response = self.client.get('/list/')
        self.assertRedirects(response, '/login/?next=/list/')
        response = self.client.post('/totp/delete/{}/'.format(device.pk))
        self.assertRedirects(
            response, '/login/?next=/totp/delete/{}/'.format(device.pk))

        # Token reuse is not allowed so the registration is no longer valid.
        response = self.client.post(
            verify_url, {'otp_token': registration_token})
        self.assertContains(
            response, 'The token is not valid for this device.')

        # Default tolerance is 1, increase drift to force next token.
        totp.drift = 1
        response = self.client.post(verify_url, {'otp_token': totp.token()})
        self.assertRedirects(response, '/list/')

        response = self.client.post(
            '/totp/delete/{}/'.format(device.pk), follow=True)
        self.assertContains(
            response, 'The TOTP &quot;Acme ID&quot; was deleted successfully.')

    @override_settings(OTP_TOTP_SYNC=False)
    def test_otp_sync(self):
        user = UserFactory()
        self.login(user)

        response = self.client.get('/totp/create/')
        totp = self.totp_from_form(response.context['form'])
        totp.drift = 1
        response = self.client.post(
            '/totp/create/', {'otp_token': totp.token()})
        self.assertRedirects(response, '/list/')
        device = user.totpdevice_set.get()
        self.assertTrue(device.confirmed)
        self.assertEqual(device.drift, 0)
