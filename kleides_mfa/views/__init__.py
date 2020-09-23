# -*- coding: utf-8 -*-
from .auth import LoginView, DeviceVerifyView
from .devices import (
    DeviceDeleteView, DeviceCreateView, DeviceListView, DeviceUpdateView)

__all__ = [
    'DeviceDeleteView', 'DeviceCreateView', 'DeviceListView',
    'DeviceUpdateView', 'DeviceVerifyView', 'LoginView', 'VerifyView',
]
