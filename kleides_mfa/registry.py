# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from collections import namedtuple

from django.forms import modelform_factory
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .forms import DeviceUpdateForm
from .settings import PLUGIN_PRIORITY

__all__ = ['registry']

KleidesPluginDevices = namedtuple('KleidesPluginDevices', 'plugin devices')
KleidesPluginDevice = namedtuple('KleidesPluginDevice', 'plugin device')


class AlreadyRegistered(Exception):
    pass


class KleidesMfaPlugin():
    def __init__(
            self, name, model, create_form_class=None, update_form_class=None,
            verify_form_class=None, show_create_button=True,
            create_message=None, update_message=None, delete_message=None,
            show_verify_button=True, device_list_javascript=None,
            device_list_template=None):
        self.slug = slugify(name)
        self.name = name
        self.model = model
        self.create_form_class = create_form_class
        self.update_form_class = update_form_class
        self.verify_form_class = verify_form_class
        self.create_message = create_message
        self.update_message = update_message
        self.delete_message = delete_message
        self.device_list_javascript = device_list_javascript
        self.device_list_template = device_list_template
        self.show_create_button = show_create_button
        self.show_verify_button = show_verify_button

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'KleidesMfaPlugin(name={!r}, model={!r})'.format(
            self.name, self.model)

    def get_create_form_class(self):
        return self.create_form_class

    def get_update_form_class(self):
        if self.update_form_class is None:
            return modelform_factory(
                self.model, form=DeviceUpdateForm, fields=('name',))
        return self.update_form_class

    def get_verify_form_class(self):
        return self.verify_form_class

    def get_create_message(self, device):
        if self.create_message is not None:
            message = self.create_message
        else:
            message = _('The {plugin} "{name}" was added successfully.')
        return message.format(plugin=self.name, name=device.name)

    def get_update_message(self, device):
        if self.update_message is not None:
            message = self.update_message
        else:
            message = _('The {plugin} "{name}" was changed successfully.')
        return message.format(plugin=self.name, name=device.name)

    def get_delete_message(self, device):
        if self.delete_message is not None:
            message = self.delete_message
        else:
            message = _('The {plugin} "{name}" was deleted successfully.')
        return message.format(plugin=self.name, name=device.name)

    def get_user_device(self, device_id, user, confirmed=True):
        return self.model.objects.devices_for_user(user, confirmed).get(
            pk=device_id)

    def get_user_devices(self, user, confirmed=True):
        devices = []
        for device in self.model.objects.devices_for_user(user, confirmed):
            devices.append(device)
        return devices


class KleidesMfaPluginRegistry():
    '''
    A registry to store and manage access to KleidesMfaPlugins.
    '''
    def __init__(self):
        self._registry = {}  # plugin.slug -> plugin

    def register_plugin(self, plugin):
        if plugin.slug in self._registry:
            raise AlreadyRegistered(
                'Plugin with slug {} already registered'.format(plugin.slug))
        self._registry[plugin.slug] = plugin

    def register(self, *args, **kwargs):
        self.register_plugin(KleidesMfaPlugin(*args, **kwargs))

    def unregister(self, name_or_slug):
        return self._registry.pop(slugify(name_or_slug))

    def get_plugin(self, slug):
        return self._registry[slug]

    def plugins(self):
        '''
        Return an iterable of registered plugins in settings.PLUGIN_PRIORITY.
        '''
        for slug in PLUGIN_PRIORITY:
            if slug in self._registry:
                yield self._registry[slug]

    def user_has_device(self, user, confirmed=True):
        for plugin in self.plugins():
            if plugin.get_user_devices(user, confirmed):
                return True
        return False

    def plugins_with_user_devices(self, user, confirmed=True):
        '''
        Return an iterable of the plugins with devices registered by the user.
        '''
        return [
            KleidesPluginDevices(
                plugin, plugin.get_user_devices(user, confirmed))
            for plugin in self.plugins()]

    def user_devices_with_plugin(self, user, confirmed=True):
        return [
            KleidesPluginDevice(plugin, device)
            for plugin in self.plugins()
            for device in plugin.get_user_devices(user, confirmed)
        ]

    def user_authentication_method(self, user):
        '''
        Return the authentication method of a logged in User.
        '''
        if user.is_verified:
            otp_class = user.otp_device.__class__
            return next(
                plugin.slug for plugin in self.plugins()
                if otp_class == plugin.model)


registry = KleidesMfaPluginRegistry()
