# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from .auth import LoginView, DeviceVerifyView
from .device import (
    DeviceDeleteView, DeviceCreateView, DeviceListView, DeviceUpdateView)

__all__ = [
    'DeviceDeleteView', 'DeviceCreateView', 'DeviceListView',
    'DeviceUpdateView', 'DeviceVerifyView', 'LoginView', 'VerifyView',
]
