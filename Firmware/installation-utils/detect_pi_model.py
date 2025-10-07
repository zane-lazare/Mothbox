#!/usr/bin/env python3
"""
Raspberry Pi Model Detection Utility

Detects whether the system is running on a Raspberry Pi 4 or Pi 5.
Returns "4" or "5" for use by installation scripts.

Usage:
    python3 detect_pi_model.py

Exit codes:
    0: Success (Pi 4 or Pi 5 detected)
    1: Error (unknown model or not a Raspberry Pi)
"""

import sys


def detect_pi_model():
    """
    Detect Raspberry Pi model by reading /proc/cpuinfo.

    Returns:
        str: "4" for Pi 4, "5" for Pi 5

    Raises:
        RuntimeError: If model cannot be determined or is unsupported
    """
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Model"):
                    model = line.split(":")[1].strip()

                    if "Pi 4" in model or "Raspberry Pi 4" in model:
                        return "4"
                    elif "Pi 5" in model or "Raspberry Pi 5" in model:
                        return "5"
                    else:
                        raise RuntimeError(f"Unsupported Raspberry Pi model: {model}")

            # If we get here, no Model line was found
            raise RuntimeError("Could not find Model information in /proc/cpuinfo")

    except FileNotFoundError:
        raise RuntimeError("/proc/cpuinfo not found - are you running on Linux?")
    except Exception as e:
        raise RuntimeError(f"Error reading /proc/cpuinfo: {e}")


if __name__ == "__main__":
    try:
        pi_version = detect_pi_model()
        print(pi_version)
        sys.exit(0)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("\nMothbox supports Raspberry Pi 4 and Pi 5 only.", file=sys.stderr)
        sys.exit(1)
