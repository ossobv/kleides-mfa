# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.test import TestCase

from kleides_mfa.registry import registry

from .factories import UserFactory


class DjangoOtpRecoveryTestCase(TestCase):
    def login(self, user, redirect_to='/list/'):
        response = self.client.post(
            '/login/',
            {'username': user.username, 'password': user.raw_password},
            follow=True)
        self.assertRedirects(response, redirect_to)
        return response

    def test_recovery(self):
        user = UserFactory()
        response = self.login(user)
        self.assertContains(
            response, 'These are your 2 step authentication methods.')

        # Create recovery codes to secure the account.
        response = self.client.post('/recovery-code/create/', follow=True)
        self.assertContains(
            response, 'Your recovery codes have been generated')

        # Login with a recovery code.
        self.client.logout()
        device = user.staticdevice_set.get()
        self.assertEqual(device.token_set.count(), 10)
        device_url = '/recovery-code/verify/{}/'.format(device.pk)
        response = self.login(user, '{}?next=/list/'.format(device_url))

        context_user = response.context['user']
        self.assertTrue(context_user.is_anonymous)

        # Continue authentication using recovery code.
        token = device.token_set.first()
        response = self.client.post(
            device_url, {'otp_token': token.token}, follow=True)
        self.assertRedirects(response, '/list/')
        self.assertEqual(device.token_set.count(), 9)

        context_user = response.context['user']
        self.assertTrue(context_user.is_authenticated)
        self.assertTrue(context_user.is_verified)

        # Verify that the authentication method matches.
        self.assertEqual(
            registry.user_authentication_method(context_user), 'recovery-code')

        # The create and update form for recovery codes replace existing codes.
        self.client.post('/recovery-code/update/{}/'.format(device.pk))
        self.assertEqual(device.token_set.count(), 10)

        # Secure access is revoked when all authentication methods are removed.
        response = self.client.post(
            '/recovery-code/delete/{}/'.format(device.pk), follow=True)
        self.assertRedirects(response, '/list/')

        context_user = response.context['user']
        self.assertTrue(context_user.is_single_factor_authenticated)
        self.assertFalse(context_user.is_authenticated)
        self.assertFalse(context_user.is_verified)
