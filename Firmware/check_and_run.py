#!/usr/bin/env python3
"""Pre-condition wrapper script for Mothbox scheduler.

Checks sensor conditions before executing scheduled actions.
Used by cron_bridge.py to wrap action commands with pre-conditions.

Usage:
    python3 check_and_run.py --sensor light --op lt --threshold 100 -- python3 TakePhoto.py
    python3 check_and_run.py --sensor temperature --op gte --threshold 20 --verbose -- python3 GPS.py
    python3 check_and_run.py --sensor light --op lt --threshold 50 --dry-run -- echo "test"

Arguments:
    --sensor {light,temperature}  Sensor type to check
    --op {gt,lt,eq,gte,lte}       Comparison operator
    --threshold FLOAT             Threshold value to compare against
    --dry-run                     Check condition without executing command
    --verbose, -v                 Enable verbose (DEBUG) logging
    command after --              The command to execute if condition is met

Exit Codes:
    0: Condition met, command executed successfully
    75: Condition not met (EX_TEMPFAIL - temporary failure)
    69: Sensor unavailable (EX_UNAVAILABLE)
    78: Invalid arguments (EX_CONFIG)
    1-127: Pass through command's exit code

Issue #311 - Create check_and_run.py pre-condition wrapper
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Path setup for accessing webui modules at firmware root
_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from webui.backend.lib.sensor_reader import (
    SENSOR_COMPARISONS,
    SENSOR_TYPES,
    check_precondition,
    get_sensor_reading,
)

# Module exports
__all__ = [
    "setup_logging",
    "parse_args",
    "check_and_run",
    "main",
    # Exit codes
    "EXIT_SUCCESS",
    "EXIT_CONDITION_NOT_MET",
    "EXIT_SENSOR_UNAVAILABLE",
    "EXIT_CONFIG_ERROR",
]

# Exit codes (sysexits.h)
EXIT_SUCCESS = 0
EXIT_CONDITION_NOT_MET = 75  # EX_TEMPFAIL - condition may be met on next execution
EXIT_SENSOR_UNAVAILABLE = 69  # EX_UNAVAILABLE - sensor hardware not available
EXIT_CONFIG_ERROR = 78  # EX_CONFIG - configuration error (bad arguments)

# Logging configuration
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Human-readable operator symbols for logging
OP_SYMBOLS = {
    "gt": ">",
    "lt": "<",
    "eq": "==",
    "gte": ">=",
    "lte": "<=",
}


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for check_and_run.

    Note: Uses force=True to reconfigure root logger. This script is designed
    for standalone CLI use (subprocess execution from cron). Do not import
    this module into other processes where logging is already configured.

    Args:
        verbose: If True, sets log level to DEBUG. Otherwise INFO.

    Returns:
        Configured logger instance
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Force reconfiguration even if already configured (standalone CLI use)
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stderr,
        force=True,
    )
    return logging.getLogger(__name__)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Arguments to parse (defaults to sys.argv[1:])

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Check sensor condition before executing command",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--sensor",
        required=True,
        choices=SENSOR_TYPES,
        help=f"Sensor type to check ({', '.join(SENSOR_TYPES)})",
    )
    parser.add_argument(
        "--op",
        required=True,
        choices=SENSOR_COMPARISONS,
        help=f"Comparison operator ({', '.join(SENSOR_COMPARISONS)})",
    )
    parser.add_argument(
        "--threshold",
        required=True,
        type=float,
        help="Threshold value to compare against",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check condition without executing command",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to execute (after --)",
    )

    return parser.parse_args(args)


def check_and_run(
    sensor_type: str,
    comparison: str,
    threshold: float,
    command: list[str],
    dry_run: bool = False,
    logger: logging.Logger | None = None,
) -> int:
    """Check sensor precondition and execute command if met.

    Args:
        sensor_type: Type of sensor to check ("light" or "temperature")
        comparison: Comparison operator ("gt", "lt", "eq", "gte", "lte")
        threshold: Threshold value for comparison
        command: Command and arguments to execute
        dry_run: If True, check condition but don't execute command
        logger: Logger instance (creates one if not provided)

    Returns:
        Exit code (0 for success, 75 for condition not met, etc.)
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Get sensor reading for logging
    reading = get_sensor_reading(sensor_type)
    if reading is None:
        logger.warning(f"Sensor unavailable: {sensor_type}")
        return EXIT_SENSOR_UNAVAILABLE

    # Log current reading
    logger.debug(f"Sensor reading: {sensor_type}={reading.value:.2f} {reading.unit}")

    # Check precondition
    condition_met = check_precondition(sensor_type, threshold, comparison)

    # Format condition for logging
    op_symbol = OP_SYMBOLS.get(comparison, comparison)
    condition_str = f"{sensor_type}={reading.value:.2f} {op_symbol} {threshold}"
    command_str = " ".join(command)

    if not condition_met:
        logger.info(f"Pre-condition NOT met ({condition_str}), skipping: {command_str}")
        return EXIT_CONDITION_NOT_MET

    logger.info(f"Pre-condition met ({condition_str}), executing: {command_str}")

    if dry_run:
        logger.info(f"Dry run: would execute: {command_str}")
        return EXIT_SUCCESS

    # Execute command
    # Security: command is pre-validated by cron_bridge.build_action_command()
    # which only allows whitelisted scripts from cron_security.py.
    # User input cannot reach this code path - commands originate from
    # schedule activation, not external input.
    try:
        result = subprocess.run(command, check=False)  # noqa: S603
        return result.returncode
    except FileNotFoundError as e:
        logger.error(f"Command not found: {e}")
        return 127  # Standard "command not found" exit code
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        return 126  # Standard "permission denied" exit code
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        return 1


def main(args: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code
    """
    parsed_args = parse_args(args)
    logger = setup_logging(parsed_args.verbose)

    # Extract command, stripping leading '--' if present
    command = parsed_args.command
    if command and command[0] == "--":
        command = command[1:]

    if not command:
        logger.error("No command specified after --")
        return EXIT_CONFIG_ERROR

    return check_and_run(
        sensor_type=parsed_args.sensor,
        comparison=parsed_args.op,
        threshold=parsed_args.threshold,
        command=command,
        dry_run=parsed_args.dry_run,
        logger=logger,
    )


if __name__ == "__main__":
    sys.exit(main())
