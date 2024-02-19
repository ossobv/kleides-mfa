from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.utils import timezone

from django_otp import DEVICE_ID_SESSION_KEY

from kleides_mfa.views.mixins import VERIFIED_SESSION_KEY
from kleides_mfa.decorators import (
    create_decorator, single_factor_required, multi_factor_required,
    recent_multi_factor_required, setup_or_mfa_required,
    setup_or_recent_mfa_required)

from .factories import UserFactory


class KleidesMfaDecoratorTestCase(TestCase):
    def setUp(self):
        self.rfactory = RequestFactory()

    def request(self, user):
        request = self.rfactory.get('/view_test/')
        request.user = user
        request.session = {}
        return request

    def mfa_request(self, user, verified_on=None):
        device = user.totpdevice_set.get_or_create(name='test')[0]
        # Force the user to login with 2 step authentication.
        # django-otp should do this if the otp_device is set.
        user.otp_device = device

        request = self.request(user)

        request.session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        if verified_on is None:
            verified_on = timezone.now()
        request.session[VERIFIED_SESSION_KEY] = verified_on.isoformat()
        return request

    def test_create_decorator(self):
        with self.assertRaises(ValueError):
            create_decorator(lambda r: r.user.is_verified)

    def test_args(self):
        @single_factor_required()
        def view_test(request):
            return HttpResponse('view_test')

        request = self.request(AnonymousUser())
        response = view_test(request)
        self.assertEqual(response.status_code, 302)

    def test_no_args(self):
        @single_factor_required
        def view_test(request):
            return HttpResponse('view_test')

        request = self.request(AnonymousUser())
        response = view_test(request)
        self.assertEqual(response.status_code, 302)

    def test_single_factor_required(self):
        @single_factor_required(raise_exception=True)
        def view_test(request):
            return HttpResponse('view_test')

        with self.assertRaises(PermissionDenied):
            request = self.request(AnonymousUser())
            view_test(request)

        request = self.request(UserFactory())
        response = view_test(request)
        self.assertEqual(response.status_code, 200)

    def test_multi_factor_required(self):
        @multi_factor_required(raise_exception=True)
        def view_test(request):
            return HttpResponse('view_test')

        with self.assertRaises(PermissionDenied):
            request = self.request(AnonymousUser())
            view_test(request)

        with self.assertRaises(PermissionDenied):
            request = self.request(UserFactory())
            view_test(request)

        request = self.mfa_request(UserFactory())
        response = view_test(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(KLEIDES_MFA_VERIFIED_TIMEOUT=60)
    def test_recent_multi_factor_required(self):
        @recent_multi_factor_required(raise_exception=True)
        def view_test(request):
            return HttpResponse('view_test')

        with self.assertRaises(PermissionDenied):
            request = self.request(AnonymousUser())
            view_test(request)

        with self.assertRaises(PermissionDenied):
            request = self.request(UserFactory())
            view_test(request)

        with self.assertRaises(PermissionDenied):
            request = self.mfa_request(
                UserFactory(),
                verified_on=timezone.now() - timedelta(seconds=90))
            view_test(request)

        request = self.mfa_request(UserFactory())
        response = view_test(request)
        self.assertEqual(response.status_code, 200)

    def test_setup_or_mfa_required(self):
        @setup_or_mfa_required(raise_exception=True)
        def view_test(request):
            return HttpResponse('view_test')

        with self.assertRaises(PermissionDenied):
            request = self.request(AnonymousUser())
            view_test(request)

        with self.assertRaises(PermissionDenied):
            request = self.request(UserFactory())
            request.user.totpdevice_set.get_or_create(name='test')
            view_test(request)

        request = self.request(UserFactory())
        response = view_test(request)
        self.assertEqual(response.status_code, 200)

        request = self.mfa_request(UserFactory())
        response = view_test(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(KLEIDES_MFA_VERIFIED_TIMEOUT=60)
    def test_setup_or_recent_mfa_required(self):
        @setup_or_recent_mfa_required(raise_exception=True)
        def view_test(request):
            return HttpResponse('view_test')

        with self.assertRaises(PermissionDenied):
            request = self.request(AnonymousUser())
            view_test(request)

        with self.assertRaises(PermissionDenied):
            request = self.request(UserFactory())
            request.user.totpdevice_set.get_or_create(name='test')
            view_test(request)

        with self.assertRaises(PermissionDenied):
            request = self.mfa_request(
                UserFactory(),
                verified_on=timezone.now() - timedelta(seconds=90))
            view_test(request)

        request = self.request(UserFactory())
        response = view_test(request)
        self.assertEqual(response.status_code, 200)

        request = self.mfa_request(UserFactory())
        response = view_test(request)
        self.assertEqual(response.status_code, 200)
