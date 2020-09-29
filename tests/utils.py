# -*- coding: utf-8 -*-
from contextlib import contextmanager
from unittest import mock


@contextmanager
def handle_signal(signal):
    """Create a signal handler and return it to the context."""
    handler = mock.Mock()
    signal.connect(handler)
    yield handler
    signal.disconnect(handler)
