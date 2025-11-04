"""
Python equivalents of install_mothbox.sh functions for integration testing.

HYBRID TESTING STRATEGY:
========================
This module follows the established pattern in the Mothbox codebase:
- Simple validation functions: Test bash directly (test_validation.sh approach)
- Complex installer logic: Python equivalents here (easier mocking, like routes/config.py)
- Integration: subprocess.run() calls actual bash installer

Successfully Proven Patterns:
- routes/config.py (Production config utilities with validation and backup)
- test_validation.sh (bash direct testing, 44 tests passing)

These functions replicate the behavior of bash installer functions to enable
proper unit testing without executing bash scripts. Each function includes
references to the original bash implementation line numbers for traceability.

Design: Keep 1:1 correspondence with bash functions where possible. If behavior
diverges, document why and maintain bash source references.

Module: Tests/integration/installer_helpers.py
Related: install_mothbox.sh, mothbox_paths.py, routes/config.py
Issue: #13  - Installer Integration Tests
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any, Callable, Optional
import fcntl
import errno
import os


def update_or_add_config(file_path: Path, key: str, value: str) -> None:
    """
    Python equivalent of bash update_or_add_config function.

    Bash source: install_mothbox.sh lines 942-956

    Bash implementation:
        if grep -q "^${key}=" "$file" 2>/dev/null; then
            sudo sed -i "s|^${key}=.*|${key}=${value}|" "$file"
        else
            echo "${key}=${value}" | sudo tee -a "$file" > /dev/null
        fi

    If key exists in file, update its value.
    If key doesn't exist, append key=value.

    Behavior notes:
    - Uses ^ anchor to match start of line (prevents partial matches)
    - Replaces entire line if key found
    - Appends with newline if key not found
    - Does NOT use sudo (tests use tmp_path, sudo mocked separately)

    Args:
        file_path: Path to controls.txt or other config file
        key: Configuration key (e.g., 'Relay_Ch1', 'relay_enabled')
        value: Configuration value (e.g., '26', 'true', '/dev/ttyAMA0')

    Example:
        >>> controls = Path('/tmp/controls.txt')
        >>> controls.write_text("Relay_Ch1=26\\n")
        >>> update_or_add_config(controls, "Relay_Ch1", "5")
        >>> controls.read_text()
        'Relay_Ch1=5\\n'

        >>> update_or_add_config(controls, "Relay_Ch2", "19")
        >>> controls.read_text()
        'Relay_Ch1=5\\nRelay_Ch2=19\\n'
    """
    lines = []
    key_found = False

    if file_path.exists():
        lines = file_path.read_text().splitlines()

    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            key_found = True
        else:
            new_lines.append(line)

    if not key_found:
        new_lines.append(f"{key}={value}")

    # Write with trailing newline (matches bash behavior)
    file_path.write_text('\n'.join(new_lines) + '\n')


def parse_controls_file(file_path: Path) -> Dict[str, str]:
    """
    Parse controls.txt into dictionary.

    Matches: mothbox_paths.py get_control_values() lines 108-129

    Python implementation it matches:
        with open(filename, "r") as file:
            for line in file:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split("=", 1)
                    control_values[key.strip()] = value.strip()

    Format: key=value pairs, one per line
    - Comments start with #
    - Blank lines ignored
    - Whitespace stripped from keys and values
    - maxsplit=1 preserves '=' in values

    Args:
        file_path: Path to controls.txt

    Returns:
        Dict of key-value pairs (all strings)

    Example:
        >>> controls = Path('/tmp/controls.txt')
        >>> controls.write_text("# Comment\\nRelay_Ch1=26\\nname=mothbox\\n")
        >>> parse_controls_file(controls)
        {'Relay_Ch1': '26', 'name': 'mothbox'}
    """
    config = {}

    if not file_path.exists():
        return config

    for line in file_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            config[key.strip()] = value.strip()

    return config


def get_firmware_defaults(firmware_version: str) -> Dict[str, int]:
    """
    Return firmware-specific GPIO defaults.

    Bash source: install_mothbox.sh lines 347-356

    Bash implementation:
        if [ "$FIRMWARE_VERSION" = "4" ]; then
            DEFAULT_CH1=26
            DEFAULT_CH2=20
            DEFAULT_CH3=21
        else
            DEFAULT_CH1=5
            DEFAULT_CH2=19
            DEFAULT_CH3=9
        fi

    Firmware version determines relay GPIO pin defaults:
    - 4.x firmware: Pins 26, 20, 21 (Pi 4 hardware)
    - 5.x firmware: Pins 5, 19, 9 (Pi 5 hardware)

    Args:
        firmware_version: "4" or "5" (major version)

    Returns:
        Dict with Relay_Ch1, Relay_Ch2, Relay_Ch3 defaults

    Example:
        >>> get_firmware_defaults("4")
        {'Relay_Ch1': 26, 'Relay_Ch2': 20, 'Relay_Ch3': 21}

        >>> get_firmware_defaults("5")
        {'Relay_Ch1': 5, 'Relay_Ch2': 19, 'Relay_Ch3': 9}
    """
    if firmware_version == "4":
        return {
            'Relay_Ch1': 26,
            'Relay_Ch2': 20,
            'Relay_Ch3': 21
        }
    else:  # 5.x or any other version defaults to 5.x
        return {
            'Relay_Ch1': 5,
            'Relay_Ch2': 19,
            'Relay_Ch3': 9
        }


def simulate_quick_install(
    firmware_version: str,
    install_type: str,
    base_path: Path
) -> Dict[str, Any]:
    """
    Simulate --quick mode installation.

    Bash source: install_mothbox.sh lines 358-384 (quick mode defaults)
    Bash source: install_mothbox.sh lines 1028-1050 (config write)

    Quick mode behavior:
    - Standard modules enabled: relay, INA260, epaper, GPS
    - Optional modules disabled: light_sensor, PCA9536, multiplexer
    - Firmware-specific GPIO defaults applied
    - All 32 hardware configuration keys written

    Installation types:
    1. "legacy" - /home/pi/Desktop/Mothbox (all files in one place)
    2. "production" - FHS-compliant:
       - /opt/mothbox - Firmware code
       - /etc/mothbox - Configuration (controls.txt)
       - /var/lib/mothbox - Data
    3. "custom" - User-specified path (all files in custom location)

    Args:
        firmware_version: "4" or "5"
        install_type: "legacy", "production", or "custom"
        base_path: Base directory for installation (tmp_path in tests)

    Returns:
        Dict with:
            - mothbox_home: Path to main installation
            - config_dir: Path to configuration directory
            - data_dir: Path to data directory
            - controls_file: Path to controls.txt
            - config: Dict of written configuration

    Example:
        >>> result = simulate_quick_install("5", "production", Path("/tmp/test"))
        >>> result['controls_file'].exists()
        True
        >>> config = parse_controls_file(result['controls_file'])
        >>> config['Relay_Ch1']
        '5'
        >>> config['relay_enabled']
        'true'
    """
    # Determine directory structure based on install type
    if install_type == "legacy":
        mothbox_home = base_path / "home" / "pi" / "Desktop" / "Mothbox"
        config_dir = mothbox_home
        data_dir = mothbox_home
    elif install_type == "production":
        mothbox_home = base_path / "opt" / "mothbox"
        config_dir = base_path / "etc" / "mothbox"
        data_dir = base_path / "var" / "lib" / "mothbox"
    else:  # custom
        mothbox_home = base_path / "custom" / "mothbox"
        config_dir = mothbox_home
        data_dir = mothbox_home

    # Create directory structure
    mothbox_home.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create firmware directories
    (mothbox_home / f"{firmware_version}.x").mkdir(exist_ok=True)

    # Create controls.txt with quick mode defaults
    controls_file = config_dir / "controls.txt"

    # Get firmware-specific GPIO defaults
    gpio_defaults = get_firmware_defaults(firmware_version)

    # Quick mode configuration (lines 358-384)
    # Standard modules enabled, optional modules disabled
    config = {
        'softwareversion': f'{firmware_version}.0.0',
        'Relay_Ch1': str(gpio_defaults['Relay_Ch1']),
        'Relay_Ch2': str(gpio_defaults['Relay_Ch2']),
        'Relay_Ch3': str(gpio_defaults['Relay_Ch3']),
        'relay_enabled': 'true',
        'ina260_enabled': 'true',
        'ina260_address': '0x40',
        'epaper_enabled': 'true',
        'epaper_rst_pin': '17',
        'epaper_dc_pin': '25',
        'epaper_cs_pin': '8',
        'epaper_busy_pin': '24',
        'epaper_pwr_pin': '18',
        'gps_enabled': 'true',
        'gps_device': '/dev/ttyAMA0',
        'gps_baudrate': '9600',
        'gps_timeout': '60',
        'gps_read_timeout': '10',
        'gps_init_timeout': '30',
        'gps_fix_timeout': '180',
        'gps_retry_timeout': '5',
        'light_sensor_enabled': 'false',
        'light_sensor_type': 'LTR303',
        'light_sensor_address': '0x29',
        'pca9536_enabled': 'false',
        'pca9536_address': '0x21',
        'mux_enabled': 'false',
        'mux_type': 'i2c',
        'mux_address': '0x20',
        'mux_en_a': '31',
        'mux_en_b': '29',
        'mux_s0': '33',
        'mux_s1': '13',
        'mux_s2': '12',
        'mux_s3': '15',
        'mux_sig': '36',
    }

    # Write configuration to controls.txt
    with controls_file.open('w') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")

    return {
        'mothbox_home': mothbox_home,
        'config_dir': config_dir,
        'data_dir': data_dir,
        'controls_file': controls_file,
        'config': config
    }


def validate_controls_content(
    controls_path: Path,
    expected_keys: List[str]
) -> Tuple[bool, List[str]]:
    """
    Validate controls.txt has all expected keys.

    Helper function for test assertions - not in bash installer.

    Useful for verifying installation completeness:
    - Quick mode wrote all required keys
    - Firmware migration preserved all keys
    - Config updates didn't delete keys

    Args:
        controls_path: Path to controls.txt
        expected_keys: List of required keys (e.g., ['Relay_Ch1', 'relay_enabled'])

    Returns:
        Tuple of (success: bool, missing_keys: List[str])
        - success: True if all keys present
        - missing_keys: List of keys not found (empty if success)

    Example:
        >>> controls = Path('/tmp/controls.txt')
        >>> controls.write_text("Relay_Ch1=5\\nrelay_enabled=true\\n")
        >>> validate_controls_content(controls, ['Relay_Ch1', 'relay_enabled'])
        (True, [])

        >>> validate_controls_content(controls, ['Relay_Ch1', 'Relay_Ch2'])
        (False, ['Relay_Ch2'])
    """
    if not controls_path.exists():
        return False, expected_keys

    config = parse_controls_file(controls_path)
    missing_keys = [key for key in expected_keys if key not in config]

    return len(missing_keys) == 0, missing_keys


def simulate_file_lock_operation(
    file_path: Path,
    operation: Callable[[], None],
    timeout: int = 10
) -> bool:
    """
    Simulate file locking during config update.

    Bash source: install_mothbox.sh lines 924-940 (update_controls_atomic)

    Bash implementation:
        update_controls_atomic() {
            local lockfile="${CONTROLS_FILE}.lock"
            (
                flock -x -w 10 200 || {
                    echo "Failed to acquire lock"
                    return 1
                }
                "$@"
            ) 200>"$lockfile"
        }

    Uses fcntl.flock() for exclusive file locking (POSIX standard).

    Lock behavior:
    - Exclusive lock (LOCK_EX) - only one writer at a time
    - Non-blocking (LOCK_NB) - fails immediately if lock held
    - Lock file: file_path.lock
    - Cleanup: Lock file removed after operation

    Args:
        file_path: Path to file to lock
        operation: Callable to execute while holding lock
        timeout: Lock timeout in seconds (not implemented - uses non-blocking)

    Returns:
        True if operation succeeded, False if lock failed

    Raises:
        Any exception raised by operation() is propagated after releasing lock

    Example:
        >>> controls = Path('/tmp/controls.txt')
        >>> controls.write_text("test=1\\n")
        >>>
        >>> def update():
        ...     data = controls.read_text()
        ...     controls.write_text(data + "new=2\\n")
        >>>
        >>> simulate_file_lock_operation(controls, update)
        True
        >>> controls.read_text()
        'test=1\\nnew=2\\n'
    """
    lockfile = Path(str(file_path) + ".lock")

    try:
        # Create/open lock file
        with lockfile.open('w') as lock:
            try:
                # Acquire exclusive lock (non-blocking)
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                # Execute operation while holding lock
                operation()

                # Release lock
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

                return True

            except BlockingIOError:
                # Lock already held by another process/thread
                return False

            except Exception as e:
                # Release lock before propagating exception
                try:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                except:
                    pass
                raise e

    finally:
        # Cleanup: Remove lock file
        if lockfile.exists():
            try:
                lockfile.unlink()
            except OSError:
                pass  # Best effort cleanup


def mock_sudo_call(cmd: List[str], check_only: bool = False) -> Dict[str, Any]:
    """
    Mock sudo command calls for testing.

    Helper function for test fixtures - not in bash installer.

    Installer uses sudo for file operations:
    - sudo sed -i "s|^key=.*|key=value|" /etc/mothbox/controls.txt
    - echo "key=value" | sudo tee -a /etc/mothbox/controls.txt

    This function mocks sudo calls without actually executing them,
    allowing tests to verify correct command structure.

    Args:
        cmd: Command list (e.g., ['sudo', 'sed', '-i', ...])
        check_only: If True, only validate command structure, don't mock execution

    Returns:
        Dict with:
            - is_sudo: bool - Command starts with 'sudo'
            - actual_cmd: List[str] - Command without 'sudo' prefix
            - operation: str - Type of operation ('sed', 'tee', 'other')
            - mocked_result: MagicMock - Mocked subprocess result

    Example:
        >>> cmd = ['sudo', 'sed', '-i', 's|^Relay_Ch1=.*|Relay_Ch1=5|', '/tmp/controls.txt']
        >>> result = mock_sudo_call(cmd)
        >>> result['is_sudo']
        True
        >>> result['operation']
        'sed'
        >>> result['mocked_result'].returncode
        0
    """
    from unittest.mock import MagicMock

    is_sudo = len(cmd) > 0 and cmd[0] == 'sudo'
    actual_cmd = cmd[1:] if is_sudo else cmd

    # Determine operation type
    operation = 'other'
    if len(actual_cmd) > 0:
        if actual_cmd[0] == 'sed':
            operation = 'sed'
        elif actual_cmd[0] == 'tee':
            operation = 'tee'

    # Create mocked result
    mocked_result = MagicMock()
    mocked_result.returncode = 0
    mocked_result.stdout = ''
    mocked_result.stderr = ''

    return {
        'is_sudo': is_sudo,
        'actual_cmd': actual_cmd,
        'operation': operation,
        'mocked_result': mocked_result
    }
