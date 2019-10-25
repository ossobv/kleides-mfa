# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.auth import get_user_model, load_backend, login
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_text
from django.utils.http import urlencode

from .device import PluginMixin
from ..registry import registry

# Note that these session keys are different from django auth so the user
# session will never pass as authenticated. Meanwhile we still need to enforce
# the same protections which is the reason for the duplication.
SESSION_KEY = '_kleides-mfa_user_id'
BACKEND_SESSION_KEY = '_kleides-mfa_user_backend'
HASH_SESSION_KEY = '_kleides-mfa_user_hash'
VERIFIED_SESSION_KEY = '_kleides-mfa_user_verified'


class UnverifiedUserMixin(UserPassesTestMixin):
    '''
    Verify that the current session is associated with a User.
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


class LoginView(DjangoLoginView):
    template_name = 'kleides_mfa/login.html'

    def form_valid(self, form):
        # If the user has any authentication methods remaining they must be
        # used before the user is logged in.
        user = form.get_user()
        user_devices = registry.user_devices_with_plugin(user, confirmed=True)
        if user_devices:
            # Store the user in the session.
            # don't allow the session to be seen as a authenticated user so
            # use our own session key values.
            session = self.request.session
            session[SESSION_KEY] = user._meta.pk.value_to_string(user)
            session[BACKEND_SESSION_KEY] = user.backend
            if hasattr(user, 'get_session_auth_hash'):
                session[HASH_SESSION_KEY] = user.get_session_auth_hash()
            plugin, device = user_devices[0]
            redirect_url = reverse(
                'kleides_mfa:verify', args=[plugin.slug, device.pk])
            params = urlencode(
                {self.redirect_field_name: self.get_success_url()})
            return HttpResponseRedirect('{}?{}'.format(redirect_url, params))
        # The user only has password authentication and will be logged in.
        return super().form_valid(form)


class DeviceVerifyView(UnverifiedUserMixin, PluginMixin, LoginView):
    template_name_suffix = '_verify_form'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['device'] = self.get_object()
        context['user_devices'] = registry.user_devices_with_plugin(
            self.unverified_user, confirmed=True)
        context['unverified_user'] = self.unverified_user
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['unverified_user'] = self.unverified_user
        kwargs['device'] = self.get_object()
        return kwargs

    def get_form_class(self):
        if self.plugin.verify_form is None:
            raise Http404(
                'Plugin {} does not support this'.format(self.plugin))
        return self.plugin.verify_form

    def get_object(self):
        # Fetch the the confirmed device of the unverified user.
        return self.plugin.get_user_device(
            self.kwargs['device_id'], self.unverified_user, confirmed=True)

    def form_valid(self, form):
        # User is now verified.
        user = form.get_user()
        # Pass otp device to django-otp.
        user.otp_device = form.get_device()
        # Perform django session login.
        login(self.request, user, self.request.session[BACKEND_SESSION_KEY])
        # Cleanup kleides_mfa session data.
        del self.request.session[SESSION_KEY]
        del self.request.session[BACKEND_SESSION_KEY]
        if hasattr(user, 'get_session_auth_hash'):
            del self.request.session[HASH_SESSION_KEY]
        # Add the last verification time to the session.
        self.request.session[VERIFIED_SESSION_KEY] = force_text(timezone.now())
        return HttpResponseRedirect(self.get_success_url())
