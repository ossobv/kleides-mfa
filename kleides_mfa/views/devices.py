# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib import messages
from django.forms import modelform_factory
from django.http import Http404
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (
    CreateView, DeleteView, TemplateView, UpdateView)

from ..forms import DeviceUpdateForm
from ..registry import registry
from .mixins import (
    MultiFactorRequiredMixin, PluginMixin, SetupOrMFARequiredMixin,
    SingleFactorRequiredMixin)


class DeviceListView(SingleFactorRequiredMixin, TemplateView):
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
        if self.plugin.create_form is None:
            raise Http404(
                'Plugin {} does not support this'.format(self.plugin))
        return self.plugin.create_form


class DeviceUpdateView(MultiFactorRequiredMixin, PluginMixin, UpdateView):
    def get_form_class(self):
        if self.plugin.update_form is None:
            return modelform_factory(
                self.plugin.model, form=DeviceUpdateForm, fields=('name',))
        return self.plugin.update_form


class DeviceDeleteView(MultiFactorRequiredMixin, PluginMixin, DeleteView):
    # XXX notification via email ?
    # XXX password confirmation ?
    def delete(self, request, *args, **kwargs):
        message = _(
            'The {plugin} "{name}" was deleted successfully.').format(
                plugin=self.plugin, name=self.get_object().name)
        response = super().delete(request, *args, **kwargs)
        messages.warning(request, message)
        return response
