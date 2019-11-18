# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.auth import get_user_model, load_backend
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.crypto import constant_time_compare

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


class SetupOrMFARequiredMixin(UserPassesTestMixin):
    '''
    Verify that the user is authenticated with multiple factors or with single
    factor and is still in the process of account setup.
    '''
    def test_func(self):
        user = self.request.user
        if user.is_verified:
            return True
        return (
            user.is_single_factor_authenticated
            and not registry.user_has_device(user, confirmed=True))


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
