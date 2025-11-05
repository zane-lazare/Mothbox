#!/usr/bin/env python3
"""
Wrapper script to run TakePhoto.py calibration independently.

Called by webUI /calibrate-photo endpoint via subprocess.
Ensures TakePhoto.py owns camera exclusively without conflicts.

This script:
1. Detects firmware version (4.x or 5.x) from controls.txt
2. Imports TakePhoto.py's run_calibration() function from correct firmware directory
3. Runs calibration (autofocus + exposure with flash)
4. Updates camera_settings.csv and LastCalibration timestamp
5. Exits cleanly for parent process to restart stream

Exit codes:
    0: Calibration successful
    1: Calibration failed (error details in stderr)
"""

import sys
from pathlib import Path

# Add mothbox root to Python path to import mothbox_paths
MOTHBOX_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(MOTHBOX_ROOT))

# Import firmware-aware path helpers
from mothbox_paths import get_firmware_version, get_takephoto_script

# Detect firmware version and get TakePhoto.py directory
firmware_version = get_firmware_version()
TAKEPHOTO_SCRIPT = get_takephoto_script()
TAKEPHOTO_DIR = TAKEPHOTO_SCRIPT.parent

print(f"Detected firmware version: {firmware_version}.x")
print(f"TakePhoto.py path: {TAKEPHOTO_SCRIPT}")

# Add TakePhoto.py directory to Python path for imports
sys.path.insert(0, str(TAKEPHOTO_DIR))

if __name__ == "__main__":
    try:
        # Import TakePhoto.py's calibration function
        from TakePhoto import run_calibration

        print("Starting photo calibration via TakePhoto.py...")

        # Run calibration
        # This will:
        # - Turn flash ON
        # - Run autofocus cycle
        # - Capture calibrated exposure and lens position
        # - Update camera_settings.csv
        # - Update LastCalibration timestamp
        # - Restart TakePhoto.py script (which we catch and exit cleanly)
        run_calibration()

        print("Photo calibration completed successfully")
        sys.exit(0)

    except FileNotFoundError as e:
        # TakePhoto.py not found for detected firmware version
        print(f"ERROR: {e}", file=sys.stderr)
        print(f"Firmware version detected: {firmware_version}.x", file=sys.stderr)
        print(f"Expected TakePhoto.py at: {TAKEPHOTO_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    except ImportError as e:
        # Failed to import TakePhoto.py or its dependencies
        print(f"ERROR: Failed to import TakePhoto.py: {e}", file=sys.stderr)
        print(f"Firmware directory: {TAKEPHOTO_DIR}", file=sys.stderr)
        print("Ensure TakePhoto.py exists and has valid Python syntax", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    except SystemExit as e:
        # TakePhoto.py calls restart_script() which does sys.exit()
        # We catch this to exit cleanly for the parent process
        if e.code == 0:
            print("Calibration completed (TakePhoto.py restart caught)")
            sys.exit(0)
        else:
            print(f"Calibration exited with code: {e.code}", file=sys.stderr)
            sys.exit(e.code if isinstance(e.code, int) else 1)

    except Exception as e:
        print(f"Photo calibration error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
