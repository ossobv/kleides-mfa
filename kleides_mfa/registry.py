# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from collections import namedtuple

from django.utils.text import slugify

from .settings import PLUGIN_PRIORITY

__all__ = ['registry']

KleidesPluginDevices = namedtuple('KleidesPluginDevices', 'plugin devices')
KleidesPluginDevice = namedtuple('KleidesPluginDevice', 'plugin device')


class AlreadyRegistered(Exception):
    pass


class KleidesMfaPlugin():
    def __init__(
            self, name, model, create_form=None, update_form=None,
            verify_form=None, show_create_button=True, show_verify_button=True,
            device_list_javascript=None, device_list_template=None):
        self.slug = slugify(name)
        self.name = name
        self.model = model
        self.create_form = create_form
        self.update_form = update_form
        self.verify_form = verify_form
        self.device_list_javascript = device_list_javascript
        self.device_list_template = device_list_template
        self.show_create_button = show_create_button
        self.show_verify_button = show_verify_button

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'KleidesMfaPlugin(name={!r}, model={!r})'.format(
            self.name, self.model)

    def __eq__(self, other):
        return bool(
            self.__class__ == other.__class__ and self.slug == other.slug)

    def __hash__(self):
        return hash(self.slug)

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

    def get_plugin(self, slug):
        return self._registry[slug]

    def plugins(self):
        '''
        Return an iterable of registered plugins in settings.PLUGIN_PRIORITY.
        '''
        for slug in PLUGIN_PRIORITY:
            if slug in self._registry:
                yield self._registry[slug]

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


registry = KleidesMfaPluginRegistry()
