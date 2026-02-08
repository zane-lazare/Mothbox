#!/usr/bin/python3
"""
Focus Bracketing Capture Script

Captures multiple photos at different focus positions for depth-of-field stacking.
Useful for macro/insect photography where achieving sharp focus across the entire
subject is challenging with a single image.
"""

# ============================================================================
# Imports
# ============================================================================

# Standard library
import csv
import os
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

# Third-party libraries
from picamera2 import Picamera2

# Mothbox modules - setup path first
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from mothbox_paths import CAMERA_SETTINGS_FILE, CONTROLS_FILE, PHOTOS_DIR, get_gpio_pins

# Import camera control mapping
sys.path.insert(0, str(Path(__file__).parent.parent))
from camera_control_mapping import build_picamera_controls

# ============================================================================
# Default Configuration (fallback values if not in CSV)
# ============================================================================

# Focus Bracketing Controls - these are overridden by CSV settings if present
num_steps = 5  # Number of focus positions to capture
focus_start = 2.0  # Starting focus position in diopters (farther)
focus_end = 8.0  # Ending focus position in diopters (closer/macro)

# Flash Timing Controls - overridden by CSV settings if present
flash_delay_before = 50  # Delay after flash on, before capture (milliseconds)
flash_delay_after = 0  # Delay after capture, before flash off (milliseconds)
focus_settle_delay = 500  # Delay for lens to settle after focus change (milliseconds)

# Colour Gains Controls - overridden by CSV settings if present
lock_colour_gains = 1  # 0=Use AWB, 1=Lock gains for consistency
colour_gain_red = 2.259439776  # Red channel gain (when locked)
colour_gain_blue = 1.500129925  # Blue channel gain (when locked)

computerName = "mothboxD"  # noqa: N816 - legacy Mothbox naming convention


def get_control_values(filepath):
    """Reads key-value pairs from the control file."""
    control_values = {}
    with open(filepath) as file:
        for line in file:
            key, value = line.strip().split("=")
            control_values[key] = value
    return control_values


# Application-level settings (not Picamera2 controls, but used by capture scripts)
APPLICATION_SETTINGS = {
    "Name",
    "HDR",
    "HDR_width",
    "AutoCalibration",
    "AutoCalibrationPeriod",
    "ImageFileType",
    "VerticalFlip",
}


def load_camera_settings():
    """
    Reads camera settings from a CSV file and converts them to appropriate data types.

    Args:
        filepath (str): Path to the CSV file containing camera settings.

    Returns:
        dict: Dictionary containing camera settings with converted data types.

    Raises:
        ValueError: If an invalid value is encountered in the CSV file.
    """

    # first look for any updated CSV files on external media, we will prioritize those
    external_media_paths = ("/media", "/mnt")  # Common external media mount points
    default_path = str(CAMERA_SETTINGS_FILE)
    file_path = default_path

    found = 0
    for path in external_media_paths:
        if found == 0:
            files = os.listdir(
                path
            )  # don't look for files recursively, only if new settings in top level
            if "camera_settings.csv" in files:
                file_path = os.path.join(path, "camera_settings.csv")
                print(f"Found settings on external media: {file_path}")
                found = 1
                break
            else:
                print("No external settings here...")
                file_path = default_path

    if found == 0:
        # redundant but being extra safe
        print("No external settings, using internal csv")
        file_path = default_path

    try:
        with open(file_path) as csv_file:
            reader = csv.DictReader(csv_file)
            camera_settings = {}
            for row in reader:
                setting, value = row["SETTING"], row["VALUE"]
                # Note: DETAILS column is ignored

                # Convert data types based on setting name (adjust as needed)
                if setting == "LensPosition":
                    try:
                        value = float(value)
                    except ValueError as err:
                        raise ValueError(f"Invalid value for LensPosition: {value}") from err
                elif setting == "AnalogueGain":
                    try:
                        value = float(value)
                    except ValueError as err:
                        raise ValueError(f"Invalid value for AnalogueGain: {value}") from err
                elif setting == "AeEnable" or setting == "AwbEnable":
                    value = value.lower() == "true"  # Convert to bool (adjust logic if needed)
                elif (
                    setting == "AwbMode"
                    or setting == "AfTrigger"
                    or setting == "AfRange"
                    or setting == "AfSpeed"
                    or setting == "AfMode"
                ):
                    value = int(value)
                    # value = getattr(controls.AwbModeEnum, value)  # Access enum value
                    # Assuming AwbMode is a string representing an enum value
                    # pass  # No conversion needed for string
                elif setting == "ExposureTime":
                    try:
                        value = int(value)
                    except ValueError as err:
                        raise ValueError(f"Invalid value for ExposureTime: {value}") from err
                elif setting == "FocusBracket":
                    try:
                        value = int(value)
                    except ValueError as err:
                        raise ValueError(f"Invalid value for FocusBracket: {value}") from err
                elif setting in [
                    "FocusBracket_Start",
                    "FocusBracket_End",
                    "FocusBracket_ColorGainRed",
                    "FocusBracket_ColorGainBlue",
                ]:
                    try:
                        value = float(value)
                    except ValueError as err:
                        raise ValueError(f"Invalid value for {setting}: {value}") from err
                elif setting in APPLICATION_SETTINGS:
                    pass  # Keep as string, application handles these
                else:
                    print(f"Warning: Unknown setting: {setting}. Ignoring.")

                camera_settings[setting] = value

        return camera_settings

    except FileNotFoundError:
        print(f"Error: CSV file not found: {file_path}")
        return None


def calculate_focus_positions(start, end, steps):
    """
    Calculate evenly-spaced focus positions for bracketing.

    Args:
        start: Starting focus position in diopters (0.0-10.0)
        end: Ending focus position in diopters (0.0-10.0)
        steps: Number of focus positions to generate (1-10)

    Returns:
        List of focus positions

    Raises:
        ValueError: If start/end are out of range (0-10 diopters) or steps is invalid
    """
    # Validate inputs
    if not isinstance(steps, int) or steps < 1 or steps > 10:
        raise ValueError(f"Steps must be an integer between 1 and 10, got: {steps}")

    if not (0.0 <= start <= 10.0):
        raise ValueError(f"Start position must be 0.0-10.0 diopters, got: {start}")

    if not (0.0 <= end <= 10.0):
        raise ValueError(f"End position must be 0.0-10.0 diopters, got: {end}")

    if steps == 1:
        # Single focus at the start position
        return [start]

    # Calculate evenly-spaced positions
    positions = []
    for i in range(steps):
        pos = start + i * (end - start) / (steps - 1)
        positions.append(pos)

    return positions


def takePhoto_FocusBracket(  # noqa: N802 - legacy Mothbox naming convention
    picam2,
    camera_settings,
    num_steps,
    focus_start,
    focus_end,
    focus_settle_delay,
    flash_delay_before,
    flash_delay_after,
    lock_colour_gains,
    colour_gain_red,
    colour_gain_blue,
    onlyflash,
    computerName,  # noqa: N803 - legacy Mothbox naming convention
    gpio_handler,
):
    """
    Capture multiple photos at different focus positions (focus bracketing)

    Args:
        picam2: Initialized Picamera2 instance
        camera_settings: Dictionary of camera settings to apply
        num_steps: Number of focus positions to capture
        focus_start: Starting focus position in diopters
        focus_end: Ending focus position in diopters
        focus_settle_delay: Delay in ms for lens to settle
        flash_delay_before: Delay in ms before capture
        flash_delay_after: Delay in ms after capture
        lock_colour_gains: Whether to lock color gains (0 or 1)
        colour_gain_red: Red channel gain value
        colour_gain_blue: Blue channel gain value
        onlyflash: Whether flash is always on
        computerName: Name of the computer for file naming
        gpio_handler: GPIOHandler instance for flash control
    """
    now = datetime.now()
    timestamp = now.strftime("%Y_%m_%d__%H_%M_%S_%f")

    # Apply camera settings
    if camera_settings:
        picam2.set_controls(camera_settings)
    else:
        print("can't set controls")

    # Apply color gains based on lock setting
    if lock_colour_gains:
        # Lock colour gains for consistency across focus stack
        # This ensures uniform colour when images are combined in stacking software
        cgains = (colour_gain_red, colour_gain_blue)
        # Use centralized mapping
        picam2.set_controls(build_picamera_controls({"colour_gains": cgains}))
        print(f"Color gains locked at R={colour_gain_red:.3f}, B={colour_gain_blue:.3f}")
    else:
        # Use auto white balance - each image may vary slightly based on lighting
        print("Using auto white balance (color may vary across stack)")

    # Calculate focus positions
    focus_positions = calculate_focus_positions(focus_start, focus_end, num_steps)
    print(f"Focus bracket positions (diopters): {focus_positions}")

    time.sleep(5)
    picam2.start()

    time.sleep(5)

    start_time = time.time()

    if num_steps > 1:
        print(f"About to take Focus Bracket photo ({num_steps} steps): {timestamp}")
    else:
        print(f"About to take single focus photo: {timestamp}")

    # Focus bracketing loop
    for i, focus_pos in enumerate(focus_positions):
        step_num = i + 1
        progress_pct = int((step_num / num_steps) * 100)

        # Progress: Starting this focus step
        print(
            f"FOCUS_BRACKET_PROGRESS: {progress_pct}% - Step {step_num}/{num_steps}: Setting focus to {focus_pos:.2f} diopters"
        )

        # Set focus position (manual mode)
        # Use centralized mapping
        picam2.set_controls(build_picamera_controls({"lens_position": focus_pos, "af_mode": 0}))
        print(f"Focus position set: {focus_pos:.2f} diopters (step {step_num}/{num_steps})")

        # Wait for lens to settle after focus change (convert ms to seconds)
        print(f"Waiting {focus_settle_delay}ms for lens to settle...")
        time.sleep(focus_settle_delay / 1000.0)

        # Turn on flash
        gpio_handler.flash_on()

        # Wait for flash to reach full brightness (convert ms to seconds)
        if flash_delay_before > 0:
            print(f"Waiting {flash_delay_before}ms for flash to reach full brightness...")
            time.sleep(flash_delay_before / 1000.0)

        # Capture the image
        print(f"Capturing image at focus position {focus_pos:.2f} diopters...")
        request = picam2.capture_request(flush=True)

        # Optional delay after capture before turning off flash (convert ms to seconds)
        if flash_delay_after > 0:
            time.sleep(flash_delay_after / 1000.0)

        # Turn off flash (unless in always-on mode)
        if not onlyflash:
            gpio_handler.flash_off()

        capture_time = time.time() - start_time
        print(f"Picture capture time: {capture_time:.2f}s")

        # Save the image with focus bracket suffix
        folder_path = str(PHOTOS_DIR) + "/"
        filepath = folder_path + f"ManFocus_{computerName}_{timestamp}_FB{i}.jpg"

        request.save("main", filepath)
        print(f"Image saved to {filepath}")
        request.release()

        print(
            f"FOCUS_BRACKET_PROGRESS: {progress_pct}% - Completed step {step_num}/{num_steps} at {focus_pos:.2f} diopters"
        )
        print(f"Captured focus bracket {step_num}/{num_steps} at {focus_pos:.2f} diopters\n")


class GPIOHandler:
    """
    Wrapper for GPIO operations with relay pin management.

    This class encapsulates all GPIO interactions and makes the relay pins
    explicit dependencies instead of relying on scoping.

    Args:
        gpio_module: The RPi.GPIO module (or mock for testing)
        relay_ch1: GPIO pin number for relay channel 1
        relay_ch2: GPIO pin number for relay channel 2
        relay_ch3: GPIO pin number for relay channel 3
    """

    def __init__(self, gpio_module, relay_ch1, relay_ch2, relay_ch3):
        self.gpio = gpio_module
        self.relay_ch1 = relay_ch1
        self.relay_ch2 = relay_ch2
        self.relay_ch3 = relay_ch3

    def setup(self):
        """Initialize GPIO pins for output using polarity-aware helpers"""
        from lib.gpio_helpers import setup_relay

        self.gpio.setwarnings(False)
        self.gpio.setmode(self.gpio.BCM)
        setup_relay(self.relay_ch1)
        setup_relay(self.relay_ch2)
        setup_relay(self.relay_ch3)

    def flash_on(self):
        """Turn flash on (Relay Ch2) using polarity-aware helper"""
        from lib.gpio_helpers import relay_on

        relay_on(self.relay_ch2)
        print("Flash On\n")

    def flash_off(self):
        """Turn flash off (Relay Ch2) using polarity-aware helper"""
        from lib.gpio_helpers import relay_off

        relay_off(self.relay_ch2)
        print("Flash Off\n")


def _detect_platform():
    """
    Detect platform and extract computer name.

    Extracted as a separate function for easier testing.

    Returns:
        tuple: (system_name, computer_name)
    """
    if platform.system() == "Windows":
        return "Windows", platform.uname().node
    else:
        return "Linux", os.uname()[1]


def main(gpio_handler_factory=None, camera_factory=None, settings_loader=None, quit_func=None):
    """
    Main execution function with dependency injection for testability.

    Args:
        gpio_handler_factory: Callable() -> GPIOHandler instance
                             Default: Creates real GPIOHandler with RPi.GPIO
        camera_factory: Callable() -> Picamera2 instance
                       Default: Picamera2 constructor
        settings_loader: Callable() -> dict of camera settings
                        Default: load_camera_settings function
        quit_func: Callable() -> None to exit program
                  Default: built-in quit() function

    Returns:
        None (calls quit_func at end)
    """
    global computerName

    # ============================================================================
    # Dependency Injection - Create default dependencies if not provided
    # ============================================================================

    if gpio_handler_factory is None:
        # Create default GPIO handler factory
        import RPi.GPIO as GPIO_module  # noqa: N811 - module alias for dependency injection

        pins = get_gpio_pins()

        def gpio_handler_factory():
            return GPIOHandler(GPIO_module, pins["Relay_Ch1"], pins["Relay_Ch2"], pins["Relay_Ch3"])

    if camera_factory is None:
        # Use real Picamera2
        camera_factory = Picamera2

    if settings_loader is None:
        # Use real settings loader
        settings_loader = load_camera_settings

    if quit_func is None:
        # Use built-in quit
        quit_func = quit

    # ============================================================================
    # Main Execution
    # ============================================================================

    print("----------------- STARTING TAKEPHOTO FOCUS BRACKET -------------------")
    now = datetime.now()
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Current time: {formatted_time}")

    # System Detection
    system, computerName = _detect_platform()
    print(computerName)

    # GPIO Setup
    gpio_handler = gpio_handler_factory()
    gpio_handler.setup()
    print("Setup The Relay Module is [success]")

    # Load configuration
    control_values = get_control_values(str(CONTROLS_FILE))
    onlyflash = control_values.get("OnlyFlash", "True").lower() == "true"
    if onlyflash:
        print("operating in always on flash mode")

    # Camera initialization
    picam2 = camera_factory()

    capture_main = {"size": (9000, 6000), "format": "RGB888"}
    capture_config = picam2.create_still_configuration(main=capture_main)
    picam2.configure(capture_config)

    """
    #This is for getting min and max details for certain settings, (See the picam pdf manual)
    print(picam2.camera_controls["AnalogueGain"])
    min_gain, max_gain, default_gain = picam2.camera_controls["AnalogueGain"]
    """
    camera_settings = settings_loader()

    # Extract focus bracketing settings (using module-level defaults)
    _num_steps = int(camera_settings.pop("FocusBracket", num_steps))
    _focus_start = float(camera_settings.pop("FocusBracket_Start", focus_start))
    _focus_end = float(camera_settings.pop("FocusBracket_End", focus_end))

    # Extract flash timing settings (in milliseconds)
    _flash_delay_before = int(camera_settings.pop("FlashDelay_BeforeCapture", flash_delay_before))
    _flash_delay_after = int(camera_settings.pop("FlashDelay_AfterCapture", flash_delay_after))
    _focus_settle_delay = int(camera_settings.pop("FocusBracket_SettleDelay", focus_settle_delay))

    # Extract color gains settings
    _lock_colour_gains = int(camera_settings.pop("FocusBracket_LockColorGains", lock_colour_gains))
    _colour_gain_red = float(camera_settings.pop("FocusBracket_ColorGainRed", colour_gain_red))
    _colour_gain_blue = float(camera_settings.pop("FocusBracket_ColorGainBlue", colour_gain_blue))

    # Validate focus bracket settings
    if _num_steps < 1:
        _num_steps = 1
        print(f"Warning: Invalid FocusBracket value, defaulting to {_num_steps}")

    if _focus_start < 0.0 or _focus_start > 10.0:
        _focus_start = 2.0
        print(f"Warning: Invalid FocusBracket_Start, defaulting to {_focus_start}")

    if _focus_end < 0.0 or _focus_end > 10.0:
        _focus_end = 8.0
        print(f"Warning: Invalid FocusBracket_End, defaulting to {_focus_end}")

    # Ensure start and end are different for multiple steps
    if _num_steps > 1 and abs(_focus_end - _focus_start) < 0.1:
        print("Warning: FocusBracket_Start and FocusBracket_End are too close. Adjusting...")
        _focus_end = _focus_start + 2.0
        if _focus_end > 10.0:
            _focus_end = 10.0
            _focus_start = 8.0

    # Validate timing settings
    if _flash_delay_before < 0 or _flash_delay_before > 500:
        _flash_delay_before = 50
        print(f"Warning: Invalid FlashDelay_BeforeCapture, defaulting to {_flash_delay_before}ms")

    if _flash_delay_after < 0 or _flash_delay_after > 500:
        _flash_delay_after = 0
        print(f"Warning: Invalid FlashDelay_AfterCapture, defaulting to {_flash_delay_after}ms")

    if _focus_settle_delay < 100 or _focus_settle_delay > 2000:
        _focus_settle_delay = 500
        print(f"Warning: Invalid FocusBracket_SettleDelay, defaulting to {_focus_settle_delay}ms")

    # Validate color gains
    if _lock_colour_gains not in [0, 1]:
        _lock_colour_gains = 1
        print(f"Warning: Invalid FocusBracket_LockColorGains, defaulting to {_lock_colour_gains}")

    if _colour_gain_red < 1.0 or _colour_gain_red > 4.0:
        _colour_gain_red = 2.259439776
        print(f"Warning: Invalid FocusBracket_ColorGainRed, defaulting to {_colour_gain_red}")

    if _colour_gain_blue < 1.0 or _colour_gain_blue > 4.0:
        _colour_gain_blue = 1.500129925
        print(f"Warning: Invalid FocusBracket_ColorGainBlue, defaulting to {_colour_gain_blue}")

    # Log the configuration being used
    print("Focus bracket configuration:")
    print(f"  Steps: {_num_steps}, Range: {_focus_start} to {_focus_end} diopters")
    print(f"  Flash delays: {_flash_delay_before}ms before, {_flash_delay_after}ms after")
    print(f"  Lens settle delay: {_focus_settle_delay}ms")
    if _lock_colour_gains:
        print(f"  Color gains locked: R={_colour_gain_red:.3f}, B={_colour_gain_blue:.3f}")
    else:
        print("  Using auto white balance (AWB)")

    if camera_settings:
        picam2.set_controls(camera_settings)

    picam2.start()
    time.sleep(0.1)

    print("cam started")

    picam2.stop()
    picam2.configure(capture_config)

    # Execute focus bracket capture
    time.sleep(0.5)
    takePhoto_FocusBracket(
        picam2,
        camera_settings,
        _num_steps,
        _focus_start,
        _focus_end,
        _focus_settle_delay,
        _flash_delay_before,
        _flash_delay_after,
        _lock_colour_gains,
        _colour_gain_red,
        _colour_gain_blue,
        onlyflash,
        computerName,
        gpio_handler,
    )

    picam2.stop()

    quit_func()


if __name__ == "__main__":
    main()
