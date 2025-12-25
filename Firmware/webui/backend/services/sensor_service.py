"""
Sensor Pre-condition Service for Mothbox Scheduler.

Evaluates sensor pre-conditions at capture time and tracks evaluation history.
Thread-safe with configurable history size.

Usage:
    from webui.backend.services import get_sensor_service
    from webui.backend.services.sensor_service import SensorPrecondition

    service = get_sensor_service()

    # Evaluate pre-conditions (returns True if ALL pass)
    preconditions = [
        SensorPrecondition(sensor_type="light", threshold=100, comparison="lt"),
        SensorPrecondition(sensor_type="temperature", threshold=30, comparison="lte"),
    ]
    if service.evaluate_preconditions(preconditions):
        # All conditions passed, proceed with capture
        pass

    # Get current readings for diagnostics
    readings = service.get_current_readings()

    # Get evaluation history
    history = service.get_evaluation_history(limit=10)

Issue #231 - Scheduler Phase 9: Sensor Pre-condition Service
"""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Final

from webui.backend.lib.sensor_reader import (
    SENSOR_COMPARISONS,
    SENSOR_TYPES,
    SensorReading,
    check_precondition,
    get_sensor_reading,
)

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_HISTORY_SIZE: Final[int] = 100
DEFAULT_HISTORY_SIZE: Final[int] = 100

# Precondition result reasons
REASON_PASSED: Final[str] = "passed"
REASON_FAILED: Final[str] = "failed"
REASON_SENSOR_UNAVAILABLE: Final[str] = "sensor_unavailable"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class SensorPrecondition:
    """
    A sensor pre-condition for capture gating.

    Pre-conditions are evaluated at capture time - if any fail,
    the capture is skipped.

    Attributes:
        sensor_type: Type of sensor ("light" or "temperature")
        threshold: Value to compare against
        comparison: Comparison operator ("gt", "lt", "eq", "gte", "lte")
        description: Optional human-readable description

    Example:
        >>> precondition = SensorPrecondition(
        ...     sensor_type="light",
        ...     threshold=100,
        ...     comparison="lt",
        ...     description="Only capture when ambient light < 100 lux"
        ... )
    """

    sensor_type: str
    threshold: float
    comparison: str
    description: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sensor_type": self.sensor_type,
            "threshold": self.threshold,
            "comparison": self.comparison,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SensorPrecondition":
        """Create from dictionary."""
        return cls(
            sensor_type=data["sensor_type"],
            threshold=data["threshold"],
            comparison=data["comparison"],
            description=data.get("description", ""),
        )


@dataclass
class PreconditionResult:
    """
    Result of evaluating a single sensor pre-condition.

    Attributes:
        precondition: The pre-condition that was evaluated
        reading_value: Sensor reading value (None if sensor unavailable)
        passed: Whether the pre-condition passed
        timestamp: When the evaluation occurred
        reason: Result reason ("passed", "failed", "sensor_unavailable")
    """

    precondition: SensorPrecondition
    reading_value: float | None
    passed: bool
    timestamp: datetime
    reason: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "precondition": self.precondition.to_dict(),
            "reading_value": self.reading_value,
            "passed": self.passed,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
        }


# =============================================================================
# SERVICE CLASS
# =============================================================================


class SensorService:
    """
    Service for evaluating sensor pre-conditions with history tracking.

    Thread-safe with configurable history size. Wraps sensor_reader functions
    with evaluation tracking for diagnostics and debugging.

    Attributes:
        _evaluation_history: Circular buffer of recent evaluation results
        _lock: RLock for thread-safe access
        _max_history: Maximum history entries to retain
    """

    def __init__(self, max_history: int = DEFAULT_HISTORY_SIZE):
        """
        Initialize SensorService.

        Args:
            max_history: Maximum history entries to retain (default 100).
                         Values < 1 are auto-corrected to 1 with a warning.
                         Values > MAX_HISTORY_SIZE are capped with a warning.
        """
        if max_history < 1:
            max_history = 1
            logger.warning("max_history must be at least 1, using 1")
        if max_history > MAX_HISTORY_SIZE:
            max_history = MAX_HISTORY_SIZE
            logger.warning(f"max_history capped at {MAX_HISTORY_SIZE}")

        self._max_history = max_history
        self._evaluation_history: deque[PreconditionResult] = deque(maxlen=max_history)
        self._lock = RLock()

        # Statistics
        self._total_evaluations = 0
        self._passed_count = 0
        self._failed_count = 0
        self._unavailable_count = 0

    def evaluate_preconditions(
        self, preconditions: list[SensorPrecondition]
    ) -> bool:
        """
        Evaluate multiple pre-conditions (ALL must pass).

        Args:
            preconditions: List of SensorPrecondition to evaluate

        Returns:
            True if ALL pre-conditions pass, False if any fail

        Note:
            Empty list returns True (no conditions = no restrictions).
            Each evaluation is recorded in history.

            All preconditions are evaluated even if one fails early.
            This ensures complete diagnostic history is captured for
            debugging why a capture was skipped.
        """
        if not preconditions:
            return True

        all_passed = True
        for precondition in preconditions:
            result = self._evaluate_single(precondition)
            if not result.passed:
                all_passed = False
                # Continue evaluating all for complete history

        return all_passed

    def _evaluate_single(self, precondition: SensorPrecondition) -> PreconditionResult:
        """
        Evaluate a single pre-condition.

        Args:
            precondition: Pre-condition to evaluate

        Returns:
            PreconditionResult with evaluation details
        """
        timestamp = datetime.now()

        # Validate sensor type
        if precondition.sensor_type not in SENSOR_TYPES:
            logger.warning(
                f"Invalid sensor type: {precondition.sensor_type}. "
                f"Valid: {SENSOR_TYPES}"
            )
            result = PreconditionResult(
                precondition=precondition,
                reading_value=None,
                passed=False,
                timestamp=timestamp,
                reason=REASON_FAILED,
            )
            with self._lock:
                self._total_evaluations += 1
                self._failed_count += 1
                self._evaluation_history.append(result)
            return result

        # Validate comparison operator
        if precondition.comparison not in SENSOR_COMPARISONS:
            logger.warning(
                f"Invalid comparison: {precondition.comparison}. "
                f"Valid: {SENSOR_COMPARISONS}"
            )
            result = PreconditionResult(
                precondition=precondition,
                reading_value=None,
                passed=False,
                timestamp=timestamp,
                reason=REASON_FAILED,
            )
            with self._lock:
                self._total_evaluations += 1
                self._failed_count += 1
                self._evaluation_history.append(result)
            return result

        # Get sensor reading
        reading = get_sensor_reading(precondition.sensor_type)

        if reading is None:
            logger.debug(f"Sensor unavailable: {precondition.sensor_type}")
            result = PreconditionResult(
                precondition=precondition,
                reading_value=None,
                passed=False,
                timestamp=timestamp,
                reason=REASON_SENSOR_UNAVAILABLE,
            )
            with self._lock:
                self._total_evaluations += 1
                self._unavailable_count += 1
                self._evaluation_history.append(result)
            return result

        # Evaluate the condition
        passed = check_precondition(
            sensor_type=precondition.sensor_type,
            threshold=precondition.threshold,
            comparison=precondition.comparison,
        )

        logger.debug(
            f"Precondition {precondition.sensor_type} "
            f"{reading.value:.2f} {precondition.comparison} "
            f"{precondition.threshold} = {passed}"
        )

        result = PreconditionResult(
            precondition=precondition,
            reading_value=reading.value,
            passed=passed,
            timestamp=timestamp,
            reason=REASON_PASSED if passed else REASON_FAILED,
        )

        with self._lock:
            self._total_evaluations += 1
            if passed:
                self._passed_count += 1
            else:
                self._failed_count += 1
            self._evaluation_history.append(result)

        return result

    def get_current_readings(self) -> dict[str, SensorReading | None]:
        """
        Get current readings from all supported sensors.

        Returns:
            Dict mapping sensor type to SensorReading (or None if unavailable)

        Example:
            >>> readings = service.get_current_readings()
            >>> if readings["light"]:
            ...     print(f"Light: {readings['light'].value} lux")
        """
        readings = {}
        for sensor_type in SENSOR_TYPES:
            readings[sensor_type] = get_sensor_reading(sensor_type)
        return readings

    def get_evaluation_history(self, limit: int = 10) -> list[PreconditionResult]:
        """
        Get recent evaluation history.

        Args:
            limit: Maximum number of results to return (default 10)

        Returns:
            List of PreconditionResult, most recent first
        """
        with self._lock:
            # Convert deque to list and get last N items, then reverse
            history = list(self._evaluation_history)[-limit:]
            history.reverse()
            return history

    def clear_history(self) -> None:
        """
        Clear all evaluation history.

        Note:
            This clears only the history buffer (recent evaluation records).
            Lifetime statistics (total_evaluations, passed_count, etc.) are
            preserved. Use reset_statistics() to reset counters.
        """
        with self._lock:
            self._evaluation_history.clear()
            logger.debug("Cleared evaluation history")

    def reset_statistics(self) -> None:
        """
        Reset all lifetime statistics counters.

        Resets total_evaluations, passed_count, failed_count, and
        unavailable_count to zero. Does NOT clear evaluation history.

        Note:
            History (evaluation records) and statistics (lifetime counters)
            are tracked separately. Use clear_history() to clear records,
            or call both methods to fully reset the service state.
        """
        with self._lock:
            self._total_evaluations = 0
            self._passed_count = 0
            self._failed_count = 0
            self._unavailable_count = 0
            logger.debug("Reset statistics counters")

    def get_statistics(self) -> dict:
        """
        Get service statistics.

        Returns:
            Dict with evaluation statistics:
            - total_evaluations: Total number of evaluations
            - passed_count: Number of passed evaluations
            - failed_count: Number of failed evaluations
            - unavailable_count: Number of sensor unavailable results
            - history_size: Current history buffer size
            - max_history: Maximum history size
            - pass_rate: Pass rate percentage (0.0 to 1.0)
        """
        with self._lock:
            total = self._total_evaluations
            pass_rate = 0.0
            if total > 0:
                pass_rate = self._passed_count / total

            return {
                "total_evaluations": total,
                "passed_count": self._passed_count,
                "failed_count": self._failed_count,
                "unavailable_count": self._unavailable_count,
                "history_size": len(self._evaluation_history),
                "max_history": self._max_history,
                "pass_rate": pass_rate,
            }


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "SensorService",
    "SensorPrecondition",
    "PreconditionResult",
    "REASON_PASSED",
    "REASON_FAILED",
    "REASON_SENSOR_UNAVAILABLE",
    "DEFAULT_HISTORY_SIZE",
    "MAX_HISTORY_SIZE",
]
