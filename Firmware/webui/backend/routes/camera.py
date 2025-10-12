"""Camera control endpoints"""
from flask import Blueprint, jsonify, request
import subprocess
from pathlib import Path
import sys

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import MOTHBOX_HOME, PHOTOS_DIR

# Allowed camera settings with validation functions (Phase 2.1: expanded controls)
ALLOWED_CAMERA_SETTINGS = {
    # Image quality controls
    'Sharpness': lambda v: 0.0 <= float(v) <= 16.0,
    'Brightness': lambda v: -1.0 <= float(v) <= 1.0,
    'Contrast': lambda v: -1.0 <= float(v) <= 1.0,
    'Saturation': lambda v: -1.0 <= float(v) <= 1.0,

    # Exposure controls
    'ExposureTime': lambda v: str(v).isdigit() and 0 < int(v) < 1000000,  # microseconds
    'ExposureValue': lambda v: -8.0 <= float(v) <= 8.0,  # EV compensation
    'AnalogueGain': lambda v: 1.0 <= float(v) <= 16.0,  # ISO gain
    'AeEnable': lambda v: str(v).lower() in ['true', 'false'],  # Auto exposure

    # Focus controls (Phase 2.1)
    'AfMode': lambda v: int(v) in [0, 1, 2],  # 0=Manual, 1=Auto Single, 2=Continuous
    'AfSpeed': lambda v: int(v) in [0, 1],  # 0=Normal, 1=Fast
    'AfRange': lambda v: int(v) in [0, 1, 2],  # 0=Normal, 1=Macro, 2=Full
    'AfMetering': lambda v: int(v) in [0, 1, 2],  # Metering mode
    'LensPosition': lambda v: 0.0 <= float(v) <= 10.0,  # Diopters (manual focus)

    # White balance controls (Phase 2.1)
    'AwbEnable': lambda v: str(v).lower() in ['true', 'false'],
    'AwbMode': lambda v: 0 <= int(v) <= 7,  # 0=Auto, 1=Incandescent, ..., 7=Custom

    # HDR/Bracketing (Phase 2.1)
    'HDR': lambda v: int(v) in [1, 3, 5, 7],  # Number of bracketed exposures
    'HDR_width': lambda v: 1000 <= int(v) <= 50000,  # Bracket step size (µs)

    # Auto-calibration (Phase 2.1)
    'AutoCalibration': lambda v: int(v) in [0, 1],  # 0=Off, 1=On
    'AutoCalibrationPeriod': lambda v: 1 <= int(v) <= 10000,  # Photos between calibrations

    # Image format
    'ImageFileType': lambda v: int(v) in [0, 1, 2],  # 0=JPEG, 1=PNG, 2=BMP
    'VerticalFlip': lambda v: int(v) in [0, 1],  # 0=No flip, 1=Flip
}

camera_bp = Blueprint('camera', __name__)

@camera_bp.route('/capture', methods=['POST'])
def capture_photo():
    """Trigger a photo capture"""
    try:
        # Determine Pi version to find correct TakePhoto.py
        import platform
        from mothbox_paths import MOTHBOX_HOME

        print(f"Photo capture requested. MOTHBOX_HOME: {MOTHBOX_HOME}")

        # Check if Pi 4 or Pi 5
        pi_version = None
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("Model"):
                        if "Pi 4" in line:
                            pi_version = "4"
                        elif "Pi 5" in line:
                            pi_version = "5"
                        break
        except Exception as cpu_error:
            print(f"Error reading /proc/cpuinfo: {cpu_error}")

        # Default to 4.x if can't determine
        if not pi_version:
            pi_version = "4"
            print(f"Could not detect Pi version, defaulting to {pi_version}")
        else:
            print(f"Detected Pi version: {pi_version}")

        script_path = MOTHBOX_HOME / f"{pi_version}.x" / "TakePhoto.py"
        print(f"Looking for TakePhoto.py at: {script_path}")

        if not script_path.exists():
            error_msg = f'TakePhoto.py not found at {script_path}'
            print(error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500

        print(f"Running: python3 {script_path}")
        result = subprocess.run(
            ['python3', str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )

        print(f"TakePhoto.py exit code: {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        if result.returncode == 0:
            # Find the most recent photo
            photos = sorted(PHOTOS_DIR.glob('**/*.jpg'), key=lambda p: p.stat().st_mtime, reverse=True)
            latest_photo = str(photos[0].relative_to(PHOTOS_DIR)) if photos else None

            # Invalidate photo count cache so dashboard shows updated count immediately
            from routes.system import invalidate_photo_count_cache
            invalidate_photo_count_cache()

            return jsonify({
                'success': True,
                'latest_photo': latest_photo,
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr or result.stdout
            }), 500

    except subprocess.TimeoutExpired:
        error_msg = 'Photo capture timed out'
        print(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 500
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Photo capture error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

@camera_bp.route('/settings', methods=['GET'])
def get_camera_settings():
    """Get camera settings from CSV (vertical format: SETTING,VALUE,DETAILS)"""
    try:
        from mothbox_paths import CAMERA_SETTINGS_FILE
        import csv

        settings = {}
        with open(CAMERA_SETTINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Build settings dict from vertical CSV format
                setting_name = row['SETTING'].strip()
                setting_value = row['VALUE'].strip()
                settings[setting_name] = setting_value

        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@camera_bp.route('/settings', methods=['POST'])
def update_camera_settings():
    """Update camera settings (vertical CSV format: SETTING,VALUE,DETAILS)"""
    try:
        from mothbox_paths import CAMERA_SETTINGS_FILE
        import csv

        new_settings = request.json

        # Validate camera settings
        for key, value in new_settings.items():
            if key not in ALLOWED_CAMERA_SETTINGS:
                return jsonify({'error': f'Invalid setting: {key}'}), 400
            try:
                if not ALLOWED_CAMERA_SETTINGS[key](value):
                    return jsonify({'error': f'Invalid value for {key}'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': f'Invalid type for {key}'}), 400

        # Read current settings (vertical format: each row is a setting)
        csv_rows = []
        with open(CAMERA_SETTINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_rows.append(dict(row))

        # Sanitize values to prevent CSV injection (defense in depth)
        # Lazy import to avoid circular dependency with app.py
        from routes.config import _sanitize_csv_value
        sanitized_settings = {k: _sanitize_csv_value(v) for k, v in new_settings.items()}

        # Update the corresponding rows
        for setting_name, setting_value in sanitized_settings.items():
            # Find and update the row for this setting
            found = False
            for row in csv_rows:
                if row['SETTING'].strip() == setting_name:
                    row['VALUE'] = str(setting_value)
                    found = True
                    break

            # If setting doesn't exist, add a new row
            if not found:
                csv_rows.append({
                    'SETTING': setting_name,
                    'VALUE': str(setting_value),
                    'DETAILS': ''
                })

        # Write back all settings in vertical format
        with open(CAMERA_SETTINGS_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['SETTING', 'VALUE', 'DETAILS'])
            writer.writeheader()
            writer.writerows(csv_rows)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@camera_bp.route('/autofocus', methods=['POST'])
def trigger_autofocus():
    """
    Trigger autofocus cycle (Phase 2.2)

    Based on PlowmanAutofocus.py and TakePhoto.py:410 pattern.

    Returns:
        JSON with:
        - success: bool - whether autofocus succeeded
        - af_state: str - "Idle", "Scanning", "Success", or "Fail"
        - lens_position: float - final lens position in diopters
        - metadata: dict - exposure, gain, etc. from final frame
    """
    try:
        # Import here to avoid issues if picamera2 not available
        try:
            from picamera2 import Picamera2
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'picamera2 not available'
            }), 500

        import time
        from flask import current_app

        print("Autofocus requested via API")

        # Release camera hardware if initialized (prevents resource conflict)
        camera_streamer = current_app.config.get('CAMERA_STREAMER')
        was_streaming = False
        if camera_streamer and camera_streamer.camera:
            print("Releasing camera hardware before autofocus...")
            was_streaming = camera_streamer.streaming
            camera_streamer.release_camera()
            time.sleep(0.5)  # Let camera fully release

        # Initialize camera for autofocus
        picam2 = None
        try:
            # Try camera 0 first, fallback to camera 1
            try:
                picam2 = Picamera2(0)
            except Exception:
                picam2 = Picamera2(1)

            # Configure for high-res preview (better for AF accuracy)
            preview_config = picam2.create_preview_configuration(
                main={'format': 'RGB888', 'size': (1920, 1080)}
            )
            picam2.configure(preview_config)

            # Start camera
            picam2.start()

            # Set initial focus controls for AF
            picam2.set_controls({
                "AfSpeed": 0,  # Normal speed for accuracy
                "AfMetering": 0,  # Auto metering
                "LensPosition": 7.0  # Starting position
            })

            # Let camera stabilize
            time.sleep(0.3)

            # Trigger autofocus cycle
            print("Running autofocus cycle...")
            af_start = time.time()
            success = picam2.autofocus_cycle()
            af_duration = time.time() - af_start
            print(f"Autofocus completed in {af_duration:.2f}s: {'Success' if success else 'Failed'}")

            # Get result metadata
            metadata = picam2.capture_metadata()
            lens_position = metadata.get('LensPosition', 0.0)
            af_state_code = metadata.get('AfState', 0)
            af_state = ("Idle", "Scanning", "Success", "Fail")[af_state_code]

            # Capture additional metadata for UI display
            exposure_time = metadata.get('ExposureTime', 0)
            analogue_gain = metadata.get('AnalogueGain', 0.0)
            colour_temp = metadata.get('ColourTemperature', 0)

            # Stop camera
            picam2.stop()
            picam2.close()

            return jsonify({
                'success': success,
                'af_state': af_state,
                'lens_position': round(lens_position, 2),
                'duration_seconds': round(af_duration, 2),
                'metadata': {
                    'exposure_time': exposure_time,
                    'analogue_gain': round(analogue_gain, 2),
                    'colour_temperature': colour_temp
                },
                'message': f'Autofocus {"succeeded" if success else "failed"} at {lens_position:.2f} diopters'
            })

        except Exception as camera_error:
            # Ensure camera is closed on error
            if picam2:
                try:
                    picam2.stop()
                    picam2.close()
                except Exception:
                    pass

            # Restart stream if it was active
            if was_streaming and camera_streamer:
                print("Restarting camera stream after autofocus error...")
                try:
                    camera_streamer.start_streaming()
                except Exception as restart_error:
                    print(f"Warning: Failed to restart stream: {restart_error}")

            raise camera_error

        finally:
            # Always restart stream if it was active
            if was_streaming and camera_streamer:
                print("Restarting camera stream after autofocus...")
                try:
                    camera_streamer.start_streaming()
                except Exception as restart_error:
                    print(f"Warning: Failed to restart stream: {restart_error}")

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Autofocus error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': traceback.format_exc()
        }), 500


@camera_bp.route('/calibrate', methods=['POST'])
def auto_calibrate():
    """
    Auto-calibrate camera settings (Phase 2.2)

    Based on TakePhoto.py:350-436 calibration logic.
    Runs autofocus and auto-exposure, then updates settings.

    Request JSON (optional):
        - apply_to: "preview", "capture", or "both" (default: "capture")

    Returns:
        JSON with:
        - success: bool
        - before: dict - settings before calibration
        - after: dict - settings after calibration
        - af_success: bool - whether autofocus succeeded
        - timestamp: float - calibration timestamp
    """
    try:
        # Import here to avoid issues if picamera2 not available
        try:
            from picamera2 import Picamera2
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'picamera2 not available'
            }), 500

        import time
        import csv
        from flask import current_app
        from mothbox_paths import CAMERA_SETTINGS_FILE, CONTROLS_FILE, WEBUI_SETTINGS_FILE

        # Parse request parameters (support both old and new format)
        request_data = request.json or {}

        # New format: apply_to = 'preview' | 'capture' | 'both'
        apply_to = request_data.get('apply_to')

        # Old format: update_capture=True, update_preview=True (backward compatibility)
        if apply_to is None:
            update_capture = request_data.get('update_capture', True)
            update_preview = request_data.get('update_preview', False)

            if update_capture and update_preview:
                apply_to = 'both'
            elif update_preview:
                apply_to = 'preview'
            else:
                apply_to = 'capture'

        if apply_to not in ['preview', 'capture', 'both']:
            return jsonify({
                'success': False,
                'error': "apply_to must be 'preview', 'capture', or 'both'"
            }), 400

        print(f"Auto-calibration requested via API (apply_to={apply_to})")

        # Release camera hardware if initialized (prevents resource conflict)
        camera_streamer = current_app.config.get('CAMERA_STREAMER')
        was_streaming = False
        if camera_streamer and camera_streamer.camera:
            print("Releasing camera hardware before calibration...")
            was_streaming = camera_streamer.streaming
            camera_streamer.release_camera()
            time.sleep(0.5)  # Let camera fully release

        # Read current settings for "before" snapshot
        # camera_settings.csv format: SETTING,VALUE,DETAILS (vertical key-value pairs)
        current_settings = {}
        settings_details = {}  # Preserve DETAILS column
        try:
            with open(CAMERA_SETTINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    setting = row['SETTING']
                    value = row['VALUE']
                    details = row.get('DETAILS', '')
                    current_settings[setting] = value
                    settings_details[setting] = details
        except Exception as e:
            print(f"Warning: Could not read current settings: {e}")

        before_snapshot = {
            'ExposureTime': current_settings.get('ExposureTime', 'unknown'),
            'AnalogueGain': current_settings.get('AnalogueGain', 'unknown'),
            'LensPosition': current_settings.get('LensPosition', 'unknown')
        }

        # Initialize camera for calibration
        picam2 = None
        try:
            # Try camera 0 first, fallback to camera 1
            try:
                picam2 = Picamera2(0)
            except Exception:
                picam2 = Picamera2(1)

            # Configure for calibration (higher res for accuracy)
            preview_config = picam2.create_preview_configuration(
                main={'size': (1920*2, 1080*2), 'format': 'BGR888'}  # BGR888 = true RGB order
            )
            picam2.configure(preview_config)

            # Start camera
            picam2.start()

            # Set initial lens position
            picam2.set_controls({"LensPosition": 7.0})

            # Let camera stabilize with auto-exposure
            time.sleep(1.0)

            # Capture initial exposure metadata
            for i in range(5):
                md = picam2.capture_metadata()
                print(f"Calibrating frame {i}: "
                      f"Exp={md.get('ExposureTime')}µs, "
                      f"Gain={md.get('AnalogueGain'):.2f}, "
                      f"Lens={md.get('LensPosition'):.2f}D")

            # Get stabilized exposure values
            md = picam2.capture_metadata()
            calib_exposure = md['ExposureTime']
            calib_gain = md['AnalogueGain']

            print(f"Auto-exposure calibrated: Exp={calib_exposure}µs, Gain={calib_gain:.2f}")

            # Run autofocus cycle
            print("Running autofocus cycle...")
            af_start = time.time()
            af_success = picam2.autofocus_cycle()
            af_duration = time.time() - af_start
            print(f"Autofocus completed in {af_duration:.2f}s: {'Success' if af_success else 'Failed'}")

            # Get final metadata
            md = picam2.capture_metadata()
            calib_lens_position = md['LensPosition']
            af_state_code = md.get('AfState', 0)
            af_state = ("Idle", "Scanning", "Success", "Fail")[af_state_code]

            print(f"Calibrated values: "
                  f"Exp={calib_exposure}µs, "
                  f"Gain={calib_gain:.2f}, "
                  f"Lens={calib_lens_position:.2f}D")

            # Stop camera
            picam2.stop()
            picam2.close()

            # Prepare calibrated settings
            calibrated_values = {
                'LensPosition': calib_lens_position,
                'ExposureTime': calib_exposure,
                'AnalogueGain': calib_gain
            }

            # Apply to requested targets
            if apply_to in ['capture', 'both']:
                # Update camera_settings.csv (vertical SETTING,VALUE,DETAILS format)
                print("Updating camera_settings.csv...")

                # Update with calibrated values
                current_settings['LensPosition'] = str(calib_lens_position)
                current_settings['ExposureTime'] = str(calib_exposure)
                current_settings['AnalogueGain'] = str(calib_gain)

                # Write back in vertical format
                with open(CAMERA_SETTINGS_FILE, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['SETTING', 'VALUE', 'DETAILS'])
                    for setting, value in current_settings.items():
                        details = settings_details.get(setting, '')
                        writer.writerow([setting, value, details])

                print("✓ Updated camera_settings.csv")

            if apply_to in ['preview', 'both']:
                # Update webui_settings.txt (just focus, not exposure for preview)
                print("Updating webui_settings.txt...")
                from mothbox_paths import get_control_values

                webui_settings = {}
                if WEBUI_SETTINGS_FILE.exists():
                    webui_settings = get_control_values(WEBUI_SETTINGS_FILE)

                # Update focus settings (exposure controlled by camera in preview)
                webui_settings['af_mode'] = '0'  # Manual mode
                # Note: We don't update exposure/gain for preview as it's handled by camera auto-exposure

                # Write back
                with open(WEBUI_SETTINGS_FILE, 'w') as f:
                    for key, value in webui_settings.items():
                        f.write(f"{key}={value}\n")

                print("✓ Updated webui_settings.txt")

            # Update LastCalibration timestamp in controls.txt
            print("Updating LastCalibration timestamp...")
            calibration_timestamp = time.time()

            try:
                # Read controls.txt
                controls_lines = []
                found_calibration = False
                if CONTROLS_FILE.exists():
                    with open(CONTROLS_FILE, 'r') as f:
                        for line in f:
                            if line.startswith('LastCalibration='):
                                controls_lines.append(f"LastCalibration={int(calibration_timestamp)}\n")
                                found_calibration = True
                            else:
                                controls_lines.append(line)

                # If LastCalibration not found, add it
                if not found_calibration:
                    controls_lines.append(f"LastCalibration={int(calibration_timestamp)}\n")

                # Write back
                with open(CONTROLS_FILE, 'w') as f:
                    f.writelines(controls_lines)

                print("✓ Updated LastCalibration timestamp")

            except Exception as timestamp_error:
                print(f"Warning: Could not update LastCalibration: {timestamp_error}")

            # Return results (use snake_case for consistency with test expectations)
            after_snapshot = {
                'exposure_time': calib_exposure,
                'analogue_gain': round(calib_gain, 2),
                'lens_position': round(calib_lens_position, 2),
                # Also include PascalCase for backward compatibility
                'ExposureTime': calib_exposure,
                'AnalogueGain': round(calib_gain, 2),
                'LensPosition': round(calib_lens_position, 2)
            }

            return jsonify({
                'success': True,
                'before': before_snapshot,
                'after': after_snapshot,
                'af_success': af_success,
                'af_state': af_state,
                'af_duration_seconds': round(af_duration, 2),
                'apply_to': apply_to,
                'timestamp': calibration_timestamp,
                'message': f'Calibration {"succeeded" if af_success else "completed with AF failure"}'
            })

        except Exception as camera_error:
            # Ensure camera is closed on error
            if picam2:
                try:
                    picam2.stop()
                    picam2.close()
                except Exception:
                    pass

            # Restart stream if it was active
            if was_streaming and camera_streamer:
                print("Restarting camera stream after calibration error...")
                try:
                    camera_streamer.start_streaming()
                except Exception as restart_error:
                    print(f"Warning: Failed to restart stream: {restart_error}")

            raise camera_error

        finally:
            # Always restart stream if it was active
            if was_streaming and camera_streamer:
                print("Restarting camera stream after calibration...")
                try:
                    camera_streamer.start_streaming()
                except Exception as restart_error:
                    print(f"Warning: Failed to restart stream: {restart_error}")

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Calibration error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': traceback.format_exc()
        }), 500


@camera_bp.route('/freeze-settings', methods=['POST'])
def freeze_settings():
    """
    Freeze camera settings to current values (Phase 2.2 - Task 2)

    Locks exposure, gain, and focus to prevent automatic adjustments.
    Useful for reproducible captures under consistent conditions.

    Returns:
        JSON with:
        - success: bool
        - frozen_settings: dict - values that were locked
        - message: str
    """
    try:
        from picamera2 import Picamera2
        from mothbox_paths import CAMERA_SETTINGS_FILE
        import csv
        import time

        # Release streaming camera if active
        from flask import current_app
        if hasattr(current_app, 'camera_streamer') and current_app.camera_streamer.streaming:
            current_app.camera_streamer.stop_stream()
            time.sleep(0.5)

        # Initialize camera to get current metadata
        picam2 = Picamera2()
        preview_config = picam2.create_preview_configuration(
            main={'size': (1920, 1080), 'format': 'RGB888'}
        )
        picam2.configure(preview_config)
        picam2.start()

        # Let camera stabilize
        time.sleep(0.5)

        # Capture current metadata
        md = picam2.capture_metadata()

        current_exposure = md.get('ExposureTime', 0)
        current_gain = md.get('AnalogueGain', 1.0)
        current_lens_position = md.get('LensPosition', 0.0)

        picam2.stop()
        picam2.close()

        # Read current settings
        current_settings = {}
        settings_details = {}

        with open(CAMERA_SETTINGS_FILE, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                setting = row.get('SETTING', '').strip()
                value = row.get('VALUE', '').strip()
                details = row.get('DETAILS', '').strip()
                if setting:
                    current_settings[setting] = value
                    settings_details[setting] = details

        # Update with frozen values and disable auto modes
        current_settings['AeEnable'] = 'False'  # Disable auto-exposure
        current_settings['AwbEnable'] = 'False'  # Disable auto white balance
        current_settings['AfMode'] = '0'  # Set to manual focus
        current_settings['ExposureTime'] = str(int(current_exposure))
        current_settings['AnalogueGain'] = str(round(current_gain, 2))
        current_settings['LensPosition'] = str(round(current_lens_position, 2))

        # Write back to CSV
        fieldnames = ['SETTING', 'VALUE', 'DETAILS']
        with open(CAMERA_SETTINGS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(fieldnames)
            for setting, value in current_settings.items():
                details = settings_details.get(setting, '')
                writer.writerow([setting, value, details])

        # Restart streaming camera
        if hasattr(current_app, 'camera_streamer'):
            current_app.camera_streamer.start_stream()

        frozen_values = {
            'ExposureTime': int(current_exposure),
            'AnalogueGain': round(current_gain, 2),
            'LensPosition': round(current_lens_position, 2),
            'AeEnable': False,
            'AwbEnable': False,
            'AfMode': 0
        }

        return jsonify({
            'success': True,
            'frozen_settings': frozen_values,
            'message': f'Settings frozen at Exp={int(current_exposure)}µs, Gain={round(current_gain, 2)}, Focus={round(current_lens_position, 2)}D',
            'timestamp': time.time()
        })

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@camera_bp.route('/test-capture', methods=['POST'])
def test_capture():
    """
    Capture a test photo using current preview settings (Phase 4.5)

    Allows testing camera settings without modifying camera_settings.csv.
    Uses webui_settings.txt controls for full-resolution capture.

    Returns:
        JSON with:
        - success: bool
        - test_photo_path: str (relative path from PHOTOS_DIR)
        - settings_used: dict (controls that were applied)
        - metadata: dict (exposure, gain, lens position, color temp)
        - timestamp: float
    """
    try:
        # Import here to avoid issues if picamera2 not available
        try:
            from picamera2 import Picamera2
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'picamera2 not available'
            }), 500

        from mothbox_paths import WEBUI_SETTINGS_FILE, PHOTOS_DIR, get_control_values
        from datetime import datetime
        from flask import current_app
        import time

        print("Test capture requested via API")

        # Load preview settings
        preview_settings = {}
        if WEBUI_SETTINGS_FILE.exists():
            preview_settings = get_control_values(WEBUI_SETTINGS_FILE)

        # Release camera hardware if initialized (prevents resource conflict)
        camera_streamer = current_app.config.get('CAMERA_STREAMER')
        was_streaming = False
        if camera_streamer and camera_streamer.camera:
            print("Releasing camera hardware before test capture...")
            was_streaming = camera_streamer.streaming
            camera_streamer.release_camera()
            time.sleep(0.5)  # Let camera fully release

        # Initialize camera for test capture
        picam2 = None
        try:
            # Try camera 0 first, fallback to camera 1
            try:
                picam2 = Picamera2(0)
            except Exception:
                picam2 = Picamera2(1)

            # Configure for full-resolution capture
            # Use maximum resolution for test captures
            capture_config = picam2.create_still_configuration(
                main={"size": (9152, 6944), "format": "BGR888"}  # Full 64MP, BGR888 = true RGB order
            )
            picam2.configure(capture_config)

            # Start camera
            picam2.start()

            # Apply preview controls to full-res capture
            controls = {
                'Sharpness': float(preview_settings.get('sharpness', 1.0)),
                'Brightness': float(preview_settings.get('brightness', 0.0)),
                'Contrast': float(preview_settings.get('contrast', 1.0)),
                'Saturation': float(preview_settings.get('saturation', 1.0)),
                'AfMode': int(preview_settings.get('af_mode', 2)),
                'AfSpeed': int(preview_settings.get('af_speed', 0)),
                'AfRange': int(preview_settings.get('af_range', 0)),
                'AwbEnable': preview_settings.get('awb_enable', 'true').lower() == 'true',
            }

            # Only set AwbMode if AWB is disabled
            if not controls['AwbEnable']:
                controls['AwbMode'] = int(preview_settings.get('awb_mode', 0))

            picam2.set_controls(controls)
            print(f"Applied preview controls to test capture: {controls}")

            # Wait for settings to stabilize
            time.sleep(0.5)

            # Create test_captures directory
            test_dir = PHOTOS_DIR / "test_captures"
            test_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_capture_{timestamp}.jpg"
            filepath = test_dir / filename

            # Capture photo
            print(f"Capturing test photo to: {filepath}")
            picam2.capture_file(str(filepath))

            # Get metadata for reference
            md = picam2.capture_metadata()

            # Stop camera
            picam2.stop()
            picam2.close()

            # Return relative path from PHOTOS_DIR
            relative_path = str(filepath.relative_to(PHOTOS_DIR))

            return jsonify({
                'success': True,
                'test_photo_path': relative_path,
                'settings_used': controls,
                'metadata': {
                    'exposure_time': md.get('ExposureTime', 0),
                    'analogue_gain': round(md.get('AnalogueGain', 0.0), 2),
                    'lens_position': round(md.get('LensPosition', 0.0), 2),
                    'colour_temperature': md.get('ColourTemperature', 0)
                },
                'timestamp': time.time(),
                'message': f'Test capture saved to {relative_path}'
            })

        except Exception as camera_error:
            # Ensure camera is closed on error
            if picam2:
                try:
                    picam2.stop()
                    picam2.close()
                except Exception:
                    pass

            # Restart stream if it was active
            if was_streaming and camera_streamer:
                print("Restarting camera stream after test capture error...")
                try:
                    camera_streamer.start_streaming()
                except Exception as restart_error:
                    print(f"Warning: Failed to restart stream: {restart_error}")

            raise camera_error

        finally:
            # Always restart stream if it was active
            if was_streaming and camera_streamer:
                print("Restarting camera stream after test capture...")
                try:
                    camera_streamer.start_streaming()
                except Exception as restart_error:
                    print(f"Warning: Failed to restart stream: {restart_error}")

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Test capture error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': traceback.format_exc()
        }), 500
