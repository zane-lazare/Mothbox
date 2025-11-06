"""
Helper to import mothbox_paths module from correct location.
This handles production, legacy, and custom MOTHBOX_HOME installations.
"""

import os
import sys
from pathlib import Path


def setup_mothbox_path():
    """Add mothbox installation directory to Python path"""
    # Check for environment variable override first
    mothbox_home = os.environ.get("MOTHBOX_HOME")

    if mothbox_home:
        # Custom installation via environment variable
        sys.path.insert(0, mothbox_home)
    elif Path("/opt/mothbox").exists():
        # Production FHS-compliant installation
        sys.path.insert(0, "/opt/mothbox")
    else:
        # Legacy Desktop installation
        sys.path.insert(0, "/home/pi/Desktop/Mothbox")


# Run automatically when imported
setup_mothbox_path()
