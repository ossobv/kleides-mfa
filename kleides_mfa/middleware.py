# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import functools

from django.utils.functional import SimpleLazyObject

from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.models import Device


class KleidesAuthenticationMiddleware(object):
    """
    This is a replacement for :class:`~django_otp.middleware.OTPMiddleware`
    that uses ``is_single_factor_authenticated`` instead of
    ``is_authenticated``. This allows us to override the ``is_authenticated``
    property to only return True when the user has used 2 step authentication.

    This must be installed after
    :class:`~django.contrib.auth.middleware.AuthenticationMiddleware` and
    performs an analogous function. Just as AuthenticationMiddleware populates
    ``request.user`` based on session data, KleidesAuthenticationMiddleware
    populates ``request.user.otp_device`` to the
    :class:`~django_otp.models.Device` object that has verified the user,
    or ``None`` if the user has not been verified.
    """
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None:
            request.user = SimpleLazyObject(
                functools.partial(self._verify_user, request, user))

        return self.get_response(request)

    def _verify_user(self, request, user):
        """
        Sets OTP-related fields on an authenticated user.
        """
        device = None

        if user.is_single_factor_authenticated:
            persistent_id = request.session.get(DEVICE_ID_SESSION_KEY)
            if persistent_id:
                device = Device.from_persistent_id(persistent_id)
                # Ensure the device belongs to the user.
                if device is not None and device.user_id != user.pk:
                    device = None

            if device is None and DEVICE_ID_SESSION_KEY in request.session:
                del request.session[DEVICE_ID_SESSION_KEY]

        user.otp_device = device

        return user
