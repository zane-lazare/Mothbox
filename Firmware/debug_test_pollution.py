#!/usr/bin/env python3
"""
Debug script to investigate test pollution in thumbnail cache tests.

This script adds instrumentation to understand why photo_path.resolve().exists()
returns False in the full test suite but not in isolation.
"""

import os
import sys
from pathlib import Path

# Monkey-patch Path.exists() to log all checks
original_exists = Path.exists

def debug_exists(self):
    """Instrumented exists() that logs all checks"""
    result = original_exists(self)
    # Only log for paths containing "photos" to reduce noise
    if "photos" in str(self):
        print(f"DEBUG exists(): {self} -> {result} (cwd: {os.getcwd()})", file=sys.stderr)
        if not result and self.is_absolute():
            # Check if parent exists
            print(f"  Parent exists: {self.parent.exists()}", file=sys.stderr)
            if self.parent.exists():
                print(f"  Parent contents: {list(self.parent.iterdir())}", file=sys.stderr)
    return result

Path.exists = debug_exists

# Now run pytest with this instrumentation
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(sys.argv[1:]))
