"""GPIO daemon IPC protocol constants and shared types.

Shared between gpio_daemon.py and gpio_client.py to avoid circular imports.
"""

SOCKET_PATH = "/run/mothbox/gpio.sock"
SOCKET_TIMEOUT = 2.0


class GPIODaemonError(Exception):
    """Raised by mutations (relay_on, relay_off, write_gpio_state, read_switch)
    when the daemon is unreachable or returns ERR.

    Flask routes catch this and return HTTP 503.
    Cron scripts let it propagate (crash = visible in journalctl)."""
