# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase

from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from kleides_mfa import settings as mfa_settings
from kleides_mfa.forms import DeviceUpdateForm
from kleides_mfa.registry import AlreadyRegistered, registry
from kleides_mfa.views.mixins import SESSION_KEY

from .factories import UserFactory


class KleidesMfaTestCase(TestCase):
    def login(self, user, redirect_to='/list/', login_url='/login/'):
        # The LoginView prepares the session for 2 step authentication.
        response = self.client.post(
            login_url,
            {'username': user.username, 'password': user.raw_password},
            follow=True)
        self.assertRedirects(response, redirect_to)
        return response

    def login_with_mfa(self, user):
        device = user.totpdevice_set.get_or_create(name='test')[0]
        # Force the user to login with 2 step authentication.
        # django-otp should do this if the otp_device is set.
        user.otp_device = device

        # Login may clear the session if a user was logged in.
        self.client.force_login(user)

        # Except the user is taken from the request, the test client does not
        # set it and django login does not add it unless the user attribute
        # already exists...
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

    def test_login_failure(self):
        response = self.client.post(
            '/login/', {'username': 'test2', 'password': 'test1234'})
        self.assertContains(
            response, 'Please enter a correct username and password.')

    def test_initial_account_setup(self):
        # With single factor authentication a user can see the empty
        # list of available authentication methods as well as add a device.
        # The user cannot do anything else without 2 step authentication.
        user = UserFactory()
        response = self.login(user)
        self.assertContains(
            response, 'These are your 2 step authentication methods.')
        self.assertFalse(registry.user_has_device(user))

        context_user = response.context['user']
        self.assertTrue(context_user.is_single_factor_authenticated)
        self.assertFalse(context_user.is_authenticated)
        self.assertFalse(context_user.is_verified)

        # User is allowed to add a authentication method.
        response = self.client.get('/totp/create/')
        self.assertEqual(response.status_code, 200)

        # Force 2 step login setup.
        self.login_with_mfa(user)
        self.assertTrue(registry.user_has_device(user))

        response = self.client.get('/list/')

        context_user = response.context['user']
        self.assertTrue(context_user.is_single_factor_authenticated)
        self.assertTrue(context_user.is_authenticated)
        self.assertTrue(context_user.is_verified)

        # Single factor authentication no longer authenticates the user.
        self.client.logout()
        device = user.totpdevice_set.get(name='test')
        response = self.login(
            user, '/totp/verify/{}/?next=/list/'.format(device.pk))

        context_user = response.context['user']
        self.assertTrue(context_user.is_anonymous)

        # No access to the device listing with single factor auth.
        response = self.client.get('/list/')
        self.assertRedirects(response, '/login/?next=/list/')
        response = self.client.get('/totp/create/')
        self.assertRedirects(response, '/login/?next=/totp/create/')

        # Start new MFA session.
        self.login_with_mfa(user)

        update_url = '/totp/update/{}/'.format(device.pk)
        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 200)

        context_user = response.context['user']
        self.assertTrue(context_user.is_single_factor_authenticated)
        self.assertTrue(context_user.is_authenticated)
        self.assertTrue(context_user.is_verified)

        # Update TOTP name.
        response = self.client.post(
            '/totp/update/{}/'.format(device.pk), {'name': 'Secure Phone'},
            follow=True)
        self.assertRedirects(response, '/list/')
        self.assertContains(
            response,
            'The TOTP &quot;Secure Phone&quot; was changed successfully.')

        # Secure access is revoked when all authentication methods are removed.
        response = self.client.post(
            '/totp/delete/{}/'.format(device.pk), follow=True)
        self.assertRedirects(response, '/list/')
        self.assertContains(
            response,
            'The TOTP &quot;Secure Phone&quot; was deleted successfully.')

        context_user = response.context['user']
        self.assertTrue(context_user.is_single_factor_authenticated)
        self.assertFalse(context_user.is_authenticated)
        self.assertFalse(context_user.is_verified)

    def test_secure_admin(self):
        # Users must be verified to access the admin interface.
        user = UserFactory(is_staff=True, is_superuser=True)
        self.login(user)

        response = self.client.get('/admin/', follow=True)
        self.assertRedirects(response, '/login/?next=/admin/')

        self.login_with_mfa(user)

        response = self.client.get('/admin/', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_login_redirect(self):
        user = UserFactory()
        # without a device configured the redirect url is SINGLE_FACTOR_URL.
        response = self.login(
            user, redirect_to=resolve_url(mfa_settings.SINGLE_FACTOR_URL))

        device = user.totpdevice_set.create(name='test')
        verify_url = '/totp/verify/{}/?next='.format(device.pk)
        # with a device configured the next redirect url is LOGIN_REDIRECT_URL.
        response = self.login(
            user,
            redirect_to=verify_url + resolve_url(settings.LOGIN_REDIRECT_URL))

        # Unless the user came here with a next parameter.
        response = self.login(
            user, login_url='/login/?next=/some/place/%3Fwith%3Dparams',
            redirect_to=verify_url + '/some/place/%3Fwith%3Dparams')

        # The next parameter is properly escaped in the template for the device
        # selection links.
        self.assertContains(response, 'Other methods')
        self.assertContains(
            response, verify_url + '/some/place/%3Fwith%3Dparams')
        self.assertNotContains(
            response, verify_url + '/some/place/?with=params')

    def test_recovery_from_bad_device(self):
        # Restart authentication if a device goes missing. (deletion etc)
        user = UserFactory()
        device = user.totpdevice_set.create(name='test')
        verify_url = '/totp/verify/{}/?next='.format(device.pk)
        response = self.login(
            user, login_url='/login/?next=/some/place/%3Fwith%3Dparams',
            redirect_to=verify_url + '/some/place/%3Fwith%3Dparams')

        device.delete()
        response = self.client.get(verify_url + '/some/place/%3Fwith%3Dparams')
        self.assertRedirects(
            response, '/login/?next=/some/place/%3Fwith%3Dparams')
        # session is invalid and has been flushed.
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_verify_permission_error(self):
        user = UserFactory()
        device = user.totpdevice_set.create(name='test')
        self.login_with_mfa(user)
        verify_url = '/totp/verify/{}/?next='.format(device.pk)
        # It is not allowed to access a verification device after verification.
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 403)

    def test_plugin(self):
        # Plugins are allowed to use the same device/model.
        totp_plugin = registry.get_plugin('totp')
        registry.register(
            'TEST', TOTPDevice, update_form_class=DeviceUpdateForm)
        plugin = registry.get_plugin('test')
        self.assertEqual(plugin.model, totp_plugin.model)
        self.assertEqual(str(plugin), 'TEST')
        self.assertEqual(
            repr(plugin),
            "KleidesMfaPlugin(name='TEST', model=<class "
            "'django_otp.plugins.otp_totp.models.TOTPDevice'>)")

        self.assertIsNone(plugin.get_create_form_class())
        self.assertIsNotNone(plugin.get_update_form_class())
        self.assertIsNone(plugin.get_verify_form_class())

        # But the name must be unique.
        with self.assertRaises(AlreadyRegistered):
            registry.register('tEsT', TOTPDevice)

        registry.unregister('test')
        with self.assertRaises(KeyError):
            registry.unregister('test')
