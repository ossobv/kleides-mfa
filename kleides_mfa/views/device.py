# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import modelform_factory
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (
    CreateView, DeleteView, TemplateView, UpdateView)

from ..forms import DeviceUpdateForm
from ..registry import registry


class DeviceListView(LoginRequiredMixin, TemplateView):
    template_name = 'kleides_mfa/plugin_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plugins'] = registry.plugins_with_user_devices(
            self.request.user, confirmed=None)
        return context


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


class DeviceCreateView(LoginRequiredMixin, PluginMixin, CreateView):
    template_name_suffix = '_create_form'

    def get_form_class(self):
        if self.plugin.create_form is None:
            raise Http404(
                'Plugin {} does not support this'.format(self.plugin))
        return self.plugin.create_form


class DeviceUpdateView(LoginRequiredMixin, PluginMixin, UpdateView):
    def get_form_class(self):
        if self.plugin.update_form is None:
            return modelform_factory(
                self.plugin.model, form=DeviceUpdateForm, fields=('name',))
        return self.plugin.update_form


class DeviceDeleteView(LoginRequiredMixin, PluginMixin, DeleteView):
    # XXX notification via email ?
    # XXX password confirmation ?
    def delete(self, request, *args, **kwargs):
        message = _(
            'The {plugin} "{name}" was deleted successfully.').format(
                plugin=self.plugin, name=self.get_object().name)
        response = super().delete(request, *args, **kwargs)
        messages.warning(request, message)
        return response
