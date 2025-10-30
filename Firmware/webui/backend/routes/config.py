"""Configuration management endpoints"""
from flask import Blueprint, jsonify, request
import csv
import shutil
from datetime import datetime
from pathlib import Path
import sys

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import (
    CAMERA_SETTINGS_FILE,
    SCHEDULE_SETTINGS_FILE,
    CONTROLS_FILE,
    LIVEVIEW_SETTINGS_FILE,
    get_control_values
)

# Import camera control mapping
from camera_control_mapping import SNAKE_TO_PASCAL, convert_to_settings_file

# Import shared utilities
from utils import sanitize_csv_value, ALLOWED_CAMERA_SETTINGS, create_backup

# Valid BCM GPIO pins (BCM mode: GPIO 2-27)
VALID_BCM_GPIO_PINS = [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27]

config_bp = Blueprint('config', __name__)

# Whitelist of allowed controls.txt keys with validation functions
ALLOWED_CONTROLS = {
    'shutdown_enabled': lambda v: str(v).lower() in ['true', 'false'],
    'OnlyFlash': lambda v: str(v).lower() in ['true', 'false'],
    'LastCalibration': lambda v: str(v).replace('-', '').isdigit(),  # Allow negative numbers
    'nextWake': lambda v: str(v).replace('-', '').isdigit(),
    'name': lambda v: len(str(v)) <= 100 and '\n' not in str(v) and '\r' not in str(v),
    'softwareversion': lambda v: len(str(v)) <= 20 and '\n' not in str(v),
    'gpstime': lambda v: str(v).replace('-', '').replace('.', '').isdigit() or str(v) == '0',
    'UTCoff': lambda v: str(v).lstrip('-').isdigit() and -12 <= int(v) <= 14,
    'lat': lambda v: len(str(v)) <= 50 and '\n' not in str(v),
    'lon': lambda v: len(str(v)) <= 50 and '\n' not in str(v),
    'weekdays': lambda v: all(c in '0123456789;' for c in str(v)),
    'hours': lambda v: all(c in '0123456789;' for c in str(v)),
    'minutes': lambda v: str(v).isdigit() or all(c in '0123456789;' for c in str(v)),
    'runtime': lambda v: str(v).isdigit(),
    'Relay_Ch1': lambda v: str(v).isdigit() and int(v) in VALID_BCM_GPIO_PINS,
    'Relay_Ch2': lambda v: str(v).isdigit() and int(v) in VALID_BCM_GPIO_PINS,
    'Relay_Ch3': lambda v: str(v).isdigit() and int(v) in VALID_BCM_GPIO_PINS,
    'relay_enabled': lambda v: str(v).lower() in ['true', 'false'],
    'flash_duration_ms': lambda v: str(v).isdigit() and 50 <= int(v) <= 5000,  # 50ms to 5s flash duration
    'jpeg_quality': lambda v: str(v).isdigit() and 50 <= int(v) <= 100,  # JPEG quality 50-100
}

@config_bp.route('/controls', methods=['GET'])
def get_controls():
    """Get controls.txt configuration"""
    try:
        controls = get_control_values(CONTROLS_FILE)
        return jsonify(controls)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_bp.route('/controls', methods=['POST'])
def update_controls():
    """Update controls.txt configuration (with backup)"""
    backup_path = None
    try:
        new_controls = request.json

        if not isinstance(new_controls, dict):
            return jsonify({'error': 'Invalid request format'}), 400

        # Validate all keys are allowed
        invalid_keys = set(new_controls.keys()) - set(ALLOWED_CONTROLS.keys())
        if invalid_keys:
            return jsonify({'error': f'Invalid keys: {", ".join(invalid_keys)}'}), 400

        # Validate all values
        for key, value in new_controls.items():
            try:
                if not ALLOWED_CONTROLS[key](value):
                    return jsonify({'error': f'Invalid value for {key}: {value}'}), 400
            except (ValueError, TypeError) as e:
                return jsonify({'error': f'Invalid value for {key}: {value}'}), 400

        # Sanitize values - remove newlines and carriage returns
        sanitized = {
            k: str(v).replace('\n', '').replace('\r', '')
            for k, v in new_controls.items()
        }

        # Create backup before modification
        backup_path = create_backup(CONTROLS_FILE)

        # Write new configuration
        with open(CONTROLS_FILE, 'w') as f:
            for key, value in sanitized.items():
                f.write(f"{key}={value}\n")

        return jsonify({'success': True})
    except Exception as e:
        # Restore backup if write failed
        if backup_path and backup_path.exists():
            try:
                shutil.copy2(backup_path, CONTROLS_FILE)
                print(f"Restored backup from {backup_path} after error")
            except Exception as restore_error:
                print(f"Failed to restore backup: {restore_error}")
        return jsonify({'error': str(e)}), 500

@config_bp.route('/schedule', methods=['GET'])
def get_schedule_settings():
    """Get schedule settings from CSV"""
    try:
        settings = {}
        with open(SCHEDULE_SETTINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                settings = row
                break

        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@config_bp.route('/schedule', methods=['POST'])
def update_schedule_settings():
    """Update schedule settings (with backup)"""
    backup_path = None
    try:
        new_settings = request.json

        if not isinstance(new_settings, dict):
            return jsonify({'error': 'Invalid request format'}), 400

        # Read existing headers
        with open(SCHEDULE_SETTINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        # Validate that all keys match existing fieldnames
        invalid_keys = set(new_settings.keys()) - set(fieldnames)
        if invalid_keys:
            return jsonify({'error': f'Invalid keys: {", ".join(invalid_keys)}'}), 400

        # Sanitize all values to prevent CSV injection
        sanitized_settings = {
            k: sanitize_csv_value(v)
            for k, v in new_settings.items()
        }

        # Create backup before modification
        backup_path = create_backup(SCHEDULE_SETTINGS_FILE)

        # Write updated settings
        with open(SCHEDULE_SETTINGS_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(sanitized_settings)

        return jsonify({'success': True})
    except Exception as e:
        # Restore backup if write failed
        if backup_path and backup_path.exists():
            try:
                shutil.copy2(backup_path, SCHEDULE_SETTINGS_FILE)
                print(f"Restored backup from {backup_path} after error")
            except Exception as restore_error:
                print(f"Failed to restore backup: {restore_error}")
        return jsonify({'error': str(e)}), 500

@config_bp.route('/webui', methods=['GET'])
def get_webui_settings():
    """Get WebUI stream settings"""
    try:
        # Default settings
        defaults = {
            # Stream/encoding settings
            'stream_width': 1024,
            'stream_height': 768,
            'frame_rate': 10,
            'jpeg_quality': 85,  # Optimized default: faster encoding, good quality
            'stream_mode': 'simplejpeg',  # Fast software encoding (5-7x faster than PIL)
            'sensor_mode': 'auto',  # auto, 4:3, 16:9, full - controls field of view

            # Image quality controls
            'sharpness': 1.0,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,

            # Noise reduction control
            'noise_reduction_mode': 0,  # 0=Off, 1=Fast, 2=High Quality

            # Focus controls
            'af_mode': 2,  # Continuous autofocus
            'af_speed': 0,  # Normal speed
            'af_range': 0,  # Normal range

            # White balance controls
            'awb_enable': True,
            'awb_mode': 0,  # Auto

            # Colour gains - fix for blue/white saturation under LED illumination
            # These values from TakePhoto.py calibration lock color balance under LED flash
            'colour_gains_red': 2.259,
            'colour_gains_blue': 1.500,

            # Exposure controls (exposure-metering feature)
            'ae_metering_mode': 0,      # 0=Centre-Weighted, 1=Spot, 2=Matrix
            'ae_enable': True,           # True=Auto, False=Manual
            'exposure_time': 500,        # Microseconds (100-200000)
            'analogue_gain': 8.0,        # ISO gain (1.0-16.0)

            # Focus peaking controls (preview-only overlay)
            'focus_peaking_enabled': False,
            'focus_peaking_intensity': 100,     # 50-200 range
            'focus_peaking_colour': 'green',     # green, red, yellow, cyan, magenta
            'focus_peaking_algorithm': 'laplacian',  # laplacian, sobel, canny
        }

        # Load from file if it exists
        if LIVEVIEW_SETTINGS_FILE.exists():
            settings = get_control_values(LIVEVIEW_SETTINGS_FILE)
            # Load settings from file, converting to appropriate types
            for key in defaults:
                if key in settings:
                    if key in ['stream_mode', 'focus_peaking_colour', 'focus_peaking_algorithm', 'sensor_mode']:
                        # String values - don't convert
                        defaults[key] = settings[key]
                    elif key in ['awb_enable', 'ae_enable', 'focus_peaking_enabled']:
                        # Boolean values
                        defaults[key] = settings[key].lower() == 'true'
                    elif key in ['sharpness', 'brightness', 'contrast', 'saturation',
                                'colour_gains_red', 'colour_gains_blue', 'analogue_gain']:
                        # Float values
                        try:
                            defaults[key] = float(settings[key])
                        except ValueError:
                            pass  # Keep default if conversion fails
                    elif key in ['noise_reduction_mode', 'ae_metering_mode', 'exposure_time', 'focus_peaking_intensity']:
                        # Integer values (noise_reduction_mode: 0-2, ae_metering_mode: 0-2, exposure_time: microseconds, focus_peaking_intensity: 50-200)
                        try:
                            defaults[key] = int(settings[key])
                        except ValueError:
                            pass  # Keep default if conversion fails
                    else:
                        # Other integer values
                        try:
                            defaults[key] = int(settings[key])
                        except ValueError:
                            pass  # Keep default if conversion fails

        return jsonify(defaults)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_bp.route('/webui', methods=['POST'])
def update_webui_settings():
    """Update WebUI stream settings (with backup)"""
    backup_path = None
    try:
        new_settings = request.json

        # Load existing settings to merge with updates (preserves unmodified values)
        existing = {}
        if LIVEVIEW_SETTINGS_FILE.exists():
            existing = get_control_values(LIVEVIEW_SETTINGS_FILE)

        # Validate and convert types - Stream/encoding settings
        try:
            stream_width = int(new_settings.get('stream_width', existing.get('stream_width', 1024)))
            stream_height = int(new_settings.get('stream_height', existing.get('stream_height', 768)))
            frame_rate = int(new_settings.get('frame_rate', existing.get('frame_rate', 10)))
            jpeg_quality = int(new_settings.get('jpeg_quality', existing.get('jpeg_quality', 85)))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid stream setting type: {e}'}), 400

        stream_mode = new_settings.get('stream_mode', existing.get('stream_mode', 'simplejpeg'))
        sensor_mode = new_settings.get('sensor_mode', existing.get('sensor_mode', 'auto'))

        if not isinstance(sensor_mode, str):
            return jsonify({'error': 'sensor_mode must be a string'}), 400

        # Validate and convert types - Image quality controls
        try:
            sharpness = float(new_settings.get('sharpness', existing.get('sharpness', 1.0)))
            brightness = float(new_settings.get('brightness', existing.get('brightness', 0.0)))
            contrast = float(new_settings.get('contrast', existing.get('contrast', 1.0)))
            saturation = float(new_settings.get('saturation', existing.get('saturation', 1.0)))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid image quality setting type: {e}'}), 400

        # Validate and convert types - Noise reduction control
        try:
            noise_reduction_mode = new_settings.get('noise_reduction_mode', existing.get('noise_reduction_mode', 0))
            # Ensure it's an integer (reject floats)
            if isinstance(noise_reduction_mode, float) and not noise_reduction_mode.is_integer():
                return jsonify({'error': 'noise_reduction_mode must be an integer (0, 1, or 2)'}), 400
            noise_reduction_mode = int(noise_reduction_mode)
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid noise_reduction_mode type: {e}'}), 400

        # Validate and convert types - Focus controls
        try:
            af_mode = int(new_settings.get('af_mode', existing.get('af_mode', 2)))
            af_speed = int(new_settings.get('af_speed', existing.get('af_speed', 0)))
            af_range = int(new_settings.get('af_range', existing.get('af_range', 0)))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid focus control type: {e}'}), 400

        # Validate and convert types - White balance controls
        awb_enable = new_settings.get('awb_enable', existing.get('awb_enable', 'true'))
        if isinstance(awb_enable, str):
            awb_enable = awb_enable.lower() == 'true'

        try:
            awb_mode = int(new_settings.get('awb_mode', existing.get('awb_mode', 0)))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid white balance mode type: {e}'}), 400

        # Validate and convert types - Colour gains (blue/white saturation fix)
        try:
            colour_gains_red = float(new_settings.get('colour_gains_red', existing.get('colour_gains_red', 2.259)))
            colour_gains_blue = float(new_settings.get('colour_gains_blue', existing.get('colour_gains_blue', 1.500)))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid colour gains type: {e}'}), 400

        # Validate and convert types - Exposure controls (exposure-metering feature)
        try:
            ae_metering_mode = new_settings.get('ae_metering_mode', existing.get('ae_metering_mode', 0))
            if isinstance(ae_metering_mode, float) and not ae_metering_mode.is_integer():
                return jsonify({'error': 'ae_metering_mode must be an integer (0, 1, or 2)'}), 400
            ae_metering_mode = int(ae_metering_mode)
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid ae_metering_mode type: {e}'}), 400

        ae_enable = new_settings.get('ae_enable', existing.get('ae_enable', True))
        if isinstance(ae_enable, str):
            ae_enable = ae_enable.lower() == 'true'

        try:
            exposure_time = int(new_settings.get('exposure_time', existing.get('exposure_time', 500)))
            analogue_gain = float(new_settings.get('analogue_gain', existing.get('analogue_gain', 8.0)))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid exposure settings type: {e}'}), 400

        # Validate and convert types - ISP tuning controls
        use_custom_tuning = new_settings.get('use_custom_tuning', existing.get('use_custom_tuning', False))
        if isinstance(use_custom_tuning, str):
            use_custom_tuning = use_custom_tuning.lower() == 'true'

        lens_shading_enable = new_settings.get('lens_shading_enable', existing.get('lens_shading_enable', True))
        if isinstance(lens_shading_enable, str):
            lens_shading_enable = lens_shading_enable.lower() == 'true'

        defect_correction_enable = new_settings.get('defect_correction_enable', existing.get('defect_correction_enable', True))
        if isinstance(defect_correction_enable, str):
            defect_correction_enable = defect_correction_enable.lower() == 'true'

        # Validate and convert types - Focus peaking controls (preview-only overlay)
        focus_peaking_enabled = new_settings.get('focus_peaking_enabled', existing.get('focus_peaking_enabled', False))
        if isinstance(focus_peaking_enabled, str):
            focus_peaking_enabled = focus_peaking_enabled.lower() == 'true'

        try:
            focus_peaking_intensity = int(new_settings.get('focus_peaking_intensity', existing.get('focus_peaking_intensity', 100)))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid focus_peaking_intensity type: {e}'}), 400

        focus_peaking_colour = new_settings.get('focus_peaking_colour', existing.get('focus_peaking_colour', 'green'))
        if not isinstance(focus_peaking_colour, str):
            return jsonify({'error': 'focus_peaking_colour must be a string'}), 400

        focus_peaking_algorithm = new_settings.get('focus_peaking_algorithm', existing.get('focus_peaking_algorithm', 'laplacian'))
        if not isinstance(focus_peaking_algorithm, str):
            return jsonify({'error': 'focus_peaking_algorithm must be a string'}), 400

        # Validate ranges - Stream/encoding
        if not (320 <= stream_width <= 1920):
            return jsonify({'error': 'Width must be between 320 and 1920'}), 400
        if not (240 <= stream_height <= 1080):
            return jsonify({'error': 'Height must be between 240 and 1080'}), 400
        if not (1 <= frame_rate <= 30):
            return jsonify({'error': 'Frame rate must be between 1 and 30'}), 400
        if not (50 <= jpeg_quality <= 100):
            return jsonify({'error': 'JPEG quality must be between 50 and 100'}), 400
        if stream_mode not in ['simplejpeg', 'mjpeg_hardware']:
            return jsonify({'error': 'stream_mode must be simplejpeg or mjpeg_hardware'}), 400
        if sensor_mode not in ['auto', '4:3', '16:9', 'full']:
            return jsonify({'error': 'sensor_mode must be auto, 4:3, 16:9, or full'}), 400

        # Validate ranges - Image quality
        # Using picamera2 typical ranges (0.0-4.0) for safety and hardware compatibility
        if not (0.0 <= sharpness <= 4.0):
            return jsonify({'error': 'Sharpness must be between 0.0 and 4.0'}), 400
        if not (-1.0 <= brightness <= 1.0):
            return jsonify({'error': 'Brightness must be between -1.0 and 1.0'}), 400
        if not (0.0 <= contrast <= 4.0):
            return jsonify({'error': 'Contrast must be between 0.0 and 4.0'}), 400
        if not (0.0 <= saturation <= 4.0):
            return jsonify({'error': 'Saturation must be between 0.0 and 4.0'}), 400

        # Validate ranges - Noise reduction
        if noise_reduction_mode not in [0, 1, 2]:
            return jsonify({'error': 'noise_reduction_mode must be 0 (Off), 1 (Fast), or 2 (High Quality)'}), 400

        # Validate ranges - Focus controls
        if af_mode not in [0, 1, 2]:
            return jsonify({'error': 'AfMode must be 0 (Manual), 1 (Auto Single), or 2 (Continuous)'}), 400
        if af_speed not in [0, 1]:
            return jsonify({'error': 'AfSpeed must be 0 (Normal) or 1 (Fast)'}), 400
        if af_range not in [0, 1, 2]:
            return jsonify({'error': 'AfRange must be 0 (Normal), 1 (Macro), or 2 (Full)'}), 400

        # Validate ranges - White balance
        if not isinstance(awb_enable, bool):
            return jsonify({'error': 'AwbEnable must be a boolean'}), 400
        if not (0 <= awb_mode <= 7):
            return jsonify({'error': 'AwbMode must be between 0 and 7'}), 400

        # Validate ranges - Colour gains
        if not (0.0 <= colour_gains_red <= 8.0):
            return jsonify({'error': 'Red colour gain must be between 0.0 and 8.0'}), 400
        if not (0.0 <= colour_gains_blue <= 8.0):
            return jsonify({'error': 'Blue colour gain must be between 0.0 and 8.0'}), 400

        # Validate ranges - Exposure controls (exposure-metering feature)
        if ae_metering_mode not in [0, 1, 2]:
            return jsonify({'error': 'ae_metering_mode must be 0 (Centre-Weighted), 1 (Spot), or 2 (Matrix)'}), 400
        if not isinstance(ae_enable, bool):
            return jsonify({'error': 'ae_enable must be a boolean'}), 400
        if not (100 <= exposure_time <= 200000):
            return jsonify({'error': 'exposure_time must be between 100 and 200000 microseconds'}), 400
        if not (1.0 <= analogue_gain <= 16.0):
            return jsonify({'error': 'analogue_gain must be between 1.0 and 16.0'}), 400

        # Validate - ISP tuning controls
        if not isinstance(use_custom_tuning, bool):
            return jsonify({'error': 'use_custom_tuning must be a boolean'}), 400
        if not isinstance(lens_shading_enable, bool):
            return jsonify({'error': 'lens_shading_enable must be a boolean'}), 400
        if not isinstance(defect_correction_enable, bool):
            return jsonify({'error': 'defect_correction_enable must be a boolean'}), 400

        # Validate - Focus peaking controls
        if not isinstance(focus_peaking_enabled, bool):
            return jsonify({'error': 'focus_peaking_enabled must be a boolean'}), 400
        if not (50 <= focus_peaking_intensity <= 200):
            return jsonify({'error': 'focus_peaking_intensity must be between 50 and 200'}), 400
        if focus_peaking_colour not in ['green', 'red', 'yellow', 'cyan', 'magenta']:
            return jsonify({'error': 'focus_peaking_colour must be green, red, yellow, cyan, or magenta'}), 400
        if focus_peaking_algorithm not in ['laplacian', 'sobel', 'canny']:
            return jsonify({'error': 'focus_peaking_algorithm must be laplacian, sobel, or canny'}), 400

        # Create backup before modification
        backup_path = create_backup(LIVEVIEW_SETTINGS_FILE)

        # Write settings to file
        with open(LIVEVIEW_SETTINGS_FILE, 'w') as f:
            # Stream/encoding settings
            f.write(f"stream_width={stream_width}\n")
            f.write(f"stream_height={stream_height}\n")
            f.write(f"frame_rate={frame_rate}\n")
            f.write(f"jpeg_quality={jpeg_quality}\n")
            f.write(f"stream_mode={stream_mode}\n")
            f.write(f"sensor_mode={sensor_mode}\n")

            # Image quality controls
            f.write(f"sharpness={sharpness}\n")
            f.write(f"brightness={brightness}\n")
            f.write(f"contrast={contrast}\n")
            f.write(f"saturation={saturation}\n")

            # Noise reduction control
            f.write(f"noise_reduction_mode={noise_reduction_mode}\n")

            # Focus controls
            f.write(f"af_mode={af_mode}\n")
            f.write(f"af_speed={af_speed}\n")
            f.write(f"af_range={af_range}\n")

            # White balance controls
            f.write(f"awb_enable={'true' if awb_enable else 'false'}\n")
            f.write(f"awb_mode={awb_mode}\n")

            # Colour gains - fix for blue/white saturation under LED illumination
            f.write(f"colour_gains_red={colour_gains_red}\n")
            f.write(f"colour_gains_blue={colour_gains_blue}\n")

            # Exposure controls (exposure-metering feature)
            f.write(f"ae_metering_mode={ae_metering_mode}\n")
            f.write(f"ae_enable={'true' if ae_enable else 'false'}\n")
            f.write(f"exposure_time={exposure_time}\n")
            f.write(f"analogue_gain={analogue_gain}\n")

            # ISP tuning controls
            f.write(f"use_custom_tuning={'true' if use_custom_tuning else 'false'}\n")
            f.write(f"lens_shading_enable={'true' if lens_shading_enable else 'false'}\n")
            f.write(f"defect_correction_enable={'true' if defect_correction_enable else 'false'}\n")

            # Focus peaking controls (preview-only overlay)
            f.write(f"focus_peaking_enabled={'true' if focus_peaking_enabled else 'false'}\n")
            f.write(f"focus_peaking_intensity={focus_peaking_intensity}\n")
            f.write(f"focus_peaking_colour={focus_peaking_colour}\n")
            f.write(f"focus_peaking_algorithm={focus_peaking_algorithm}\n")

        return jsonify({'success': True})
    except Exception as e:
        # Restore backup if write failed
        if backup_path and backup_path.exists():
            try:
                shutil.copy2(backup_path, LIVEVIEW_SETTINGS_FILE)
                print(f"Restored backup from {backup_path} after error")
            except Exception as restore_error:
                print(f"Failed to restore backup: {restore_error}")
        return jsonify({'error': str(e)}), 500


@config_bp.route('/copy-settings', methods=['POST'])
def copy_settings():
    """
    Copy compatible settings between live view and capture systems

    Request JSON:
        - direction: "preview_to_capture" or "capture_to_preview"

    Returns:
        JSON with:
        - success: bool
        - copied: list of setting names that were copied
        - skipped: list of setting names that were incompatible/not copied
    """
    try:
        request_data = request.json or {}
        direction = request_data.get('direction')

        if direction not in ['preview_to_capture', 'capture_to_preview']:
            return jsonify({
                'error': 'direction must be "preview_to_capture" or "capture_to_preview"'
            }), 400

        print(f"Copy settings requested: {direction}")

        # Use centralized mapping from camera_control_mapping.py
        # This eliminates local duplicate mapping table

        # Define compatible controls to copy between systems
        # Format: (preview_name, capture_name, converter_func)
        compatible_keys = ['sharpness', 'brightness', 'contrast', 'saturation',
                          'af_mode', 'af_speed', 'af_range', 'awb_enable', 'awb_mode']

        # Generate mappings from centralized source
        compatible_mappings = [
            (snake, SNAKE_TO_PASCAL[snake], lambda v, k=snake: convert_to_settings_file(k, v))
            for snake in compatible_keys
        ]

        copied = []
        skipped = []

        if direction == 'preview_to_capture':
            # Read live view settings
            from mothbox_paths import get_control_values
            if not LIVEVIEW_SETTINGS_FILE.exists():
                return jsonify({
                    'success': False,
                    'error': 'webui_settings.txt not found'
                }), 404

            preview_settings = get_control_values(LIVEVIEW_SETTINGS_FILE)

            # Read current capture settings (row-based CSV format)
            # Format: SETTING,VALUE,DETAILS
            import csv
            csv_rows = []
            capture_settings_dict = {}

            with open(CAMERA_SETTINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Store original rows for writing back
                    csv_rows.append(dict(row))
                    # Build settings dict like TakePhoto.py does
                    setting_name = row['SETTING'].strip()
                    setting_value = row['VALUE'].strip()
                    capture_settings_dict[setting_name] = setting_value

            # Copy compatible settings
            for preview_key, capture_key, converter in compatible_mappings:
                if preview_key in preview_settings:
                    try:
                        # Convert live view value to capture format
                        preview_value = preview_settings[preview_key]

                        # Type conversion for live view settings
                        if preview_key in ['sharpness', 'brightness', 'contrast', 'saturation']:
                            preview_value = float(preview_value)
                        elif preview_key in ['af_mode', 'af_speed', 'af_range', 'awb_mode']:
                            preview_value = int(preview_value)
                        elif preview_key == 'awb_enable':
                            preview_value = preview_value.lower() == 'true'

                        # Convert to capture format
                        capture_value = converter(preview_value)

                        # Validate using capture validator
                        if capture_key in ALLOWED_CAMERA_SETTINGS:
                            if ALLOWED_CAMERA_SETTINGS[capture_key](capture_value):
                                # Update the settings dict
                                capture_settings_dict[capture_key] = capture_value

                                # Update the corresponding row
                                for row in csv_rows:
                                    if row['SETTING'] == capture_key:
                                        row['VALUE'] = str(capture_value)
                                        break

                                copied.append(f"{preview_key} → {capture_key}")
                            else:
                                skipped.append(f"{preview_key} (validation failed)")
                        else:
                            skipped.append(f"{preview_key} (no capture validator)")

                    except Exception as e:
                        skipped.append(f"{preview_key} (error: {str(e)})")
                else:
                    skipped.append(f"{preview_key} (not set in live view)")

            # Write updated capture settings back in row format
            with open(CAMERA_SETTINGS_FILE, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['SETTING', 'VALUE', 'DETAILS'])
                writer.writeheader()
                writer.writerows(csv_rows)

            print(f"Copied {len(copied)} settings to capture: {copied}")

        elif direction == 'capture_to_preview':
            # Read capture settings (row-based CSV format)
            # Format: SETTING,VALUE,DETAILS
            import csv
            capture_settings_dict = {}
            with open(CAMERA_SETTINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Build settings dict like TakePhoto.py does
                    setting_name = row['SETTING'].strip()
                    setting_value = row['VALUE'].strip()
                    capture_settings_dict[setting_name] = setting_value

            # Read current live view settings
            from mothbox_paths import get_control_values
            preview_settings = {}
            if LIVEVIEW_SETTINGS_FILE.exists():
                preview_settings = get_control_values(LIVEVIEW_SETTINGS_FILE)
            else:
                # Start with defaults from get_webui_settings
                response = get_webui_settings()
                preview_settings = response.get_json()

            # Copy compatible settings
            for preview_key, capture_key, converter in compatible_mappings:
                if capture_key in capture_settings_dict:
                    try:
                        capture_value = capture_settings_dict[capture_key]

                        # Convert to live view type
                        if preview_key in ['sharpness', 'brightness', 'contrast', 'saturation']:
                            preview_value = float(capture_value)
                        elif preview_key in ['af_mode', 'af_speed', 'af_range', 'awb_mode']:
                            preview_value = int(capture_value)
                        elif preview_key == 'awb_enable':
                            preview_value = capture_value.lower() == 'true'
                        else:
                            preview_value = capture_value

                        # Validate ranges (basic validation)
                        valid = True
                        if preview_key == 'sharpness' and not (0.0 <= preview_value <= 16.0):
                            valid = False
                        elif preview_key == 'brightness' and not (-1.0 <= preview_value <= 1.0):
                            valid = False
                        elif preview_key in ['contrast', 'saturation'] and not (0.0 <= preview_value <= 32.0):
                            valid = False
                        elif preview_key == 'af_mode' and preview_value not in [0, 1, 2]:
                            valid = False
                        elif preview_key == 'af_speed' and preview_value not in [0, 1]:
                            valid = False
                        elif preview_key == 'af_range' and preview_value not in [0, 1, 2]:
                            valid = False
                        elif preview_key == 'awb_mode' and not (0 <= preview_value <= 7):
                            valid = False

                        if valid:
                            preview_settings[preview_key] = preview_value
                            copied.append(f"{capture_key} → {preview_key}")
                        else:
                            skipped.append(f"{capture_key} (validation failed)")

                    except Exception as e:
                        skipped.append(f"{capture_key} (error: {str(e)})")
                else:
                    skipped.append(f"{capture_key} (not set in capture)")

            # Write updated live view settings
            with open(LIVEVIEW_SETTINGS_FILE, 'w') as f:
                for key, value in preview_settings.items():
                    if isinstance(value, bool):
                        f.write(f"{key}={'true' if value else 'false'}\n")
                    else:
                        f.write(f"{key}={value}\n")

            print(f"Copied settings to live view: {copied}")

        return jsonify({
            'success': True,
            'copied': copied,
            'copied_count': len(copied),
            'skipped': skipped,
            'skipped_count': len(skipped),
            'message': f'Copied {len(copied)} settings, skipped {len(skipped)}'
        })

    except Exception as e:
        import traceback
        print(f"Copy settings error: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
