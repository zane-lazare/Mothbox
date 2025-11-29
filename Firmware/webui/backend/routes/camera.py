"""Camera control endpoints"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Setup path to import mothbox_paths
# Import camera control mapping
from camera_control_mapping import build_picamera_controls, convert_from_settings_file
from flask import Blueprint, current_app, jsonify, request

# Import shared utilities
from utils import ALLOWED_CAMERA_SETTINGS, sanitize_csv_value

from mothbox_paths import CAMERA_SETTINGS_FILE, PHOTOS_DIR

# Import centralized constants
from constants import (
    AF_MODES_REQUIRING_TRIGGER,
    AF_PREVIEW_RESOLUTION,
    CAMERA_MAKE,
    CAMERA_MODEL,
    DEFAULT_COLOUR_GAINS,
    EXIF_RATIONAL_MAX,
    FB_DEFAULT_END_DIOPTERS,
    FB_DEFAULT_START_DIOPTERS,
    FB_MAX_DIOPTERS,
    FB_MAX_STEPS,
    FB_MIN_DIOPTERS,
    FB_MIN_STEPS,
    HDR_DEFAULT_WIDTH_US,
    HDR_MAX_WIDTH_US,
    HDR_MIN_WIDTH_US,
    HDR_VALID_COUNTS,
    TEST_CAPTURE_RESOLUTION,
)

# ============================================================================
# Operation Timeouts and Delays
# ============================================================================

# Camera hardware release timing
CAMERA_RELEASE_WAIT_SECONDS = (
    1.5  # Wait after releasing camera before subprocess (increased from 0.5s)
)

# Subprocess timeouts
CALIBRATION_TIMEOUT_SECONDS = (
    30  # Maximum time for photo calibration subprocess (matches TakePhoto.py timeout)
)

# Error reporting limits
ERROR_DETAILS_MAX_LENGTH = 500  # Maximum characters of stderr to include in API error responses


# ============================================================================
# Helper Functions
# ============================================================================


def acquire_camera_with_retry(
    camera_id: int = 0, max_retries: int = 3, wait_time: float = 2.0
) -> "Picamera2":
    """
    Acquire camera with retry logic for busy state

    Handles cases where hardware hasn't fully released yet after
    camera_streamer.release_camera() call. Common when switching
    between photo and stream workflows.

    Args:
        camera_id: Camera index (0 or 1)
        max_retries: Maximum number of retry attempts
        wait_time: Seconds to wait between retries

    Returns:
        Picamera2: Initialized camera instance

    Raises:
        RuntimeError: If camera cannot be acquired after max_retries
    """
    import time

    from picamera2 import Picamera2

    for attempt in range(max_retries):
        try:
            print(
                f"🎥 Attempting to acquire camera {camera_id} (attempt {attempt + 1}/{max_retries})"
            )
            return Picamera2(camera_id)
        except RuntimeError as e:
            error_msg = str(e).lower()
            if ("busy" in error_msg or "resource" in error_msg) and attempt < max_retries - 1:
                print(f"⚠️  Camera busy, waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                # Last attempt or non-busy error
                raise

    raise RuntimeError(f"Failed to acquire camera {camera_id} after {max_retries} attempts")


def _emit_calibration_progress(step, total_steps, message, progress):
    """
    Emit calibration progress via WebSocket for real-time progress updates

    Args:
        step: Current step number (1-indexed)
        total_steps: Total number of steps
        message: Human-readable status message
        progress: Progress percentage (0-100)
    """
    try:
        socketio = current_app.extensions.get("socketio")
        if socketio:
            socketio.emit(
                "calibration_progress",
                {
                    "step": step,
                    "total_steps": total_steps,
                    "message": message,
                    "progress": progress,
                },
            )
            print(f"📊 Calibration progress: Step {step}/{total_steps} ({progress}%) - {message}")
    except Exception as e:
        # Don't fail calibration if progress emission fails
        print(f"Warning: Failed to emit calibration progress: {e}")


def _build_exif_metadata(
    md: dict,
    settings_dict: dict,
    capture_type: str,
    picam2=None,
) -> bytes:
    """
    Build EXIF metadata bytes for photo capture.

    Centralizes EXIF generation for test captures and instant captures,
    reducing code duplication (~120 lines per function).

    Args:
        md: Camera metadata dict from picam2.capture_metadata()
        settings_dict: Camera settings dict (AfMode, Sharpness, etc.)
        capture_type: "test" or "instant" for MakerNote
        picam2: Optional Picamera2 instance for sensor detection

    Returns:
        bytes: EXIF data ready for PIL Image.save(exif=...)
    """
    import json

    import piexif

    from mothbox_paths import CONTROLS_FILE, get_firmware_version

    # Read mothbox name from controls.txt
    mothbox_name = "mothbox"
    try:
        if CONTROLS_FILE.exists():
            with open(CONTROLS_FILE) as f:
                for line in f:
                    if line.startswith("name="):
                        mothbox_name = line.split("=", 1)[1].strip()
                        break
    except Exception as e:
        print(f"Warning: Could not read mothbox name from controls.txt: {e}")

    # Detect sensor from Picamera2 metadata
    sensor_name = "Unknown"
    try:
        sensor_name = md.get("SensorName", "")
        if not sensor_name and picam2:
            model_str = str(picam2.camera_properties.get("Model", ""))
            if "ov64a40" in model_str.lower():
                sensor_name = "ov64a40"
            else:
                sensor_name = model_str or "Unknown"
    except Exception as e:
        print(f"Warning: Could not detect sensor: {e}")

    # Get firmware version
    firmware_version = get_firmware_version()

    # Build 0th IFD (main image metadata)
    zeroth_ifd = {
        piexif.ImageIFD.Make: CAMERA_MAKE.encode("utf-8"),
        piexif.ImageIFD.Model: CAMERA_MODEL.encode("utf-8"),
        piexif.ImageIFD.Software: firmware_version.encode("utf-8"),
    }

    # Extract exposure time and convert to EXIF rational format
    exposure_time_us = md.get("ExposureTime", 1000)  # microseconds
    exposure_time_s = exposure_time_us / 1000000.0  # convert to seconds
    if exposure_time_s > 0:
        # Store as (numerator, denominator) rational with overflow protection
        denominator = min(int(1 / exposure_time_s), EXIF_RATIONAL_MAX)
        exif_exposure = (1, denominator)
    else:
        exif_exposure = (1, 1000)

    # Get current timestamp for DateTimeOriginal
    capture_timestamp = datetime.now().strftime('%Y:%m:%d %H:%M:%S')

    # Build Exif IFD
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: capture_timestamp.encode('utf-8'),
        piexif.ExifIFD.ExposureTime: exif_exposure,
        piexif.ExifIFD.FocalLength: (
            int(md.get("LensPosition", 0.0) * 100),
            10,
        ),  # Store with extra precision
        piexif.ExifIFD.ISOSpeed: int(md.get("AnalogueGain", 1.0) * 100),
        piexif.ExifIFD.ISOSpeedRatings: int(md.get("AnalogueGain", 1.0) * 100),
        piexif.ExifIFD.WhiteBalance: 0,  # 0 = Auto white balance
        piexif.ExifIFD.Flash: 0,  # 0 = Flash did not fire
        piexif.ExifIFD.ExposureMode: 0 if settings_dict.get("AfMode", 2) == 0 else 1,
        piexif.ExifIFD.MeteringMode: int(settings_dict.get("AeMeteringMode", 2)),
        piexif.ExifIFD.Sharpness: int(settings_dict.get("Sharpness", 1.0)),
        piexif.ExifIFD.Contrast: int(settings_dict.get("Contrast", 1.0)),
        piexif.ExifIFD.Saturation: int(settings_dict.get("Saturation", 1.0)),
        piexif.ExifIFD.BrightnessValue: (int(settings_dict.get("Brightness", 0.0) * 100), 100),
    }

    # Add MakerNote with Mothbox-specific metadata
    maker_note_data = {
        "mothbox_name": mothbox_name or "mothbox",
        "capture_type": capture_type,
        "sensor": sensor_name,
        "focus_mode": int(settings_dict.get("AfMode", 2)),
        "af_range": int(settings_dict.get("AfRange", 0)),
        "af_speed": int(settings_dict.get("AfSpeed", 0)),
        "noise_reduction": int(settings_dict.get("NoiseReductionMode", 2)),
        "lens_position": float(md.get("LensPosition", 0.0)),
        "colour_gain_red": float(settings_dict.get("ColourGains", DEFAULT_COLOUR_GAINS)[0]) if "ColourGains" in settings_dict else DEFAULT_COLOUR_GAINS[0],
        "colour_gain_blue": float(settings_dict.get("ColourGains", DEFAULT_COLOUR_GAINS)[1]) if "ColourGains" in settings_dict else DEFAULT_COLOUR_GAINS[1],
    }
    exif_ifd[piexif.ExifIFD.MakerNote] = json.dumps(maker_note_data).encode('utf-8')

    # GPS IFD - embed GPS coordinates from controls.txt if available
    gps_ifd = {}
    try:
        from webui.backend.lib.gps_exif_lib import build_gps_ifd, get_gps_data_from_controls

        gps_data = get_gps_data_from_controls()
        if gps_data.get('has_fix'):
            gps_ifd = build_gps_ifd(gps_data)
            if gps_ifd:
                # CodeQL: py/clear-text-logging-sensitive-data - GPS coordinates are equipment deployment location for wildlife monitoring, not personal/user data
                print(f"GPS EXIF embedded: lat={gps_data['latitude']}, lon={gps_data['longitude']}")
    except Exception as gps_error:
        print(f"Warning: Could not embed GPS EXIF: {gps_error}")

    # Build complete EXIF dictionary
    exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd, "1st": {}}
    if gps_ifd:
        exif_dict["GPS"] = gps_ifd

    return piexif.dump(exif_dict)


camera_bp = Blueprint("camera", __name__)


def _should_use_hdr_mode() -> tuple[bool, int, int]:
    """
    Check if HDR mode is enabled in camera settings

    Returns:
        tuple: (bool, int, int) - (use_hdr, hdr_count, hdr_width)
               use_hdr: True if HDR > 1
               hdr_count: Number of exposures (1, 3, 5, or 7)
               hdr_width: Bracket step size in microseconds
    """
    try:
        import csv

        from mothbox_paths import CAMERA_SETTINGS_FILE

        hdr_count = 1
        hdr_width = HDR_DEFAULT_WIDTH_US

        if not CAMERA_SETTINGS_FILE.exists():
            print("ℹ️  camera_settings.csv not found, defaulting to single exposure")
            return False, 1, HDR_DEFAULT_WIDTH_US

        with open(CAMERA_SETTINGS_FILE) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["SETTING"] == "HDR":
                    try:
                        hdr_count = int(row["VALUE"])
                        # Validate HDR count is one of the allowed values
                        if hdr_count not in HDR_VALID_COUNTS:
                            print(
                                f"⚠️  Invalid HDR count {hdr_count}, must be 1, 3, 5, or 7. Defaulting to 1."
                            )
                            hdr_count = 1
                    except (ValueError, KeyError) as e:
                        print(f"⚠️  Could not parse HDR setting value: {e}. Defaulting to 1.")
                        hdr_count = 1
                elif row["SETTING"] == "HDR_width":
                    try:
                        hdr_width = int(row["VALUE"])
                        # Validate bracket width is in reasonable range (1ms - 50ms)
                        if not (HDR_MIN_WIDTH_US <= hdr_width <= HDR_MAX_WIDTH_US):
                            print(
                                f"⚠️  Invalid HDR_width {hdr_width}µs, must be {HDR_MIN_WIDTH_US}-{HDR_MAX_WIDTH_US}. Defaulting to {HDR_DEFAULT_WIDTH_US}."
                            )
                            hdr_width = HDR_DEFAULT_WIDTH_US
                    except (ValueError, KeyError) as e:
                        print(
                            f"⚠️  Could not parse HDR_width setting value: {e}. Defaulting to {HDR_DEFAULT_WIDTH_US}."
                        )
                        hdr_width = HDR_DEFAULT_WIDTH_US

        use_hdr = hdr_count > 1

        # Log the decision
        if use_hdr:
            print(f"✓ HDR mode enabled: {hdr_count} exposures with {hdr_width}µs bracket width")
        else:
            print(f"✓ Single exposure mode (HDR={hdr_count})")

        return use_hdr, hdr_count, hdr_width

    except Exception as e:
        print(f"❌ Error reading HDR settings: {e}. Defaulting to single exposure.")
        return False, 1, HDR_DEFAULT_WIDTH_US


def _should_use_focus_bracket_mode() -> tuple[bool, int, float, float]:
    """
    Check if Focus Bracketing mode is enabled in camera settings

    Returns:
        tuple: (bool, int, float, float) - (use_focus_bracket, steps, start, end)
               use_focus_bracket: True if FocusBracket > 1
               steps: Number of focus steps (1-10)
               start: Starting focus position in diopters (0-10)
               end: Ending focus position in diopters (0-10)
    """
    try:
        import csv

        from mothbox_paths import CAMERA_SETTINGS_FILE

        steps = 1
        start = FB_DEFAULT_START_DIOPTERS
        end = FB_DEFAULT_END_DIOPTERS

        if not CAMERA_SETTINGS_FILE.exists():
            print("ℹ️  camera_settings.csv not found, defaulting to single focus")
            return False, 1, FB_DEFAULT_START_DIOPTERS, FB_DEFAULT_END_DIOPTERS

        with open(CAMERA_SETTINGS_FILE) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["SETTING"] == "FocusBracket":
                    try:
                        steps = int(row["VALUE"])
                        # Validate steps is in allowed range
                        if not (FB_MIN_STEPS <= steps <= FB_MAX_STEPS):
                            print(
                                f"⚠️  Invalid FocusBracket count {steps}, must be {FB_MIN_STEPS}-{FB_MAX_STEPS}. Defaulting to 1."
                            )
                            steps = 1
                    except (ValueError, KeyError) as e:
                        print(
                            f"⚠️  Could not parse FocusBracket setting value: {e}. Defaulting to 1."
                        )
                        steps = 1
                elif row["SETTING"] == "FocusBracket_Start":
                    try:
                        start = float(row["VALUE"])
                        # Validate start is in reasonable range
                        if not (FB_MIN_DIOPTERS <= start <= FB_MAX_DIOPTERS):
                            print(
                                f"⚠️  Invalid FocusBracket_Start {start}, must be {FB_MIN_DIOPTERS}-{FB_MAX_DIOPTERS}. Defaulting to {FB_DEFAULT_START_DIOPTERS}."
                            )
                            start = FB_DEFAULT_START_DIOPTERS
                    except (ValueError, KeyError) as e:
                        print(
                            f"⚠️  Could not parse FocusBracket_Start setting value: {e}. Defaulting to {FB_DEFAULT_START_DIOPTERS}."
                        )
                        start = FB_DEFAULT_START_DIOPTERS
                elif row["SETTING"] == "FocusBracket_End":
                    try:
                        end = float(row["VALUE"])
                        # Validate end is in reasonable range
                        if not (FB_MIN_DIOPTERS <= end <= FB_MAX_DIOPTERS):
                            print(
                                f"⚠️  Invalid FocusBracket_End {end}, must be {FB_MIN_DIOPTERS}-{FB_MAX_DIOPTERS}. Defaulting to {FB_DEFAULT_END_DIOPTERS}."
                            )
                            end = FB_DEFAULT_END_DIOPTERS
                    except (ValueError, KeyError) as e:
                        print(
                            f"⚠️  Could not parse FocusBracket_End setting value: {e}. Defaulting to {FB_DEFAULT_END_DIOPTERS}."
                        )
                        end = FB_DEFAULT_END_DIOPTERS

        use_focus_bracket = steps > 1

        # Log the decision
        if use_focus_bracket:
            print(f"✓ Focus Bracket mode enabled: {steps} steps from {start} to {end} diopters")
        else:
            print(f"✓ Single focus mode (FocusBracket={steps})")

        return use_focus_bracket, steps, start, end

    except Exception as e:
        print(f"❌ Error reading Focus Bracket settings: {e}. Defaulting to single focus.")
        return False, 1, FB_DEFAULT_START_DIOPTERS, FB_DEFAULT_END_DIOPTERS


@camera_bp.route("/capture", methods=["POST"])
def capture_photo():
    """Trigger a photo capture (automatically uses HDR if configured)"""
    try:
        # Determine Pi version to find correct TakePhoto.py or TakePhoto_HDR.py
        import time

        from flask import current_app

        from mothbox_paths import MOTHBOX_HOME, get_takephoto_script

        print(f"Photo capture requested. MOTHBOX_HOME: {MOTHBOX_HOME}")

        # Check if Focus Bracket mode is enabled (takes priority over HDR)
        use_focus_bracket, fb_steps, fb_start, fb_end = _should_use_focus_bracket_mode()

        # Check if HDR mode is enabled (only if not doing focus bracketing)
        use_hdr, hdr_count, hdr_width = (
            _should_use_hdr_mode() if not use_focus_bracket else (False, 1, 7000)
        )

        # Check if Pi 4 or Pi 5
        pi_version = None
        try:
            with open("/proc/cpuinfo") as f:
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

        # Determine which script to use based on Focus Bracket and HDR settings
        if use_focus_bracket:
            script_name = "capture_focus_bracket.py"
            script_path = MOTHBOX_HOME / "webui" / "backend" / "scripts" / script_name
            print(
                f"🎯 Focus Bracket mode enabled: {fb_steps} steps from {fb_start} to {fb_end} diopters"
            )
        elif use_hdr:
            script_name = "TakePhoto_HDR.py"
            script_path = MOTHBOX_HOME / f"{pi_version}.x" / "scripts" / script_name
            print(f"📸 HDR mode enabled: {hdr_count} exposures, {hdr_width}µs bracket width")
        else:
            # Use get_takephoto_script() for standard captures to get correct path
            script_path = get_takephoto_script()
            script_name = "TakePhoto.py"
            print("📸 Standard single-exposure mode")

        print(f"Looking for {script_name} at: {script_path}")

        if not script_path.exists():
            error_msg = f"{script_name} not found at {script_path}"
            print(error_msg)

            # Provide helpful context based on script type
            if script_name == "TakePhoto.py":
                help_msg = f"Ensure TakePhoto.py exists in the {pi_version}.x directory"
            elif script_name == "TakePhoto_HDR.py":
                help_msg = f"Ensure TakePhoto_HDR.py exists in the {pi_version}.x/scripts directory"
            else:
                help_msg = f"Ensure {script_name} exists in webui/backend/scripts directory"

            return jsonify(
                {
                    "success": False,
                    "error": error_msg,
                    "help": help_msg,
                }
            ), 500

        # Helper function for subprocess execution (used with or without lock)
        def run_takephoto_subprocess():
            """Execute TakePhoto.py subprocess with optional stream management"""
            # Release streaming camera if active
            was_streaming = False
            if camera_streamer and camera_streamer.camera:
                print("Releasing camera hardware before TakePhoto.py subprocess...")
                was_streaming = camera_streamer.streaming
                camera_streamer.release_camera()
                time.sleep(0.5)  # Let camera fully release

            try:
                print(f"Running: python3 {script_path}")
                result = subprocess.run(
                    ["python3", str(script_path)], capture_output=True, text=True, timeout=30
                )

                print(f"TakePhoto.py exit code: {result.returncode}")
                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")

                if result.returncode == 0:
                    # Find the most recent photo(s)
                    photos = sorted(
                        PHOTOS_DIR.glob("**/*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True
                    )
                    latest_photo = str(photos[0].relative_to(PHOTOS_DIR)) if photos else None

                    # Invalidate photo count cache so dashboard shows updated count immediately
                    from routes.system import invalidate_photo_count_cache

                    invalidate_photo_count_cache()

                    # Invalidate location-related caches so map view shows new photo
                    try:
                        from webui.backend.app import (
                            clustering_service,
                            series_service,
                            locations_service
                        )

                        if clustering_service:
                            clustering_service.invalidate_cache(PHOTOS_DIR)
                        if series_service:
                            series_service.invalidate_cache(PHOTOS_DIR)
                        if locations_service:
                            locations_service.invalidate_cache(PHOTOS_DIR)

                        logger.debug("Invalidated location/clustering/series caches after photo capture")
                    except ImportError:
                        # Services not yet initialized - this is fine during startup
                        pass
                    except Exception as cache_error:
                        # Log but don't fail capture on cache invalidation errors
                        logger.warning(f"Failed to invalidate caches: {cache_error}")

                    # Build success response with Focus Bracket / HDR metadata
                    response_data = {
                        "success": True,
                        "latest_photo": latest_photo,
                        "output": result.stdout,
                        "focus_bracket_mode": use_focus_bracket,
                        "hdr_mode": use_hdr,
                        "script_used": script_name,
                    }

                    if use_focus_bracket:
                        response_data["focus_bracket_steps"] = fb_steps
                        response_data["focus_bracket_start"] = fb_start
                        response_data["focus_bracket_end"] = fb_end
                        response_data["message"] = (
                            f"Focus bracket capture complete: {fb_steps} steps from {fb_start} to {fb_end} diopters"
                        )
                    elif use_hdr:
                        response_data["hdr_count"] = hdr_count
                        response_data["hdr_width"] = hdr_width
                        response_data["message"] = (
                            f"HDR capture complete: {hdr_count} exposures with {hdr_width}µs bracket width"
                        )
                    else:
                        response_data["message"] = "Single exposure capture complete"

                    return jsonify(response_data)
                else:
                    return jsonify({"success": False, "error": result.stderr or result.stdout}), 500

            finally:
                # Always restart stream if it was active
                if was_streaming and camera_streamer:
                    print("Restarting camera stream after TakePhoto.py subprocess...")
                    try:
                        camera_streamer.start_streaming()
                    except Exception as restart_error:
                        print(f"Warning: Failed to restart stream: {restart_error}")

        # Acquire operation lock to prevent concurrent camera access (if available)
        camera_streamer = current_app.config.get("CAMERA_STREAMER")

        if camera_streamer:
            # Production mode: use lock to serialize with other camera operations
            with camera_streamer.acquire_for_operation():
                return run_takephoto_subprocess()
        else:
            # Standalone/test mode: no lock available, run subprocess directly
            return run_takephoto_subprocess()

    except subprocess.TimeoutExpired:
        error_msg = "Photo capture timed out"
        print(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500
    except Exception as e:
        import traceback

        error_msg = str(e)
        print(f"Photo capture error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": error_msg}), 500


@camera_bp.route("/settings", methods=["GET"])
def get_camera_settings():
    """Get camera settings from CSV (vertical format: SETTING,VALUE,DETAILS)"""
    try:
        import csv

        from mothbox_paths import CAMERA_SETTINGS_FILE

        settings = {}
        with open(CAMERA_SETTINGS_FILE) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Build settings dict from vertical CSV format
                setting_name = row["SETTING"].strip()
                setting_value = row["VALUE"].strip()
                settings[setting_name] = setting_value

        return jsonify(settings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@camera_bp.route("/settings", methods=["POST"])
def update_camera_settings():
    """Update camera settings (vertical CSV format: SETTING,VALUE,DETAILS)"""
    try:
        import csv

        from mothbox_paths import CAMERA_SETTINGS_FILE

        new_settings = request.json

        # Validate camera settings
        for key, value in new_settings.items():
            if key not in ALLOWED_CAMERA_SETTINGS:
                return jsonify({"error": f"Invalid setting: {key}"}), 400
            try:
                if not ALLOWED_CAMERA_SETTINGS[key](value):
                    return jsonify({"error": f"Invalid value for {key}"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": f"Invalid type for {key}"}), 400

        # Read current settings (vertical format: each row is a setting)
        csv_rows = []
        if CAMERA_SETTINGS_FILE.exists():
            with open(CAMERA_SETTINGS_FILE) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    csv_rows.append(dict(row))

        # Sanitize values to prevent CSV injection (defense in depth)
        sanitized_settings = {k: sanitize_csv_value(v) for k, v in new_settings.items()}

        # Update the corresponding rows
        for setting_name, setting_value in sanitized_settings.items():
            # Find and update the row for this setting
            found = False
            for row in csv_rows:
                if row["SETTING"].strip() == setting_name:
                    row["VALUE"] = str(setting_value)
                    found = True
                    break

            # If setting doesn't exist, add a new row
            if not found:
                csv_rows.append(
                    {"SETTING": setting_name, "VALUE": str(setting_value), "DETAILS": ""}
                )

        # Write back all settings in vertical format
        with open(CAMERA_SETTINGS_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["SETTING", "VALUE", "DETAILS"])
            writer.writeheader()
            writer.writerows(csv_rows)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@camera_bp.route("/autofocus", methods=["POST"])
def trigger_autofocus():
    """
    Trigger autofocus cycle

    Based on PlowmanAutofocus.py and TakePhoto.py:410 pattern.

    Returns:
        JSON with:
        - success: bool - whether autofocus succeeded
        - af_state: str - "Idle", "Scanning", "Success", or "Fail"
        - lens_position: float - final lens position in diopters
        - metadata: dict - exposure, gain, etc. from final frame
    """
    try:
        import time

        from flask import current_app

        print("Autofocus requested via API")

        # Acquire operation lock to prevent concurrent camera access
        camera_streamer = current_app.config.get("CAMERA_STREAMER")
        if not camera_streamer:
            return jsonify({"success": False, "error": "Camera streamer not initialized"}), 500

        with camera_streamer.acquire_for_operation():
            # Release camera hardware if initialized (prevents resource conflict)
            was_streaming = False
            if camera_streamer.camera:
                print("Releasing camera hardware before autofocus...")
                was_streaming = camera_streamer.streaming
                camera_streamer.release_camera()
                time.sleep(1.5)  # Let camera fully release (increased from 0.5s)

            # Initialize camera for autofocus
            picam2 = None
            try:
                # Try camera 0 first with retry logic, fallback to camera 1
                try:
                    picam2 = acquire_camera_with_retry(0)
                except Exception:
                    picam2 = acquire_camera_with_retry(1)

                # Configure for high-res preview (better for AF accuracy)
                preview_config = picam2.create_preview_configuration(
                    main={"format": "RGB888", "size": AF_PREVIEW_RESOLUTION}
                )
                picam2.configure(preview_config)

                # Start camera
                picam2.start()

                # Set initial focus controls for AF
                picam2.set_controls(
                    {
                        "AfSpeed": 0,  # Normal speed for accuracy
                        "AfMetering": 0,  # Auto metering
                        "LensPosition": 7.0,  # Starting position
                    }
                )

                # Let camera stabilize
                time.sleep(0.3)

                # Trigger autofocus cycle
                print("Running autofocus cycle...")
                af_start = time.time()
                success = picam2.autofocus_cycle()
                af_duration = time.time() - af_start
                print(
                    f"Autofocus completed in {af_duration:.2f}s: {'Success' if success else 'Failed'}"
                )

                # Get result metadata
                metadata = picam2.capture_metadata()
                lens_position = metadata.get("LensPosition", 0.0)
                af_state_code = metadata.get("AfState", 0)
                af_state = ("Idle", "Scanning", "Success", "Fail")[af_state_code]

                # Capture additional metadata for UI display
                exposure_time = metadata.get("ExposureTime", 0)
                analogue_gain = metadata.get("AnalogueGain", 0.0)
                colour_temp = metadata.get("ColourTemperature", 0)

                # Stop camera
                picam2.stop()
                picam2.close()

                # Lock to manual focus mode to preserve AF position
                # This prevents continuous AF from overriding the locked focus when stream restarts
                if success:
                    print("Locking to manual focus mode to preserve autofocus position...")
                    camera_streamer.set_manual_focus_mode(True)
                    print(f"✓ Manual focus locked at {lens_position:.2f} diopters")

                return jsonify(
                    {
                        "success": success,
                        "af_state": af_state,
                        "lens_position": round(lens_position, 2),
                        "duration_seconds": round(af_duration, 2),
                        "metadata": {
                            "exposure_time": exposure_time,
                            "analogue_gain": round(analogue_gain, 2),
                            "colour_temperature": colour_temp,
                        },
                        "message": f"Autofocus {'succeeded' if success else 'failed'} at {lens_position:.2f} diopters",
                    }
                )

            except Exception as camera_error:
                # Ensure camera is closed on error
                if picam2:
                    try:
                        picam2.stop()
                        picam2.close()
                    except Exception:
                        pass

                # Stream restart handled by finally block to avoid duplicate restarts
                raise camera_error

            finally:
                # Always restart stream if it was active (handles both success and error cases)
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
        return jsonify(
            {"success": False, "error": error_msg}
        ), 500


@camera_bp.route("/calibrate-photo", methods=["POST"])
def calibrate_photo():
    """
    Calibrate TakePhoto.py settings

    Runs TakePhoto.py's run_calibration() function via subprocess
    to properly calibrate exposure, gain, and focus for high-res
    still photos with flash.

    Updates camera_settings.csv and LastCalibration timestamp.

    Returns:
        JSON with:
        - success: bool
        - before: dict - settings before calibration
        - after: dict - settings after calibration
        - af_success: bool - whether autofocus succeeded
        - af_duration_seconds: float - calibration duration
        - timestamp: float - calibration timestamp
    """
    import csv
    import subprocess
    import time
    import traceback

    from flask import current_app

    from mothbox_paths import get_firmware_version

    print("📸 Photo calibration requested via API")

    # Emit progress: Starting calibration
    _emit_calibration_progress(1, 4, "Starting photo calibration...", 0)

    # Read current settings for "before" snapshot
    before_settings = {}
    try:
        with open(CAMERA_SETTINGS_FILE) as f:
            reader = csv.DictReader(f)
            for row in reader:
                before_settings[row["SETTING"]] = row["VALUE"]
    except Exception as e:
        print(f"⚠️  Warning: Could not read current settings: {e}")

    before_snapshot = {
        "ExposureTime": before_settings.get("ExposureTime", "unknown"),
        "AnalogueGain": before_settings.get("AnalogueGain", "unknown"),
        "LensPosition": before_settings.get("LensPosition", "unknown"),
    }

    # Get camera streamer
    camera_streamer = current_app.config.get("CAMERA_STREAMER")
    if not camera_streamer:
        return jsonify({"success": False, "error": "Camera streamer not initialized"}), 500

    # Track state for cleanup
    was_streaming = False
    operation_lock_acquired = False
    subprocess_result = None
    start_time = time.time()

    try:
        # Acquire operation lock
        with camera_streamer.acquire_for_operation():
            operation_lock_acquired = True

            # Release camera hardware completely
            if camera_streamer.camera:
                print("🔓 Releasing camera for photo calibration subprocess...")
                was_streaming = camera_streamer.streaming
                camera_streamer.release_camera()
                time.sleep(CAMERA_RELEASE_WAIT_SECONDS)  # Ensure hardware fully released

            # Emit progress: Running subprocess
            _emit_calibration_progress(2, 4, "Running photo calibration subprocess...", 25)

            # Run calibration via subprocess
            calibration_script = (
                Path(__file__).parent.parent / "scripts" / "run_photo_calibration.py"
            )

            print(f"🚀 Running photo calibration subprocess: {calibration_script}")

            try:
                subprocess_result = subprocess.run(
                    ["python3", str(calibration_script)],
                    capture_output=True,
                    text=True,
                    timeout=CALIBRATION_TIMEOUT_SECONDS,
                )
            finally:
                # Always restart stream if it was active, even if subprocess fails/times out
                duration = time.time() - start_time
                if was_streaming and camera_streamer:
                    print("🔄 Restarting camera stream after photo calibration...")
                    try:
                        camera_streamer.start_streaming()
                        print("✅ Stream restarted successfully")
                    except Exception as restart_error:
                        print(f"❌ Warning: Failed to restart stream: {restart_error}")
                        traceback.print_exc()

        # Check subprocess result
        if subprocess_result is None:
            # Should not happen, but handle defensive case
            return jsonify(
                {"success": False, "error": "Calibration subprocess did not complete"}
            ), 500

        if subprocess_result.returncode != 0:
            # Log detailed error server-side
            print(f"❌ Calibration subprocess failed with code {subprocess_result.returncode}")
            print(f"stderr: {subprocess_result.stderr}")
            print(f"stdout: {subprocess_result.stdout}")

            # Determine error type from stderr
            error_msg = "Calibration subprocess failed"
            stderr_lower = subprocess_result.stderr.lower() if subprocess_result.stderr else ""

            if "filenotfounderror" in stderr_lower:
                firmware_version = get_firmware_version()
                error_msg = f"TakePhoto.py not found for firmware {firmware_version}.x"
            elif "importerror" in stderr_lower or "modulenotfounderror" in stderr_lower:
                error_msg = "TakePhoto.py import failed - missing dependencies"
            elif "busy" in stderr_lower or "resource" in stderr_lower:
                error_msg = "Camera hardware busy"
            elif "permission" in stderr_lower or "denied" in stderr_lower:
                error_msg = "Permission denied accessing camera"

            # Return sanitized error with last N chars of stderr for debugging
            return jsonify(
                {
                    "success": False,
                    "error": error_msg,
                    "details": subprocess_result.stderr[-ERROR_DETAILS_MAX_LENGTH:]
                    if subprocess_result.stderr
                    else None,
                    "returncode": subprocess_result.returncode,
                }
            ), 500

        # Emit progress: Parsing results
        _emit_calibration_progress(3, 4, "Parsing calibration results...", 75)

        # Read updated settings for "after" snapshot
        after_settings = {}
        try:
            with open(CAMERA_SETTINGS_FILE) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    after_settings[row["SETTING"]] = row["VALUE"]
        except Exception as e:
            print(f"⚠️  Warning: Could not read updated settings: {e}")

        after_snapshot = {
            "ExposureTime": after_settings.get("ExposureTime", "unknown"),
            "AnalogueGain": after_settings.get("AnalogueGain", "unknown"),
            "LensPosition": after_settings.get("LensPosition", "unknown"),
        }

        print(f"✅ Photo calibration completed in {duration:.2f}s")
        print(
            f"   Before: Exp={before_snapshot['ExposureTime']}, Gain={before_snapshot['AnalogueGain']}, Lens={before_snapshot['LensPosition']}"
        )
        print(
            f"   After:  Exp={after_snapshot['ExposureTime']}, Gain={after_snapshot['AnalogueGain']}, Lens={after_snapshot['LensPosition']}"
        )

        # Emit progress: Complete
        _emit_calibration_progress(4, 4, "Photo calibration complete!", 100)

        return jsonify(
            {
                "success": True,
                "before": before_snapshot,
                "after": after_snapshot,
                "af_success": True,  # run_calibration() always runs AF
                "af_duration_seconds": round(duration, 2),
                "timestamp": time.time(),
                "message": "Photo calibration completed via TakePhoto.py subprocess",
            }
        )

    except subprocess.TimeoutExpired:
        print("⏱️  Calibration subprocess timeout (>30s)")
        # Stream should already be restarted by finally block above
        return jsonify({"success": False, "error": "Calibration timeout (>30s)"}), 500

    except Exception as e:
        # Log full error for debugging
        print(f"❌ Calibration error: {e}")
        traceback.print_exc()

        # Ensure stream is restarted even on unexpected errors
        if was_streaming and camera_streamer and not operation_lock_acquired:
            try:
                print("🔄 Emergency stream restart after error...")
                camera_streamer.start_streaming()
            except Exception as restart_error:
                print(f"❌ Failed emergency restart: {restart_error}")

        return jsonify(
            {"success": False, "error": str(e)}
        ), 500


# ============================================================================
# Migration Note:
# The /calibrate endpoint was removed and replaced by /calibrate-photo.
# Use the new subprocess-based endpoint for proper camera resource management.
# ============================================================================


@camera_bp.route("/freeze-settings", methods=["POST"])
def freeze_settings():
    """
    Freeze camera settings to current values

    Locks exposure, gain, and focus to prevent automatic adjustments.
    Useful for reproducible captures under consistent conditions.

    Returns:
        JSON with:
        - success: bool
        - frozen_settings: dict - values that were locked
        - message: str
    """
    try:
        import csv
        import time

        # Acquire operation lock to prevent concurrent camera access
        from flask import current_app
        from picamera2 import Picamera2

        from mothbox_paths import CAMERA_SETTINGS_FILE

        camera_streamer = current_app.config.get("CAMERA_STREAMER")
        if not camera_streamer:
            return jsonify({"success": False, "error": "Camera streamer not initialized"}), 500

        with camera_streamer.acquire_for_operation():
            # Release streaming camera if active
            if hasattr(current_app, "camera_streamer") and current_app.camera_streamer.streaming:
                current_app.camera_streamer.stop_stream()
                time.sleep(0.5)

            # Initialize camera to get current metadata
            picam2 = Picamera2()
            preview_config = picam2.create_preview_configuration(
                main={"size": AF_PREVIEW_RESOLUTION, "format": "RGB888"}
            )
            picam2.configure(preview_config)
            picam2.start()

            # Let camera stabilize
            time.sleep(0.5)

            # Capture current metadata
            md = picam2.capture_metadata()

            current_exposure = md.get("ExposureTime", 0)
            current_gain = md.get("AnalogueGain", 1.0)
            current_lens_position = md.get("LensPosition", 0.0)

            picam2.stop()
            picam2.close()

            # Read current settings
            current_settings = {}
            settings_details = {}

            with open(CAMERA_SETTINGS_FILE, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    setting = row.get("SETTING", "").strip()
                    value = row.get("VALUE", "").strip()
                    details = row.get("DETAILS", "").strip()
                    if setting:
                        current_settings[setting] = value
                        settings_details[setting] = details

            # Update with frozen values and disable auto modes
            current_settings["AeEnable"] = "False"  # Disable auto-exposure
            current_settings["AwbEnable"] = "False"  # Disable auto white balance
            current_settings["AfMode"] = "0"  # Set to manual focus
            current_settings["ExposureTime"] = str(int(current_exposure))
            current_settings["AnalogueGain"] = str(round(current_gain, 2))
            current_settings["LensPosition"] = str(round(current_lens_position, 2))

            # Write back to CSV
            fieldnames = ["SETTING", "VALUE", "DETAILS"]
            with open(CAMERA_SETTINGS_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(fieldnames)
                for setting, value in current_settings.items():
                    details = settings_details.get(setting, "")
                    writer.writerow([setting, value, details])

            # Restart streaming camera
            if hasattr(current_app, "camera_streamer"):
                current_app.camera_streamer.start_stream()

            frozen_values = {
                "ExposureTime": int(current_exposure),
                "AnalogueGain": round(current_gain, 2),
                "LensPosition": round(current_lens_position, 2),
                "AeEnable": False,
                "AwbEnable": False,
                "AfMode": 0,
            }

            return jsonify(
                {
                    "success": True,
                    "frozen_settings": frozen_values,
                    "message": f"Settings frozen at Exp={int(current_exposure)}µs, Gain={round(current_gain, 2)}, Focus={round(current_lens_position, 2)}D",
                    "timestamp": time.time(),
                }
            )

    except Exception as e:
        import traceback

        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


def _execute_test_capture(settings_dict, af_mode, settings_source):
    """
    Helper function to execute a test capture with given settings

    Args:
        settings_dict: Dict of camera control values to apply
        af_mode: Autofocus mode (1=Auto, 2=Manual, 3=Continuous)
        settings_source: String describing source ('live view' or 'photo capture')

    Returns:
        tuple: (success_dict, status_code) or raises exception
    """
    import gc
    import time
    from datetime import datetime

    from flask import current_app

    from mothbox_paths import PHOTOS_DIR

    # Acquire operation lock to prevent concurrent camera access
    camera_streamer = current_app.config.get("CAMERA_STREAMER")
    if not camera_streamer:
        return jsonify({"success": False, "error": "Camera streamer not initialized"}), 500

    with camera_streamer.acquire_for_operation():
        # Release camera hardware if initialized (prevents resource conflict)
        was_streaming = False
        if camera_streamer.camera:
            print("Releasing camera hardware before test capture...")
            was_streaming = camera_streamer.streaming
            camera_streamer.release_camera()
            time.sleep(0.5)  # Let camera fully release

        # Initialize camera for test capture
        picam2 = None
        try:
            # Try camera 0 first with retry logic, fallback to camera 1
            try:
                picam2 = acquire_camera_with_retry(0)
            except Exception:
                picam2 = acquire_camera_with_retry(1)

            # Configure for high-resolution test capture
            # Use 4K instead of 64MP to fit within Pi 5's 64MB CMA constraint (~24MB vs ~180MB)
            # Production 64MP captures still work via /api/camera/capture → TakePhoto.py (standalone process)
            # 4K provides excellent quality for previewing settings in WebUI
            # Disable raw/lores buffers to reduce CMA usage (matches TakePhoto.py pattern)
            # Note: Picamera2 format names are counterintuitive - "BGR888" outputs RGB byte order
            # (See: https://github.com/raspberrypi/picamera2/discussions/568)
            capture_config = picam2.create_still_configuration(
                main={
                    "size": TEST_CAPTURE_RESOLUTION,
                    "format": "BGR888",  # Outputs RGB-ordered bytes for PIL compatibility
                },
                raw=None,
                lores=None,
            )
            picam2.configure(capture_config)

            # Start camera
            picam2.start()

            # Apply controls using build_picamera_controls() to convert snake_case → PascalCase
            # This ensures camera accepts the control keys (e.g., af_mode → AfMode)
            controls = build_picamera_controls(settings_dict)

            picam2.set_controls(controls)
            print(f"Applied {settings_source} settings to test capture: {controls}")

            # Wait for settings to stabilize
            time.sleep(0.5)

            # Trigger autofocus if in Auto mode (1) or Continuous mode (3)
            if af_mode in AF_MODES_REQUIRING_TRIGGER:
                print(f"Triggering autofocus (mode={af_mode})...")
                try:
                    picam2.autofocus_cycle()
                    # Wait for autofocus to complete
                    time.sleep(1.0)
                    print("Autofocus cycle completed")
                except Exception as af_error:
                    print(f"Warning: Autofocus cycle failed: {af_error}")
                    # Continue with capture even if AF fails
            else:
                # Manual focus mode - no autofocus trigger needed
                time.sleep(0.5)  # Additional stabilization time

            # Create test_captures directory
            test_dir = PHOTOS_DIR / "test_captures"
            test_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_capture_{timestamp}.jpg"
            filepath = test_dir / filename

            # Capture photo with rich EXIF metadata
            print(f"Capturing test photo to: {filepath}")

            # Capture array and metadata (instead of capture_file to allow custom EXIF)
            array = picam2.capture_array("main")
            md = picam2.capture_metadata()

            # Build EXIF metadata using centralized helper
            from PIL import Image

            exif_bytes = _build_exif_metadata(md, settings_dict, "test", picam2)

            # Save with EXIF (Picamera2 BGR888 outputs RGB bytes - no conversion needed)
            pil_image = Image.fromarray(array, mode="RGB")
            pil_image.save(str(filepath), exif=exif_bytes, quality=95)
            print(f"Saved test capture with rich EXIF metadata to {filepath}")

            # Stop camera
            picam2.stop()
            picam2.close()

            # Force garbage collection to free CMA buffers immediately
            # Critical for tests doing multiple captures in sequence
            gc.collect()
            gc.collect()

            # Return relative path from PHOTOS_DIR
            relative_path = str(filepath.relative_to(PHOTOS_DIR))

            return jsonify(
                {
                    "success": True,
                    "test_photo_path": relative_path,
                    "settings_used": controls,
                    "settings_source": settings_source,
                    "metadata": {
                        "exposure_time": md.get("ExposureTime", 0),
                        "analogue_gain": round(md.get("AnalogueGain", 0.0), 2),
                        "lens_position": round(md.get("LensPosition", 0.0), 2),
                        "colour_temperature": md.get("ColourTemperature", 0),
                    },
                    "timestamp": time.time(),
                    "message": f"Test capture saved to {relative_path}",
                }
            )

        except Exception as camera_error:
            # Ensure camera is closed on error
            if picam2:
                try:
                    picam2.stop()
                    picam2.close()
                except Exception:
                    pass

            # Stream restart handled by finally block to avoid duplicate restarts
            raise camera_error

        finally:
            # Always restart stream if it was active (handles both success and error cases)
            if was_streaming and camera_streamer:
                print("Restarting camera stream after test capture...")
                try:
                    camera_streamer.start_streaming()
                except Exception as restart_error:
                    print(f"Warning: Failed to restart stream: {restart_error}")


@camera_bp.route("/test-capture-liveview", methods=["POST"])
def test_capture_liveview():
    """
    Capture a test photo using current live view settings

    Allows testing live view stream settings at full resolution without
    modifying camera_settings.csv. Uses liveview_settings.txt controls.

    Returns:
        JSON with:
        - success: bool
        - test_photo_path: str (relative path from PHOTOS_DIR)
        - settings_used: dict (controls that were applied)
        - settings_source: str ('live view')
        - metadata: dict (exposure, gain, lens position, color temp)
        - timestamp: float
    """
    try:
        from flask import current_app

        from mothbox_paths import LIVEVIEW_SETTINGS_FILE, get_control_values

        print("Test capture (live view settings) requested via API")

        # PRIMARY: Get settings from camera_streamer instance (live values)
        camera_streamer = current_app.config.get('CAMERA_STREAMER')
        if camera_streamer:
            print("Using live camera settings from camera_streamer instance")
            liveview_settings = camera_streamer.get_current_settings()
        else:
            # FALLBACK: Read from file when camera_streamer unavailable
            print("Falling back to liveview_settings.txt file")
            liveview_settings = {}
            if LIVEVIEW_SETTINGS_FILE.exists():
                liveview_settings = get_control_values(LIVEVIEW_SETTINGS_FILE)

        # Use centralized mapping from camera_control_mapping.py
        # This eliminates implicit snake_case → PascalCase conversion

        # Extract and convert settings with proper types
        settings = {}
        setting_keys = [
            "sharpness",
            "brightness",
            "contrast",
            "saturation",
            "af_mode",
            "af_speed",
            "af_range",
            "af_metering",
            "lens_position",
            "awb_enable",
            "awb_mode",
            "ae_enable",
            "ae_metering_mode",
            "exposure_time",
            "analogue_gain",
            "noise_reduction_mode",
            "colour_gains_red",
            "colour_gains_blue",
        ]

        for key in setting_keys:
            if key in liveview_settings:
                # If settings came from camera_streamer, they're already typed correctly
                # If from file, they need conversion from strings
                value = liveview_settings[key]
                if camera_streamer:
                    # Already correct type from get_current_settings()
                    settings[key] = value
                else:
                    # Convert from string (file format)
                    settings[key] = convert_from_settings_file(key, value)

        # Apply defaults for missing settings
        settings.setdefault("sharpness", 1.0)
        settings.setdefault("brightness", 0.0)
        settings.setdefault("contrast", 1.0)
        settings.setdefault("saturation", 1.0)
        settings.setdefault("af_mode", 2)
        settings.setdefault("af_speed", 0)
        settings.setdefault("af_range", 0)
        settings.setdefault("awb_enable", True)
        settings.setdefault("ae_enable", True)
        settings.setdefault("noise_reduction_mode", 2)

        # Extract awb_mode, lens_position, colour gains and exposure controls before building controls (they need special handling)
        awb_mode = settings.pop("awb_mode", None)
        lens_position = settings.pop("lens_position", None)
        colour_gains_red = settings.pop("colour_gains_red", None)
        colour_gains_blue = settings.pop("colour_gains_blue", None)
        exposure_time = settings.pop("exposure_time", None)
        analogue_gain = settings.pop("analogue_gain", None)

        # Build controls dict (handles case conversion and type validation)
        controls = build_picamera_controls(settings)

        # Only set AwbMode if AWB is disabled
        if not settings.get("awb_enable", True) and awb_mode is not None:
            controls["AwbMode"] = awb_mode

        # Handle colour gains tuple (only when AWB is disabled)
        # When AWB is enabled, manual ColourGains are ignored by the camera
        # ColourGains must be set as a tuple, not individual red/blue controls
        if not settings.get("awb_enable", True):
            if colour_gains_red is not None or colour_gains_blue is not None:
                red_gain = colour_gains_red if colour_gains_red is not None else DEFAULT_COLOUR_GAINS[0]
                blue_gain = colour_gains_blue if colour_gains_blue is not None else DEFAULT_COLOUR_GAINS[1]
                controls["ColourGains"] = (float(red_gain), float(blue_gain))

        # Only set manual exposure if AE disabled
        if not settings.get("ae_enable", True):
            if exposure_time is not None:
                controls["ExposureTime"] = int(exposure_time)
            if analogue_gain is not None:
                controls["AnalogueGain"] = float(analogue_gain)

        # Apply lens position if available (preserves focus across all AF modes)
        if lens_position is not None:
            controls["LensPosition"] = float(lens_position)

        return _execute_test_capture(controls, settings.get("af_mode", 2), "live view")

    except Exception as e:
        import traceback

        error_msg = str(e)
        print(f"Test capture (live view) error: {error_msg}")
        print(traceback.format_exc())
        return jsonify(
            {"success": False, "error": error_msg}
        ), 500


@camera_bp.route("/instant-capture", methods=["POST"])
def instant_capture():
    """
    Capture an instant photo using current live view settings

    Captures a photo immediately with current live view settings and saves it
    with instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg naming convention.
    Useful for quick snapshots without changing production settings.

    Returns:
        JSON with:
        - success: bool
        - test_photo_path: str (relative path from PHOTOS_DIR)
        - settings_used: dict (controls that were applied)
        - settings_source: str ('instant capture')
        - metadata: dict (exposure, gain, lens position, color temp)
        - timestamp: float
    """
    try:
        from datetime import datetime

        from flask import current_app

        print("Instant capture requested via API")

        # Get serial number for filename
        def get_serial_number():
            """Get Raspberry Pi serial number from /proc/cpuinfo"""
            try:
                with open("/proc/cpuinfo") as cpuinfo:
                    for line in cpuinfo:
                        if line.startswith("Serial"):
                            return line.split(":")[1].strip()
            except (OSError, IndexError):
                pass
            return "UNKNOWN"

        # PRIMARY: Get settings from camera_streamer instance (live values)
        camera_streamer = current_app.config.get('CAMERA_STREAMER')
        if not camera_streamer:
            return jsonify({
                "success": False,
                "error": "Camera streamer not initialized. Cannot capture instant photo."
            }), 500

        # Get current live view settings
        print("Using live camera settings from camera_streamer instance")
        liveview_settings = camera_streamer.get_current_settings()

        # Extract and build settings (same logic as test_capture_liveview)
        settings = {}
        setting_keys = [
            "sharpness",
            "brightness",
            "contrast",
            "saturation",
            "af_mode",
            "af_speed",
            "af_range",
            "af_metering",
            "lens_position",
            "awb_enable",
            "awb_mode",
            "ae_enable",
            "ae_metering_mode",
            "exposure_time",
            "analogue_gain",
            "noise_reduction_mode",
            "colour_gains_red",
            "colour_gains_blue",
        ]

        # Settings from camera_streamer are already typed correctly
        for key in setting_keys:
            if key in liveview_settings:
                settings[key] = liveview_settings[key]

        # Apply defaults for missing settings
        settings.setdefault("sharpness", 1.0)
        settings.setdefault("brightness", 0.0)
        settings.setdefault("contrast", 1.0)
        settings.setdefault("saturation", 1.0)
        settings.setdefault("af_mode", 2)
        settings.setdefault("af_speed", 0)
        settings.setdefault("af_range", 0)
        settings.setdefault("awb_enable", True)
        settings.setdefault("ae_enable", True)
        settings.setdefault("noise_reduction_mode", 2)

        # Extract special settings before building controls
        awb_mode = settings.pop("awb_mode", None)
        lens_position = settings.pop("lens_position", None)
        colour_gains_red = settings.pop("colour_gains_red", None)
        colour_gains_blue = settings.pop("colour_gains_blue", None)
        exposure_time = settings.pop("exposure_time", None)
        analogue_gain = settings.pop("analogue_gain", None)

        # Build controls dict
        controls = build_picamera_controls(settings)

        # Only set AwbMode if AWB is disabled
        if not settings.get("awb_enable", True) and awb_mode is not None:
            controls["AwbMode"] = awb_mode

        # Handle colour gains tuple (only when AWB is disabled)
        if not settings.get("awb_enable", True):
            if colour_gains_red is not None or colour_gains_blue is not None:
                red_gain = colour_gains_red if colour_gains_red is not None else DEFAULT_COLOUR_GAINS[0]
                blue_gain = colour_gains_blue if colour_gains_blue is not None else DEFAULT_COLOUR_GAINS[1]
                controls["ColourGains"] = (float(red_gain), float(blue_gain))

        # Only set manual exposure if AE disabled
        if not settings.get("ae_enable", True):
            if exposure_time is not None:
                controls["ExposureTime"] = int(exposure_time)
            if analogue_gain is not None:
                controls["AnalogueGain"] = float(analogue_gain)

        # Apply lens position if available (preserves focus across all AF modes)
        # When lens_position is set, force Manual AF mode to prevent autofocus from overriding it
        af_mode_for_capture = settings.get("af_mode", 2)
        if lens_position is not None:
            controls["LensPosition"] = float(lens_position)
            controls["AfMode"] = 0  # Force Manual AF to preserve lens position
            af_mode_for_capture = 0
            print(f"Preserving lens position {lens_position:.2f} - forcing Manual AF mode")

        # Generate instant capture filename: instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg
        timestamp = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
        serial = get_serial_number()
        filename = f"instant_{timestamp}_{serial}.jpg"

        return _execute_instant_capture(controls, af_mode_for_capture, "instant capture", filename)

    except Exception as e:
        import traceback

        error_msg = str(e)
        print(f"Instant capture error: {error_msg}")
        print(traceback.format_exc())
        return jsonify(
            {"success": False, "error": error_msg}
        ), 500


def _execute_instant_capture(settings_dict, af_mode, settings_source, filename):
    """
    Helper function to execute an instant capture with given settings and filename

    Similar to _execute_test_capture but uses a custom filename instead of
    generating timestamp-based name.

    Args:
        settings_dict: Dict of camera control values to apply
        af_mode: Autofocus mode (1=Auto, 2=Manual, 3=Continuous)
        settings_source: String describing source ('instant capture')
        filename: Custom filename for the capture

    Returns:
        tuple: (success_dict, status_code) or raises exception
    """
    # Reuse the existing _execute_test_capture logic but with custom filename
    # This is more maintainable than duplicating the entire capture logic
    import gc
    import time
    from datetime import datetime

    from flask import current_app

    from mothbox_paths import PHOTOS_DIR

    # Acquire operation lock to prevent concurrent camera access
    camera_streamer = current_app.config.get("CAMERA_STREAMER")
    if not camera_streamer:
        return jsonify({"success": False, "error": "Camera streamer not initialized"}), 500

    with camera_streamer.acquire_for_operation():
        # Release camera hardware if initialized (prevents resource conflict)
        was_streaming = False
        if camera_streamer.camera:
            print("Releasing camera hardware before instant capture...")
            was_streaming = camera_streamer.streaming
            camera_streamer.release_camera()
            time.sleep(0.5)  # Let camera fully release

        # Initialize camera for instant capture
        picam2 = None
        try:
            # Try camera 0 first with retry logic, fallback to camera 1
            try:
                picam2 = acquire_camera_with_retry(0)
            except Exception:
                picam2 = acquire_camera_with_retry(1)

            # Configure for high-resolution capture (same as test capture)
            # Note: Picamera2 "BGR888" outputs RGB byte order (counterintuitive naming)
            capture_config = picam2.create_still_configuration(
                main={
                    "size": TEST_CAPTURE_RESOLUTION,
                    "format": "BGR888",  # Outputs RGB-ordered bytes for PIL compatibility
                },
                raw=None,
                lores=None,
            )
            picam2.configure(capture_config)

            # Start camera
            picam2.start()

            # Apply controls using build_picamera_controls() to convert snake_case → PascalCase
            # This ensures camera accepts the control keys (e.g., af_mode → AfMode)
            controls = build_picamera_controls(settings_dict)

            picam2.set_controls(controls)
            print(f"Applied {settings_source} settings to instant capture: {controls}")

            # Wait for settings to stabilize
            time.sleep(0.5)

            # Trigger autofocus if in Auto mode (1) or Continuous mode (3)
            if af_mode in AF_MODES_REQUIRING_TRIGGER:
                print(f"Triggering autofocus (mode={af_mode})...")
                try:
                    picam2.autofocus_cycle()
                    # Wait for autofocus to complete
                    time.sleep(1.0)
                    print("Autofocus cycle completed")
                except Exception as af_error:
                    print(f"Warning: Autofocus cycle failed: {af_error}")
                    # Continue with capture even if AF fails
            else:
                # Manual focus mode - no autofocus trigger needed
                time.sleep(0.5)  # Additional stabilization time

            # Create test_captures directory
            test_dir = PHOTOS_DIR / "test_captures"
            test_dir.mkdir(parents=True, exist_ok=True)

            # Use provided filename
            filepath = test_dir / filename

            # Capture photo with rich EXIF metadata
            print(f"Capturing instant photo to: {filepath}")

            # Capture array and metadata
            array = picam2.capture_array("main")
            md = picam2.capture_metadata()

            # Build EXIF metadata using centralized helper
            from PIL import Image

            exif_bytes = _build_exif_metadata(md, settings_dict, "instant", picam2)

            # Save with EXIF metadata (Picamera2 BGR888 outputs RGB bytes - no conversion needed)
            img = Image.fromarray(array)
            img.save(str(filepath), quality=95, exif=exif_bytes)
            print(f"Instant photo saved successfully: {filepath}")

            # Get relative path from PHOTOS_DIR
            relative_path = filepath.relative_to(PHOTOS_DIR)

            # Return success response
            return jsonify(
                {
                    "success": True,
                    "photo_path": str(relative_path),
                    "settings_used": controls,
                    "settings_source": settings_source,
                    "metadata": {
                        "exposure_time": md.get("ExposureTime", 0),
                        "analogue_gain": md.get("AnalogueGain", 0.0),
                        "lens_position": md.get("LensPosition", 0.0),
                        "colour_temperature": md.get("ColourTemperature", 0),
                    },
                    "timestamp": time.time(),
                }
            ), 200

        except Exception as e:
            import traceback

            error_msg = str(e)
            print(f"Instant capture error: {error_msg}")
            print(traceback.format_exc())
            raise  # Re-raise to be caught by outer try/except

        finally:
            # Cleanup camera
            if picam2:
                try:
                    picam2.stop()
                    picam2.close()
                    print("Camera closed")
                except Exception as close_error:
                    print(f"Warning: Error closing camera: {close_error}")

                # Force garbage collection
                del picam2
                gc.collect()

            # Restart streaming if it was active
            if was_streaming and camera_streamer:
                print("Restarting camera stream after instant capture...")
                try:
                    camera_streamer.start_streaming()
                except Exception as restart_error:
                    print(f"Warning: Failed to restart stream: {restart_error}")


@camera_bp.route("/test-capture-photo", methods=["POST"])
def test_capture_photo():
    """
    Capture a test photo using current photo capture settings

    Allows testing photo capture settings at full resolution without
    actually triggering a production capture. Uses camera_settings.csv controls.

    Returns:
        JSON with:
        - success: bool
        - test_photo_path: str (relative path from PHOTOS_DIR)
        - settings_used: dict (controls that were applied)
        - settings_source: str ('photo capture')
        - metadata: dict (exposure, gain, lens position, color temp)
        - timestamp: float
    """
    try:
        import csv

        from mothbox_paths import CAMERA_SETTINGS_FILE

        print("Test capture (photo settings) requested via API")

        # Load photo capture settings from CSV
        photo_settings = {}
        if CAMERA_SETTINGS_FILE.exists():
            with open(CAMERA_SETTINGS_FILE) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Build settings dict from vertical CSV format (SETTING,VALUE,DETAILS)
                    setting_name = row["SETTING"].strip()
                    setting_value = row["VALUE"].strip()
                    photo_settings[setting_name] = setting_value

        # Build controls dict from photo capture settings
        controls = {}

        # Map CSV fields to Picamera2 controls
        if "Sharpness" in photo_settings:
            controls["Sharpness"] = float(photo_settings["Sharpness"])
        if "Brightness" in photo_settings:
            controls["Brightness"] = float(photo_settings["Brightness"])
        if "Contrast" in photo_settings:
            controls["Contrast"] = float(photo_settings["Contrast"])
        if "Saturation" in photo_settings:
            controls["Saturation"] = float(photo_settings["Saturation"])
        # Extract af_mode for autofocus trigger logic
        af_mode = 2  # Default to Manual (2)
        if "AfMode" in photo_settings:
            af_mode = int(photo_settings["AfMode"])
            controls["AfMode"] = af_mode
        if "AfSpeed" in photo_settings:
            controls["AfSpeed"] = int(photo_settings["AfSpeed"])
        if "AfRange" in photo_settings:
            controls["AfRange"] = int(photo_settings["AfRange"])
        if "ExposureTime" in photo_settings:
            controls["ExposureTime"] = int(photo_settings["ExposureTime"])
        if "AnalogueGain" in photo_settings:
            controls["AnalogueGain"] = float(photo_settings["AnalogueGain"])
        if "AeEnable" in photo_settings:
            controls["AeEnable"] = photo_settings["AeEnable"].lower() == "true"
        if "AwbEnable" in photo_settings:
            controls["AwbEnable"] = photo_settings["AwbEnable"].lower() == "true"
        if "AwbMode" in photo_settings and not controls.get("AwbEnable", True):
            controls["AwbMode"] = int(photo_settings["AwbMode"])

        return _execute_test_capture(controls, af_mode, "photo capture")

    except Exception as e:
        import traceback

        error_msg = str(e)
        print(f"Test capture (photo) error: {error_msg}")
        print(traceback.format_exc())
        return jsonify(
            {"success": False, "error": error_msg}
        ), 500
