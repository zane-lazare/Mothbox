"""
Unit tests for check_and_run.py pre-condition wrapper (Issue #311).

Tests the CLI wrapper script that checks sensor conditions before executing
scheduled actions. Used by cron_bridge.py to gate action execution based
on sensor readings.

Test structure:
- TestParseArgs (6 tests): Argument parsing
- TestCheckAndRun (10 tests): Core condition checking and execution
- TestEdgeCases (3 tests): Edge cases (zero, large values, special chars)
- TestMain (2 tests): Main entry point
- TestLogging (3 tests): Logging behavior
- TestIntegration (3 tests): Integration with cron_bridge

Total: 27 tests (covering all acceptance criteria)
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add firmware root to path for imports
_tests_dir = Path(__file__).resolve().parent.parent
_firmware_root = _tests_dir.parent
if str(_firmware_root) not in sys.path:
    sys.path.insert(0, str(_firmware_root))

from check_and_run import (
    EXIT_CONDITION_NOT_MET,
    EXIT_CONFIG_ERROR,
    EXIT_SENSOR_UNAVAILABLE,
    EXIT_SUCCESS,
    OP_SYMBOLS,
    check_and_run,
    main,
    parse_args,
    setup_logging,
)
from webui.backend.lib.sensor_reader import (
    SENSOR_COMPARISONS,
    SENSOR_TYPES,
    reset_i2c_availability,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def reset_sensor_state():
    """Reset sensor reader I2C state before each test."""
    reset_i2c_availability()
    yield
    reset_i2c_availability()


@pytest.fixture
def mock_sensor_reading():
    """Mock get_sensor_reading to return controlled values."""
    with patch("check_and_run.get_sensor_reading") as mock:
        yield mock


@pytest.fixture
def mock_check_precondition():
    """Mock check_precondition to return controlled results."""
    with patch("check_and_run.check_precondition") as mock:
        yield mock


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for command execution tests."""
    with patch("check_and_run.subprocess.run") as mock:
        mock.return_value = MagicMock(returncode=0)
        yield mock


# =============================================================================
# TEST ARGUMENT PARSING
# =============================================================================


class TestParseArgs:
    """Tests for argument parsing."""

    def test_valid_arguments_parsed(self):
        """Test that valid arguments are parsed correctly."""
        args = parse_args(
            ["--sensor", "light", "--op", "lt", "--threshold", "100", "--", "echo", "test"]
        )

        assert args.sensor == "light"
        assert args.op == "lt"
        assert args.threshold == 100.0
        assert args.command == ["--", "echo", "test"]
        assert args.dry_run is False
        assert args.verbose is False

    def test_all_sensor_types_accepted(self):
        """Test that all defined sensor types are accepted."""
        for sensor_type in SENSOR_TYPES:
            args = parse_args(
                ["--sensor", sensor_type, "--op", "gt", "--threshold", "50", "--", "cmd"]
            )
            assert args.sensor == sensor_type

    def test_all_comparison_operators_accepted(self):
        """Test that all defined comparison operators are accepted."""
        for comparison in SENSOR_COMPARISONS:
            args = parse_args(
                ["--sensor", "light", "--op", comparison, "--threshold", "50", "--", "cmd"]
            )
            assert args.op == comparison

    def test_invalid_sensor_type_fails(self):
        """Test that invalid sensor type raises error."""
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--sensor", "invalid", "--op", "lt", "--threshold", "100", "--", "cmd"])
        assert exc_info.value.code == 2  # argparse error code

    def test_invalid_comparison_fails(self):
        """Test that invalid comparison operator raises error."""
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--sensor", "light", "--op", "invalid", "--threshold", "100", "--", "cmd"])
        assert exc_info.value.code == 2  # argparse error code

    def test_dry_run_and_verbose_flags(self):
        """Test that dry-run and verbose flags are parsed."""
        args = parse_args(
            [
                "--sensor",
                "light",
                "--op",
                "lt",
                "--threshold",
                "100",
                "--dry-run",
                "--verbose",
                "--",
                "cmd",
            ]
        )

        assert args.dry_run is True
        assert args.verbose is True


# =============================================================================
# TEST CHECK AND RUN CORE LOGIC
# =============================================================================


class TestCheckAndRun:
    """Tests for check_and_run core function."""

    def test_condition_met_executes_command(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that command is executed when condition is met."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=50.0, timestamp=datetime.now(), unit="lux"
        )
        mock_check_precondition.return_value = True
        mock_subprocess.return_value.returncode = 0

        result = check_and_run(
            sensor_type="light",
            comparison="lt",
            threshold=100.0,
            command=["echo", "test"],
        )

        assert result == EXIT_SUCCESS
        mock_subprocess.assert_called_once_with(["echo", "test"], check=False)

    def test_condition_not_met_skips_command(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that command is skipped when condition is not met."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=150.0, timestamp=datetime.now(), unit="lux"
        )
        mock_check_precondition.return_value = False

        result = check_and_run(
            sensor_type="light",
            comparison="lt",
            threshold=100.0,
            command=["echo", "test"],
        )

        assert result == EXIT_CONDITION_NOT_MET
        mock_subprocess.assert_not_called()

    def test_sensor_unavailable_returns_error(self, mock_sensor_reading, mock_subprocess):
        """Test that unavailable sensor returns appropriate exit code."""
        mock_sensor_reading.return_value = None

        result = check_and_run(
            sensor_type="light",
            comparison="lt",
            threshold=100.0,
            command=["echo", "test"],
        )

        assert result == EXIT_SENSOR_UNAVAILABLE
        mock_subprocess.assert_not_called()

    def test_dry_run_does_not_execute(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that dry-run mode doesn't execute the command."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=50.0, timestamp=datetime.now(), unit="lux"
        )
        mock_check_precondition.return_value = True

        result = check_and_run(
            sensor_type="light",
            comparison="lt",
            threshold=100.0,
            command=["echo", "test"],
            dry_run=True,
        )

        assert result == EXIT_SUCCESS
        mock_subprocess.assert_not_called()

    def test_command_exit_code_passed_through(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that command's exit code is passed through."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=50.0, timestamp=datetime.now(), unit="lux"
        )
        mock_check_precondition.return_value = True
        mock_subprocess.return_value.returncode = 42

        result = check_and_run(
            sensor_type="light",
            comparison="lt",
            threshold=100.0,
            command=["exit", "42"],
        )

        assert result == 42

    def test_command_not_found_returns_127(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that command not found returns exit code 127."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=50.0, timestamp=datetime.now(), unit="lux"
        )
        mock_check_precondition.return_value = True
        mock_subprocess.side_effect = FileNotFoundError("No such file")

        result = check_and_run(
            sensor_type="light",
            comparison="lt",
            threshold=100.0,
            command=["nonexistent_command"],
        )

        assert result == 127

    def test_permission_denied_returns_126(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that permission denied returns exit code 126."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=50.0, timestamp=datetime.now(), unit="lux"
        )
        mock_check_precondition.return_value = True
        mock_subprocess.side_effect = PermissionError("Permission denied")

        result = check_and_run(
            sensor_type="light",
            comparison="lt",
            threshold=100.0,
            command=["protected_command"],
        )

        assert result == 126

    def test_temperature_sensor_supported(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that temperature sensor works correctly."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="temperature", value=25.0, timestamp=datetime.now(), unit="celsius"
        )
        mock_check_precondition.return_value = True
        mock_subprocess.return_value.returncode = 0

        result = check_and_run(
            sensor_type="temperature",
            comparison="gte",
            threshold=20.0,
            command=["echo", "warm"],
        )

        assert result == EXIT_SUCCESS
        mock_check_precondition.assert_called_once_with("temperature", 20.0, "gte")

    def test_all_comparison_operators_work(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that all comparison operators are passed correctly."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=100.0, timestamp=datetime.now(), unit="lux"
        )
        mock_subprocess.return_value.returncode = 0

        for comparison in SENSOR_COMPARISONS:
            mock_check_precondition.return_value = True
            mock_check_precondition.reset_mock()

            check_and_run(
                sensor_type="light",
                comparison=comparison,
                threshold=100.0,
                command=["echo", "test"],
            )

            mock_check_precondition.assert_called_once_with("light", 100.0, comparison)

    def test_negative_threshold_supported(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that negative threshold values work (for temperature)."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="temperature", value=-5.0, timestamp=datetime.now(), unit="celsius"
        )
        mock_check_precondition.return_value = True
        mock_subprocess.return_value.returncode = 0

        result = check_and_run(
            sensor_type="temperature",
            comparison="lt",
            threshold=0.0,
            command=["echo", "freezing"],
        )

        assert result == EXIT_SUCCESS
        mock_check_precondition.assert_called_once_with("temperature", 0.0, "lt")


# =============================================================================
# TEST EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_threshold(self, mock_sensor_reading, mock_check_precondition, mock_subprocess):
        """Test that zero threshold works correctly."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=0.0, timestamp=datetime.now(), unit="lux"
        )
        mock_check_precondition.return_value = True
        mock_subprocess.return_value.returncode = 0

        result = check_and_run(
            sensor_type="light",
            comparison="eq",
            threshold=0.0,
            command=["echo", "dark"],
        )

        assert result == EXIT_SUCCESS
        mock_check_precondition.assert_called_once_with("light", 0.0, "eq")

    def test_large_threshold(self, mock_sensor_reading, mock_check_precondition, mock_subprocess):
        """Test that very large threshold values are handled."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=100000.0, timestamp=datetime.now(), unit="lux"
        )
        mock_check_precondition.return_value = True
        mock_subprocess.return_value.returncode = 0

        result = check_and_run(
            sensor_type="light",
            comparison="lt",
            threshold=1000000.0,
            command=["echo", "bright"],
        )

        assert result == EXIT_SUCCESS
        mock_check_precondition.assert_called_once_with("light", 1000000.0, "lt")

    def test_command_with_special_characters(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that commands with special characters are passed correctly."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=50.0, timestamp=datetime.now(), unit="lux"
        )
        mock_check_precondition.return_value = True
        mock_subprocess.return_value.returncode = 0

        # Command with spaces and quotes in arguments
        command = ["echo", "test with spaces", "and 'quotes'", 'double "quotes"']

        result = check_and_run(
            sensor_type="light",
            comparison="lt",
            threshold=100.0,
            command=command,
        )

        assert result == EXIT_SUCCESS
        mock_subprocess.assert_called_once_with(command, check=False)


# =============================================================================
# TEST MAIN FUNCTION
# =============================================================================


class TestMain:
    """Tests for main entry point."""

    def test_missing_command_returns_config_error(self, mock_sensor_reading):
        """Test that missing command returns config error."""
        result = main(["--sensor", "light", "--op", "lt", "--threshold", "100"])

        assert result == EXIT_CONFIG_ERROR

    def test_strips_leading_separator(
        self, mock_sensor_reading, mock_check_precondition, mock_subprocess
    ):
        """Test that leading '--' separator is stripped from command."""
        from datetime import datetime

        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light", value=50.0, timestamp=datetime.now(), unit="lux"
        )
        mock_check_precondition.return_value = True
        mock_subprocess.return_value.returncode = 0

        result = main(
            ["--sensor", "light", "--op", "lt", "--threshold", "100", "--", "echo", "test"]
        )

        assert result == EXIT_SUCCESS
        mock_subprocess.assert_called_once_with(["echo", "test"], check=False)


# =============================================================================
# TEST LOGGING
# =============================================================================


class TestLogging:
    """Tests for logging behavior."""

    def test_setup_logging_returns_logger(self):
        """Test that setup_logging returns a logger instance."""
        logger = setup_logging(verbose=False)
        assert isinstance(logger, logging.Logger)
        assert logger.name == "check_and_run"

    def test_setup_logging_verbose_sets_root_level(self):
        """Test that verbose=True sets root logger to DEBUG level."""
        # Save original level
        original_level = logging.getLogger().level

        try:
            setup_logging(verbose=True)
            # With verbose=True, root logger should be set to DEBUG
            assert logging.getLogger().level == logging.DEBUG
        finally:
            # Restore original level
            logging.getLogger().setLevel(original_level)

    def test_op_symbols_all_defined(self):
        """Test that all comparison operators have symbols defined."""
        for comparison in SENSOR_COMPARISONS:
            assert comparison in OP_SYMBOLS


# =============================================================================
# TEST INTEGRATION WITH CRON BRIDGE
# =============================================================================


class TestIntegration:
    """Tests for integration with cron_bridge.py."""

    def test_script_exists_at_firmware_root(self):
        """Test that check_and_run.py exists at MOTHBOX_HOME (firmware root)."""
        script_path = _firmware_root / "check_and_run.py"
        assert script_path.exists(), f"check_and_run.py not found at {script_path}"

    def test_command_format_matches_cron_bridge(self):
        """Test that CLI accepts the exact format generated by cron_bridge.py.

        cron_bridge.py generates:
            python3 {check_and_run_script}
            --sensor {pre_condition.sensor_type}
            --op {pre_condition.comparison}
            --threshold {pre_condition.threshold}
            -- {base_command}

        Note: parse_args() returns command with leading "--" (argparse.REMAINDER
        captures it). The main() function strips it before passing to check_and_run().
        """
        # This is the exact format from cron_bridge.py build_action_command()
        args = parse_args(
            [
                "--sensor",
                "light",
                "--op",
                "gt",
                "--threshold",
                "500.0",
                "--",
                "/usr/bin/python3",
                "/opt/mothbox/5.x/TakePhoto.py",
            ]
        )

        assert args.sensor == "light"
        assert args.op == "gt"
        assert args.threshold == 500.0
        # parse_args returns command with "--" prefix (stripped by main())
        assert args.command == ["--", "/usr/bin/python3", "/opt/mothbox/5.x/TakePhoto.py"]

    def test_exit_codes_documented(self):
        """Test that all documented exit codes are defined."""
        assert EXIT_SUCCESS == 0
        assert EXIT_CONDITION_NOT_MET == 75
        assert EXIT_SENSOR_UNAVAILABLE == 69
        assert EXIT_CONFIG_ERROR == 78
