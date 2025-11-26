"""
Centralized constants for the webui backend.

This module consolidates magic numbers and configuration values
scattered throughout the codebase into named constants for
better maintainability and self-documentation.
"""
from typing import Final

# =============================================================================
# STREAM DEFAULTS (liveview_stream.py already has these - just re-export)
# =============================================================================
DEFAULT_STREAM_WIDTH: Final[int] = 1024
DEFAULT_STREAM_HEIGHT: Final[int] = 768
DEFAULT_FRAME_DELAY: Final[float] = 0.1  # 10 FPS
DEFAULT_JPEG_QUALITY: Final[int] = 85

# =============================================================================
# CAMERA OPERATION TIMEOUTS
# =============================================================================
CAMERA_RELEASE_WAIT_SECONDS: Final[float] = 1.5
CAMERA_RELEASE_STABILIZE_SECONDS: Final[float] = 0.5
CAMERA_STABILIZE_BEFORE_AF_SECONDS: Final[float] = 0.3
AUTOFOCUS_COMPLETION_WAIT_SECONDS: Final[float] = 1.0
SUBPROCESS_TIMEOUT_SECONDS: Final[int] = 30
CAMERA_ACQUIRE_MAX_RETRIES: Final[int] = 3
CAMERA_ACQUIRE_WAIT_SECONDS: Final[float] = 2.0

# =============================================================================
# HDR CAPTURE SETTINGS
# =============================================================================
HDR_DEFAULT_WIDTH_US: Final[int] = 7000  # microseconds
HDR_MIN_WIDTH_US: Final[int] = 1000
HDR_MAX_WIDTH_US: Final[int] = 50000
HDR_VALID_COUNTS: Final[tuple[int, ...]] = (1, 3, 5, 7)

# =============================================================================
# FOCUS BRACKET SETTINGS
# =============================================================================
FB_DEFAULT_START_DIOPTERS: Final[float] = 2.0
FB_DEFAULT_END_DIOPTERS: Final[float] = 8.0
FB_MIN_STEPS: Final[int] = 1
FB_MAX_STEPS: Final[int] = 10
FB_MIN_DIOPTERS: Final[float] = 0.0
FB_MAX_DIOPTERS: Final[float] = 10.0

# =============================================================================
# HARDWARE MJPEG ENCODER (QP formula: qp = QP_MAX - (quality * QP_FACTOR))
# =============================================================================
MJPEG_QP_MAX: Final[int] = 25
MJPEG_QP_MIN: Final[int] = 1
MJPEG_QUALITY_TO_QP_FACTOR: Final[float] = 0.24

# =============================================================================
# CAMERA DEFAULT CONTROLS
# =============================================================================
DEFAULT_COLOUR_GAINS: Final[tuple[float, float]] = (2.259, 1.5)  # red, blue
AF_INITIAL_LENS_POSITION: Final[float] = 7.0
AF_PREVIEW_RESOLUTION: Final[tuple[int, int]] = (1920, 1080)
TEST_CAPTURE_RESOLUTION: Final[tuple[int, int]] = (3840, 2160)

# =============================================================================
# AF MODE CONSTANTS
# =============================================================================
AF_MODE_MANUAL: Final[int] = 0
AF_MODE_AUTO: Final[int] = 1
AF_MODE_CONTINUOUS: Final[int] = 2
AF_MODES_REQUIRING_TRIGGER: Final[tuple[int, ...]] = (AF_MODE_AUTO, AF_MODE_CONTINUOUS)

# =============================================================================
# FOCUS PEAKING PARAMETERS
# =============================================================================
FOCUS_PEAKING_INTENSITY_MIN: Final[int] = 50
FOCUS_PEAKING_INTENSITY_MAX: Final[int] = 200
FOCUS_PEAKING_BLEND_ALPHA: Final[float] = 0.6
EDGE_DETECTION_THRESHOLD_BASE: Final[int] = 250

# =============================================================================
# ZOOM LIMITS
# =============================================================================
ZOOM_LEVEL_MIN: Final[float] = 1.0
ZOOM_LEVEL_MAX: Final[float] = 10.0

# =============================================================================
# CALIBRATION PROGRESS
# =============================================================================
CALIBRATION_TOTAL_STEPS: Final[int] = 4

# =============================================================================
# CAMERA HARDWARE IDENTIFICATION (for EXIF metadata)
# =============================================================================
CAMERA_MAKE: Final[str] = "Arducam"
CAMERA_MODEL: Final[str] = "OwlSight 64MP"
