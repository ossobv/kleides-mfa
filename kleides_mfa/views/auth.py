# -*- coding: utf-8 -*-
from django.contrib.auth import login
from django.contrib.auth.signals import user_login_failed
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlencode

from .mixins import (
    BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, VERIFIED_SESSION_KEY,
    PluginMixin, UnverifiedUserMixin)
from .. import settings
from ..registry import registry


class LoginView(DjangoLoginView):
    template_name = 'kleides_mfa/login.html'

    def get_success_url(self, has_device=False):
        if not has_device:
            return resolve_url(settings.SINGLE_FACTOR_URL)
        return super().get_success_url()

    def form_valid(self, form):
        # If the user has any authentication methods remaining they must be
        # used *before the user is logged in*.
        user = form.get_user()
        user_devices = registry.user_devices_with_plugin(user, confirmed=True)
        if user_devices:
            # Store the User data in the session so we can call Django login
            # after verifying a 2nd device.
            session = self.request.session
            session[SESSION_KEY] = user._meta.pk.value_to_string(user)
            session[BACKEND_SESSION_KEY] = user.backend
            if hasattr(user, 'get_session_auth_hash'):
                session[HASH_SESSION_KEY] = user.get_session_auth_hash()

            # Devices are sorted by security/type.
            plugin, device = user_devices[0]
            redirect_url = reverse(
                'kleides_mfa:verify', args=[plugin.slug, device.pk])
            params = urlencode(
                {self.redirect_field_name: self.get_success_url(
                    has_device=True)})
            return HttpResponseRedirect('{}?{}'.format(redirect_url, params))
        # Otherwise the user is authenticated with a single factor and will
        # have to fortify his account by adding authentication methods.
        return super().form_valid(form)


class DeviceVerifyView(UnverifiedUserMixin, PluginMixin, DjangoLoginView):
    template_name_suffix = '_verify_form'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except self.get_plugin().model.DoesNotExist:
            # A user tried to access a device that no longer exists or belongs
            # to another user. Flush the session and restart authentication.
            request.session.flush()
            redirect_url = reverse('kleides_mfa:login')
            params = urlencode(
                {self.redirect_field_name: self.get_success_url()})
            return HttpResponseRedirect('{}?{}'.format(redirect_url, params))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['device'] = self.object
        context['user_devices'] = registry.user_devices_with_plugin(
            self.unverified_user, confirmed=True)
        context['unverified_user'] = self.unverified_user
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['unverified_user'] = self.unverified_user
        kwargs['device'] = self.object
        return kwargs

    def get_form_class(self):
        form_class = self.plugin.get_verify_form_class()
        if form_class is None:
            raise Http404(
                'Plugin {} does not support this'.format(self.plugin))
        return form_class

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
        try:
            del self.request.session[SESSION_KEY]
            del self.request.session[BACKEND_SESSION_KEY]
            if hasattr(user, 'get_session_auth_hash'):
                del self.request.session[HASH_SESSION_KEY]
        except KeyError:
            # Login can flush the session if it belonged to another user.
            pass
        # Add the last verification time to the session.
        self.request.session[VERIFIED_SESSION_KEY] = force_str(timezone.now())
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        # The device verification failed, fire login_failed signal like Django
        # does on failed autentication attempts against all backends.
        # Token will be excluded from credentials so just provide an empty
        # dictionary and log the user and device that were protected.
        user_login_failed.send(
            sender=__name__, credentials={}, request=self.request,
            user=self.unverified_user, device=self.object)
        return super().form_invalid(form)
