#!/usr/bin/env python3
"""
Wrapper script to run TakePhoto.py calibration independently.

Called by webUI /calibrate-photo endpoint via subprocess.
Ensures TakePhoto.py owns camera exclusively without conflicts.

This script:
1. Imports TakePhoto.py's run_calibration() function
2. Runs calibration (autofocus + exposure with flash)
3. Updates camera_settings.csv and LastCalibration timestamp
4. Exits cleanly for parent process to restart stream

Exit codes:
    0: Calibration successful
    1: Calibration failed (error details in stderr)

Related: Issue #45 - Camera Calibration Architecture
"""
import sys
from pathlib import Path

# Add TakePhoto.py directory to Python path
TAKEPHOTO_DIR = Path(__file__).parent.parent.parent.parent / '5.x'
sys.path.insert(0, str(TAKEPHOTO_DIR))

if __name__ == '__main__':
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
