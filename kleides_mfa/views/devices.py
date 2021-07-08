# -*- coding: utf-8 -*-
from django.contrib import messages
from django.http import Http404
from django.views.generic import (
    CreateView, DeleteView, TemplateView, UpdateView)

from django_otp import DEVICE_ID_SESSION_KEY, login as django_otp_login

from ..registry import registry
from .mixins import (
    MultiFactorRequiredMixin, PluginMixin, SetupOrMFARequiredMixin)


class DeviceListView(SetupOrMFARequiredMixin, TemplateView):
    template_name = 'kleides_mfa/plugin_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plugins'] = registry.plugins_with_user_devices(
            self.request.user, confirmed=None)
        return context


class DeviceCreateView(SetupOrMFARequiredMixin, PluginMixin, CreateView):
    # XXX notification via email ?
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
        messages.success(
            self.request, self.plugin.get_create_message(self.object))
        return response


class DeviceUpdateView(MultiFactorRequiredMixin, PluginMixin, UpdateView):
    def get_form_class(self):
        return self.plugin.get_update_form_class()

    def form_valid(self, form):
        messages.success(
            self.request, self.plugin.get_update_message(self.object))
        return super().form_valid(form)


class DeviceDeleteView(MultiFactorRequiredMixin, PluginMixin, DeleteView):
    # XXX notification via email ?
    # XXX password confirmation ?
    def delete(self, request, *args, **kwargs):
        message = self.plugin.get_delete_message(self.get_object())
        response = super().delete(request, *args, **kwargs)
        messages.warning(request, message)
        # User has removed all authentication methods, disable his access.
        if not registry.user_has_device(self.request.user, confirmed=True):
            self.request.user.otp_device = None
            if DEVICE_ID_SESSION_KEY in self.request.session:
                del self.request.session[DEVICE_ID_SESSION_KEY]

        return response
