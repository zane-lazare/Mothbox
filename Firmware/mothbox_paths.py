"""
Minimal stub of mothbox_paths for Issue #100.

This is a temporary stub for testing. The full implementation exists
in the main branch and will be available when this branch is merged.
"""

from pathlib import Path
import os

# Determine base directory
MOTHBOX_HOME = Path(os.environ.get('MOTHBOX_HOME', '/tmp/mothbox'))

# Standard paths
CONFIG_DIR = MOTHBOX_HOME / 'config'
DATA_DIR = MOTHBOX_HOME / 'data'
PHOTOS_DIR = MOTHBOX_HOME / 'photos'

# Create directories if they don't exist (for testing)
for directory in [CONFIG_DIR, DATA_DIR, PHOTOS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
