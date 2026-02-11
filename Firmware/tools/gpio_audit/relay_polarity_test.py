#!/usr/bin/env python3
"""
GPIO Relay Polarity Test (lgpio version)

Toggles each relay pin between HIGH and LOW with pauses,
printing the state at each step. An observer watching the
relay module should note when each relay clicks ON and OFF.

Usage: python3 relay_polarity_test.py
"""

import contextlib
import sys
import time

try:
    import lgpio
except ImportError:
    print("ERROR: lgpio not available. Run on Raspberry Pi 5.")
    sys.exit(1)

RELAY_PINS = {
    "Ch1 (Attract)": 5,
    "Ch2 (Flash)": 6,
    "Ch3": 13,
}

PAUSE = 3  # seconds between toggles


def test_pin(chip, name, pin):
    """Toggle a single pin and report states."""
    print(f"\n{'=' * 50}")
    print(f"Testing {name} -- GPIO {pin}")
    print(f"{'=' * 50}")

    # Claim as output, initial HIGH (safe for active-low)
    try:
        lgpio.gpio_claim_output(chip, pin, 1)  # initial HIGH
    except lgpio.error:
        # Pin might already be claimed — free it first
        with contextlib.suppress(Exception):
            lgpio.gpio_free(chip, pin)
        lgpio.gpio_claim_output(chip, pin, 1)

    state = lgpio.gpio_read(chip, pin)
    print(f"  Initial state: {'HIGH' if state else 'LOW'}")

    # Step 1: Set HIGH
    print(f"\n  >>> Setting GPIO {pin} HIGH...")
    lgpio.gpio_write(chip, pin, 1)
    state = lgpio.gpio_read(chip, pin)
    print(f"  State confirmed: {'HIGH' if state else 'LOW'}")
    print(f"  OBSERVE: Is the relay ON or OFF? (waiting {PAUSE}s)")
    time.sleep(PAUSE)

    # Step 2: Set LOW
    print(f"\n  >>> Setting GPIO {pin} LOW...")
    lgpio.gpio_write(chip, pin, 0)
    state = lgpio.gpio_read(chip, pin)
    print(f"  State confirmed: {'HIGH' if state else 'LOW'}")
    print(f"  OBSERVE: Is the relay ON or OFF? (waiting {PAUSE}s)")
    time.sleep(PAUSE)

    # Step 3: Return to HIGH
    print(f"\n  >>> Setting GPIO {pin} back to HIGH...")
    lgpio.gpio_write(chip, pin, 1)
    state = lgpio.gpio_read(chip, pin)
    print(f"  Final state: {'HIGH' if state else 'LOW'}")

    # Free the pin
    lgpio.gpio_free(chip, pin)
    print(f"  Pin freed. (waiting {PAUSE}s before next)")
    time.sleep(PAUSE)


def main():
    print("=" * 50)
    print("  RELAY POLARITY TEST")
    print("=" * 50)
    print()
    print("This test toggles each relay pin HIGH then LOW.")
    print("Watch/listen to the relay module and note when")
    print("each relay clicks ON and OFF.")
    print()
    print(f"Pins to test: {RELAY_PINS}")
    print(f"Pause between toggles: {PAUSE} seconds")
    print()
    print("Starting in 3 seconds...")
    time.sleep(3)

    chip = lgpio.gpiochip_open(0)

    try:
        for name, pin in RELAY_PINS.items():
            test_pin(chip, name, pin)

        print(f"\n{'=' * 50}")
        print("  TEST COMPLETE")
        print(f"{'=' * 50}")
        print()
        print("Results interpretation:")
        print("  If relay clicks ON when pin goes LOW  -> Active-LOW (standard)")
        print("  If relay clicks ON when pin goes HIGH -> Active-HIGH")
        print()
        print("All pins left at HIGH (relay OFF for active-low modules).")

    except KeyboardInterrupt:
        print("\n\nInterrupted! Setting all pins HIGH...")
        for _name, pin in RELAY_PINS.items():
            try:
                lgpio.gpio_write(chip, pin, 1)
                lgpio.gpio_free(chip, pin)
            except Exception:
                pass

    finally:
        lgpio.gpiochip_close(chip)


if __name__ == "__main__":
    main()
