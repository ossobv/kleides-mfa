# -*- coding: utf-8 -*-
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    get_user_model, load_backend, mixins as auth_mixins)
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import resolve_url
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.translation import gettext_lazy as _

from urllib.parse import urlparse

from ..conf import app_settings
from ..registry import registry


# Note that these session keys are different from django auth so the user
# session will never pass as authenticated. Meanwhile we still need to enforce
# the same protections which is the reason for the duplication.
SESSION_KEY = '_kleides-mfa_user_id'
BACKEND_SESSION_KEY = '_kleides-mfa_user_backend'
HASH_SESSION_KEY = '_kleides-mfa_user_hash'
VERIFIED_SESSION_KEY = '_kleides-mfa_user_verified'


class PluginMixin():
    success_url = reverse_lazy('kleides_mfa:index')

    def dispatch(self, *args, **kwargs):
        self.plugin = self.get_plugin()
        return super().dispatch(*args, **kwargs)

    def get_plugin(self):
        try:
            return registry.get_plugin(self.kwargs['plugin'])
        except KeyError:
            raise Http404('Plugin does not exist')

    def get_object(self):
        return self.plugin.get_user_device(
            self.kwargs['device_id'], self.request.user, confirmed=None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plugin'] = self.plugin
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['plugin'] = self.plugin
        kwargs['request'] = self.request
        return kwargs

    def get_template_names(self):
        return [
            'kleides_mfa/device_{}{}.html'.format(
                self.plugin.slug, self.template_name_suffix),
            'kleides_mfa/device{}.html'.format(self.template_name_suffix),
        ]


class UserPassesTestMixin(auth_mixins.UserPassesTestMixin):
    def handle_no_permission(self):
        '''
        Raise PermissionDenied only when raise_exception is True.
        The original implementation also raises PermissionDenied when the user
        is authenticated and fails the test. This mixin is used to force
        re-authentication for users that have exceeded the VERIFIED_TIMEOUT.
        '''
        if self.raise_exception:
            raise PermissionDenied(self.get_permission_denied_message())

        if self.request.user.is_verified:
            messages.info(
                self.request,
                _('We need to confirm your identity, please login again.'))

        path = self.request.build_absolute_uri()
        resolved_login_url = resolve_url(self.get_login_url())
        # If the login url is the same scheme and net location then use the
        # path as the "next" url.
        login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
        current_scheme, current_netloc = urlparse(path)[:2]
        if (not login_scheme or login_scheme == current_scheme) and (
            not login_netloc or login_netloc == current_netloc
        ):
            path = self.request.get_full_path()
        return redirect_to_login(
            path,
            resolved_login_url,
            self.get_redirect_field_name(),
        )


class SingleFactorRequiredMixin(UserPassesTestMixin):
    '''
    Verify that the user is authenticated with a single authentication factor.
    '''
    def test_func(self):
        return self.request.user.is_single_factor_authenticated


class MultiFactorRequiredMixin(UserPassesTestMixin):
    '''
    Verify that the user is authenticated with multiple authentication factors.
    '''
    def test_func(self):
        return self.request.user.is_verified


def is_recently_verified(request):
    '''
    Verify that the user has recently verified with a authentication device.
    '''
    if request.user.is_verified:
        if app_settings.KLEIDES_MFA_VERIFIED_TIMEOUT is None:
            return True

        try:
            verified_on = datetime.fromisoformat(
                request.session[VERIFIED_SESSION_KEY])
        except (KeyError, TypeError, ValueError):
            return False

        verified_seconds = (timezone.now() - verified_on).seconds
        if verified_seconds < app_settings.KLEIDES_MFA_VERIFIED_TIMEOUT:
            if app_settings.KLEIDES_MFA_VERIFIED_UPDATE:
                (request.session
                 [VERIFIED_SESSION_KEY]) = timezone.now().isoformat()
            return True

    return False


class RecentMultiFactorRequiredMixin(UserPassesTestMixin):
    '''
    Verify that the user has recently authenticated with multiple
    authentication factors.
    '''
    def test_func(self):
        return is_recently_verified(self.request)


def is_user_in_setup(request):
    '''
    Verify that the user account is in it's initial setup stage.
    '''
    return bool(
        request.user.is_single_factor_authenticated
        and not registry.user_has_device(request.user, confirmed=True))


class SetupOrMFARequiredMixin(UserPassesTestMixin):
    '''
    Verify that the user is authenticated with multiple factors or
    with single factor and is still in the process of account setup.
    '''
    def test_func(self):
        if self.request.user.is_verified:
            return True
        return is_user_in_setup(self.request)


class SetupOrRecentMFARequiredMixin(UserPassesTestMixin):
    '''
    Verify that the user is authenticated with multiple factors or
    with single factor and is still in the process of account setup.
    '''
    def test_func(self):
        if is_recently_verified(self.request):
            return True
        return is_user_in_setup(self.request)


class UnverifiedUserMixin(UserPassesTestMixin):
    '''
    Verify that the session is associated with a User.
    Note that the user may not be fully authenticated.
    '''
    def test_func(self):
        self.unverified_user = self.get_unverified_user()
        return bool(self.unverified_user is not None)

    def get_unverified_user(self):
        '''
        Return the unverified user model instance associated with the session.
        If no user is retrieved return None.
        '''
        user = None
        try:
            user_id = get_user_model()._meta.pk.to_python(
                self.request.session[SESSION_KEY])
            backend_path = self.request.session[BACKEND_SESSION_KEY]
        except KeyError:
            pass
        else:
            if backend_path in settings.AUTHENTICATION_BACKENDS:
                backend = load_backend(backend_path)
                user = backend.get_user(user_id)
                # Verify the session
                if hasattr(user, 'get_session_auth_hash'):
                    session_hash = self.request.session.get(HASH_SESSION_KEY)
                    session_hash_verified = bool(
                        session_hash and constant_time_compare(
                            session_hash,
                            user.get_session_auth_hash()))
                    if not session_hash_verified:
                        self.request.session.flush()
                        user = None

        return user
