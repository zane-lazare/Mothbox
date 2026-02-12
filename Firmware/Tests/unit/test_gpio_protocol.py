"""Tests for GPIO daemon IPC protocol constants and exceptions."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.gpio_protocol import (
    SOCKET_PATH,
    SOCKET_TIMEOUT,
    GPIODaemonError,
)


@pytest.mark.unit
class TestGPIODaemonError:
    """GPIODaemonError exception class."""

    def test_is_exception(self):
        assert issubclass(GPIODaemonError, Exception)

    def test_message(self):
        err = GPIODaemonError("daemon not running")
        assert str(err) == "daemon not running"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(GPIODaemonError, match="test"):
            raise GPIODaemonError("test")


@pytest.mark.unit
class TestProtocolConstants:
    """IPC protocol constants."""

    def test_socket_path(self):
        assert SOCKET_PATH == "/run/mothbox/gpio.sock"

    def test_socket_timeout(self):
        assert SOCKET_TIMEOUT == 2.0
