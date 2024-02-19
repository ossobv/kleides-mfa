# -*- coding: utf-8 -*-
from django.contrib import messages
from django.http import Http404
from django.utils import timezone
from django.views.generic import (
    CreateView, DeleteView, TemplateView, UpdateView)

from django_otp import DEVICE_ID_SESSION_KEY, login as django_otp_login

from ..registry import registry
from ..signals import mfa_added, mfa_removed
from .mixins import (
    VERIFIED_SESSION_KEY, PluginMixin, RecentMultiFactorRequiredMixin,
    SetupOrMFARequiredMixin, SetupOrRecentMFARequiredMixin)


class DeviceListView(SetupOrMFARequiredMixin, TemplateView):
    template_name = 'kleides_mfa/plugin_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plugins'] = registry.plugins_with_user_devices(
            self.request.user, confirmed=None)
        return context


class DeviceCreateView(SetupOrRecentMFARequiredMixin, PluginMixin, CreateView):
    template_name_suffix = '_create_form'

    def get_form_class(self):
        form_class = self.plugin.get_create_form_class()
        if form_class is None:
            raise Http404(
                'Plugin {} does not support this'.format(self.plugin))
        return form_class

    def form_valid(self, form):
        response = super().form_valid(form)
        # This is the users first device, use it to verify the user.
        if not self.request.user.is_verified:
            django_otp_login(self.request, self.object)
            # Add the last verification time to the session.
            # Note that the verified session parameters should match the
            # session when authenticating in DeviceVerifyView.
            self.request.session[
                VERIFIED_SESSION_KEY] = timezone.now().isoformat()
        messages.success(
            self.request, self.plugin.get_create_message(self.object))
        mfa_added.send(
            sender=__name__, instance=self.object, request=self.request)
        return response


class DeviceUpdateView(
        RecentMultiFactorRequiredMixin, PluginMixin, UpdateView):
    def get_form_class(self):
        return self.plugin.get_update_form_class()

    def form_valid(self, form):
        messages.success(
            self.request, self.plugin.get_update_message(self.object))
        return super().form_valid(form)


class DeviceDeleteView(
        RecentMultiFactorRequiredMixin, PluginMixin, DeleteView):
    def get_form_class(self):
        return self.plugin.get_delete_form_class()

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        mfa_removed.send(sender=__name__, instance=obj, request=request)
        message = self.plugin.get_delete_message(obj)
        response = super().post(request, *args, **kwargs)
        messages.warning(request, message)
        # User has removed all authentication methods, disable his access.
        if not registry.user_has_device(self.request.user, confirmed=True):
            self.request.user.otp_device = None
            if DEVICE_ID_SESSION_KEY in self.request.session:
                del self.request.session[DEVICE_ID_SESSION_KEY]

        return response
