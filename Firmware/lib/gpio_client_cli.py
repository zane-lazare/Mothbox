#!/usr/bin/env python3
"""CLI wrapper for GPIO daemon client.

Usage:
    python3 gpio_client_cli.py set attract on
    python3 gpio_client_cli.py set flash off
    python3 gpio_client_cli.py get attract
    python3 gpio_client_cli.py read off_pin
    python3 gpio_client_cli.py status
    python3 gpio_client_cli.py ping
"""

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.gpio_protocol import RECV_BUFFER_SIZE, SOCKET_PATH, SOCKET_TIMEOUT


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = " ".join(sys.argv[1:]).upper()

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect(SOCKET_PATH)
            sock.sendall((command + "\n").encode())
            response = sock.recv(RECV_BUFFER_SIZE).decode().strip()
            print(response)
    except ConnectionRefusedError:
        print(f"ERROR: daemon not running at {SOCKET_PATH}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError:
        print(f"ERROR: daemon not responding within {SOCKET_TIMEOUT}s", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
