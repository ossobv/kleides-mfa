# -*- coding: utf-8 -*-
from base64 import b32decode
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.test import TestCase
from django.test.utils import override_settings

from django_otp.oath import TOTP

from kleides_mfa.registry import registry

from .factories import UserFactory
from .utils import handle_signal


class DjangoOtpTotpTestCase(TestCase):
    def totp_from_device(self, device):
        url = urlsplit(device.config_url)
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
        totp = self.totp_from_device(response.context['form'].instance)

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
        response = self.login(user, '{}?next=/list/'.format(verify_url))

        context_user = response.context['user']
        self.assertTrue(context_user.is_anonymous)

        # User is forced to use 2 step authentication.
        response = self.client.get('/list/')
        self.assertRedirects(response, '/login/?next=/list/')
        response = self.client.post('/totp/delete/{}/'.format(device.pk))
        self.assertRedirects(
            response, '/login/?next=/totp/delete/{}/'.format(device.pk))

        # Token reuse is not allowed so the registration is no longer valid.
        with handle_signal(user_login_failed) as handler:
            response = self.client.post(
                verify_url, {'otp_token': registration_token})
            handler.assert_called_once_with(
                credentials={}, user=user, device=device,
                sender=mock.ANY, request=mock.ANY, signal=user_login_failed)
        self.assertContains(
            response, 'The token is not valid for this device.')

        # Default tolerance is 1, increase drift to force next token.
        totp.drift = 1
        with handle_signal(user_logged_in) as handler:
            response = self.client.post(
                verify_url, {'otp_token': totp.token()}, follow=True)
            handler.assert_called_once_with(
                user=user, sender=mock.ANY, request=mock.ANY,
                signal=user_logged_in)
        self.assertRedirects(response, '/list/')

        context_user = response.context['user']
        self.assertTrue(context_user.is_authenticated)
        self.assertTrue(context_user.is_verified)

        # Verify that the authentication method matches.
        self.assertEqual(
            registry.user_authentication_method(context_user), 'totp')

        response = self.client.post(
            '/totp/delete/{}/'.format(device.pk), follow=True)
        self.assertContains(
            response, 'The TOTP &quot;Acme ID&quot; was deleted successfully.')

    @override_settings(OTP_TOTP_SYNC=False)
    def test_otp_sync(self):
        user = UserFactory()
        self.login(user)

        response = self.client.get('/totp/create/')
        totp = self.totp_from_device(response.context['form'].instance)
        totp.drift = 1
        response = self.client.post(
            '/totp/create/', {'otp_token': totp.token()})
        self.assertRedirects(response, '/list/')
        device = user.totpdevice_set.get()
        self.assertTrue(device.confirmed)
        self.assertEqual(device.drift, 0)

    def test_totp_after_different_user(self):
        user = UserFactory()
        self.login(user)
        session = self.client.session
        session['secrets'] = 'yes'
        session.save()

        user = UserFactory()
        device = user.totpdevice_set.create(name='test')
        totp = self.totp_from_device(device)

        verify_url = '/totp/verify/{}/'.format(device.pk)
        response = self.login(user, '{}?next=/list/'.format(verify_url))

        self.assertEqual(self.client.session['secrets'], 'yes')

        response = self.client.post(
            verify_url, {'otp_token': totp.token()}, follow=True)
        self.assertRedirects(response, '/list/')

        context_user = response.context['user']
        self.assertTrue(context_user.is_authenticated)
        self.assertTrue(context_user.is_verified)
        with self.assertRaises(KeyError):
            self.client.session['secrets']
