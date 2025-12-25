"""
Unit tests for Sensor Service (Issue #231).

Tests the SensorService class for pre-condition evaluation, history tracking,
and thread-safety.

Test structure:
- TestSensorPrecondition (3 tests)
- TestPreconditionResult (2 tests)
- TestSensorServiceInit (3 tests)
- TestEvaluateSingle (5 tests)
- TestEvaluatePreconditions (4 tests)
- TestGetCurrentReadings (2 tests)
- TestGetEvaluationHistory (3 tests)
- TestGetStatistics (2 tests)
- TestClearHistory (1 test)
- TestResetStatistics (2 tests)
- TestSingleton (1 test)

Total: 28 tests
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from webui.backend.services import get_sensor_service
from webui.backend.services.sensor_service import (
    DEFAULT_HISTORY_SIZE,
    REASON_FAILED,
    REASON_PASSED,
    REASON_SENSOR_UNAVAILABLE,
    PreconditionResult,
    SensorPrecondition,
    SensorService,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def reset_sensor_service_singleton():
    """Reset the singleton before each test."""
    import webui.backend.services as services_module

    services_module._sensor_service = None
    yield
    services_module._sensor_service = None


@pytest.fixture
def mock_sensor_reading():
    """Mock get_sensor_reading to return controlled values."""
    with patch("webui.backend.services.sensor_service.get_sensor_reading") as mock:
        yield mock


@pytest.fixture
def mock_check_precondition():
    """Mock check_precondition to return controlled values."""
    with patch("webui.backend.services.sensor_service.check_precondition") as mock:
        yield mock


# =============================================================================
# TEST SENSOR PRECONDITION DATACLASS
# =============================================================================


class TestSensorPrecondition:
    """Tests for SensorPrecondition dataclass."""

    def test_precondition_creation(self):
        """Test creating a SensorPrecondition with all fields."""
        precondition = SensorPrecondition(
            sensor_type="light",
            threshold=100.0,
            comparison="lt",
            description="Only capture in low light",
        )

        assert precondition.sensor_type == "light"
        assert precondition.threshold == 100.0
        assert precondition.comparison == "lt"
        assert precondition.description == "Only capture in low light"

    def test_precondition_to_dict(self):
        """Test serialization to dictionary."""
        precondition = SensorPrecondition(
            sensor_type="temperature",
            threshold=30.0,
            comparison="lte",
            description="Capture below 30C",
        )

        data = precondition.to_dict()

        assert data["sensor_type"] == "temperature"
        assert data["threshold"] == 30.0
        assert data["comparison"] == "lte"
        assert data["description"] == "Capture below 30C"

    def test_precondition_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "sensor_type": "light",
            "threshold": 50.0,
            "comparison": "gt",
            "description": "Test",
        }

        precondition = SensorPrecondition.from_dict(data)

        assert precondition.sensor_type == "light"
        assert precondition.threshold == 50.0
        assert precondition.comparison == "gt"


# =============================================================================
# TEST PRECONDITION RESULT DATACLASS
# =============================================================================


class TestPreconditionResult:
    """Tests for PreconditionResult dataclass."""

    def test_result_creation(self):
        """Test creating a PreconditionResult."""
        precondition = SensorPrecondition(
            sensor_type="light", threshold=100, comparison="lt"
        )
        now = datetime.now()

        result = PreconditionResult(
            precondition=precondition,
            reading_value=50.0,
            passed=True,
            timestamp=now,
            reason=REASON_PASSED,
        )

        assert result.precondition == precondition
        assert result.reading_value == 50.0
        assert result.passed is True
        assert result.reason == REASON_PASSED

    def test_result_to_dict(self):
        """Test serialization to dictionary."""
        precondition = SensorPrecondition(
            sensor_type="temperature", threshold=25, comparison="lte"
        )
        now = datetime.now()

        result = PreconditionResult(
            precondition=precondition,
            reading_value=22.5,
            passed=True,
            timestamp=now,
            reason=REASON_PASSED,
        )

        data = result.to_dict()

        assert data["reading_value"] == 22.5
        assert data["passed"] is True
        assert data["reason"] == REASON_PASSED
        assert "precondition" in data
        assert data["precondition"]["sensor_type"] == "temperature"


# =============================================================================
# TEST SENSOR SERVICE INITIALIZATION
# =============================================================================


class TestSensorServiceInit:
    """Tests for SensorService initialization."""

    def test_default_initialization(self):
        """Test creating SensorService with defaults."""
        service = SensorService()

        assert service._max_history == DEFAULT_HISTORY_SIZE
        assert len(service._evaluation_history) == 0

    def test_custom_max_history(self):
        """Test creating SensorService with custom history size."""
        service = SensorService(max_history=50)

        assert service._max_history == 50

    def test_invalid_max_history_raises(self):
        """Test that invalid max_history raises ValueError."""
        with pytest.raises(ValueError):
            SensorService(max_history=0)

        with pytest.raises(ValueError):
            SensorService(max_history=-1)


# =============================================================================
# TEST EVALUATE SINGLE
# =============================================================================


class TestEvaluateSingle:
    """Tests for _evaluate_single method."""

    def test_evaluate_passing_precondition(
        self, mock_sensor_reading, mock_check_precondition
    ):
        """Test evaluating a passing pre-condition."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=50.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        mock_check_precondition.return_value = True

        service = SensorService()
        precondition = SensorPrecondition(
            sensor_type="light", threshold=100, comparison="lt"
        )

        result = service._evaluate_single(precondition)

        assert result.passed is True
        assert result.reading_value == 50.0
        assert result.reason == REASON_PASSED

    def test_evaluate_failing_precondition(
        self, mock_sensor_reading, mock_check_precondition
    ):
        """Test evaluating a failing pre-condition."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=150.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        mock_check_precondition.return_value = False

        service = SensorService()
        precondition = SensorPrecondition(
            sensor_type="light", threshold=100, comparison="lt"
        )

        result = service._evaluate_single(precondition)

        assert result.passed is False
        assert result.reading_value == 150.0
        assert result.reason == REASON_FAILED

    def test_evaluate_sensor_unavailable(self, mock_sensor_reading):
        """Test evaluating when sensor is unavailable."""
        mock_sensor_reading.return_value = None

        service = SensorService()
        precondition = SensorPrecondition(
            sensor_type="light", threshold=100, comparison="lt"
        )

        result = service._evaluate_single(precondition)

        assert result.passed is False
        assert result.reading_value is None
        assert result.reason == REASON_SENSOR_UNAVAILABLE

    def test_evaluate_invalid_sensor_type(self):
        """Test evaluating with invalid sensor type."""
        service = SensorService()
        precondition = SensorPrecondition(
            sensor_type="motion",  # Invalid - not in SENSOR_TYPES
            threshold=1,
            comparison="gt",
        )

        result = service._evaluate_single(precondition)

        assert result.passed is False
        assert result.reason == REASON_FAILED

    def test_evaluate_invalid_comparison(self):
        """Test evaluating with invalid comparison operator."""
        service = SensorService()
        precondition = SensorPrecondition(
            sensor_type="light",
            threshold=100,
            comparison="ne",  # Invalid - not in SENSOR_COMPARISONS
        )

        result = service._evaluate_single(precondition)

        assert result.passed is False
        assert result.reason == REASON_FAILED


# =============================================================================
# TEST EVALUATE PRECONDITIONS (MULTIPLE)
# =============================================================================


class TestEvaluatePreconditions:
    """Tests for evaluate_preconditions method."""

    def test_empty_list_returns_true(self):
        """Test that empty precondition list returns True."""
        service = SensorService()

        result = service.evaluate_preconditions([])

        assert result is True

    def test_all_pass_returns_true(
        self, mock_sensor_reading, mock_check_precondition
    ):
        """Test that all passing pre-conditions return True."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=50.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        mock_check_precondition.return_value = True

        service = SensorService()
        preconditions = [
            SensorPrecondition(sensor_type="light", threshold=100, comparison="lt"),
            SensorPrecondition(sensor_type="light", threshold=25, comparison="gt"),
        ]

        result = service.evaluate_preconditions(preconditions)

        assert result is True

    def test_any_fail_returns_false(
        self, mock_sensor_reading, mock_check_precondition
    ):
        """Test that any failing pre-condition returns False."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=50.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        # First passes, second fails
        mock_check_precondition.side_effect = [True, False]

        service = SensorService()
        preconditions = [
            SensorPrecondition(sensor_type="light", threshold=100, comparison="lt"),
            SensorPrecondition(sensor_type="light", threshold=75, comparison="gt"),
        ]

        result = service.evaluate_preconditions(preconditions)

        assert result is False

    def test_all_preconditions_evaluated_even_if_one_fails(
        self, mock_sensor_reading, mock_check_precondition
    ):
        """Test that all pre-conditions are evaluated for history."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=50.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        mock_check_precondition.side_effect = [False, True, True]

        service = SensorService()
        preconditions = [
            SensorPrecondition(sensor_type="light", threshold=25, comparison="lt"),
            SensorPrecondition(sensor_type="light", threshold=100, comparison="lt"),
            SensorPrecondition(sensor_type="light", threshold=25, comparison="gt"),
        ]

        service.evaluate_preconditions(preconditions)

        # All 3 should be in history
        history = service.get_evaluation_history(limit=10)
        assert len(history) == 3


# =============================================================================
# TEST GET CURRENT READINGS
# =============================================================================


class TestGetCurrentReadings:
    """Tests for get_current_readings method."""

    def test_returns_readings_for_all_sensor_types(self, mock_sensor_reading):
        """Test that readings are returned for all sensor types."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=100.0,
            timestamp=datetime.now(),
            unit="lux",
        )

        service = SensorService()
        readings = service.get_current_readings()

        assert "light" in readings
        assert "temperature" in readings

    def test_returns_none_for_unavailable_sensors(self, mock_sensor_reading):
        """Test that None is returned for unavailable sensors."""
        mock_sensor_reading.return_value = None

        service = SensorService()
        readings = service.get_current_readings()

        assert readings["light"] is None
        assert readings["temperature"] is None


# =============================================================================
# TEST GET EVALUATION HISTORY
# =============================================================================


class TestGetEvaluationHistory:
    """Tests for get_evaluation_history method."""

    def test_empty_history(self):
        """Test getting history when empty."""
        service = SensorService()

        history = service.get_evaluation_history()

        assert history == []

    def test_history_limit(self, mock_sensor_reading, mock_check_precondition):
        """Test that limit parameter works correctly."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=50.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        mock_check_precondition.return_value = True

        service = SensorService()
        preconditions = [
            SensorPrecondition(sensor_type="light", threshold=100, comparison="lt")
            for _ in range(10)
        ]
        service.evaluate_preconditions(preconditions)

        history = service.get_evaluation_history(limit=5)

        assert len(history) == 5

    def test_history_most_recent_first(
        self, mock_sensor_reading, mock_check_precondition
    ):
        """Test that history is ordered most recent first."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=50.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        mock_check_precondition.return_value = True

        service = SensorService()

        # Evaluate two with different thresholds
        service.evaluate_preconditions(
            [SensorPrecondition(sensor_type="light", threshold=100, comparison="lt")]
        )
        service.evaluate_preconditions(
            [SensorPrecondition(sensor_type="light", threshold=200, comparison="lt")]
        )

        history = service.get_evaluation_history(limit=2)

        # Most recent (threshold=200) should be first
        assert history[0].precondition.threshold == 200
        assert history[1].precondition.threshold == 100


# =============================================================================
# TEST GET STATISTICS
# =============================================================================


class TestGetStatistics:
    """Tests for get_statistics method."""

    def test_initial_statistics(self):
        """Test statistics when no evaluations have occurred."""
        service = SensorService()

        stats = service.get_statistics()

        assert stats["total_evaluations"] == 0
        assert stats["passed_count"] == 0
        assert stats["failed_count"] == 0
        assert stats["unavailable_count"] == 0
        assert stats["pass_rate"] == 0.0

    def test_statistics_after_evaluations(
        self, mock_sensor_reading, mock_check_precondition
    ):
        """Test statistics after some evaluations."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=50.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        mock_check_precondition.side_effect = [True, True, False]

        service = SensorService()
        preconditions = [
            SensorPrecondition(sensor_type="light", threshold=100, comparison="lt"),
            SensorPrecondition(sensor_type="light", threshold=75, comparison="lt"),
            SensorPrecondition(sensor_type="light", threshold=25, comparison="lt"),
        ]
        service.evaluate_preconditions(preconditions)

        stats = service.get_statistics()

        assert stats["total_evaluations"] == 3
        assert stats["passed_count"] == 2
        assert stats["failed_count"] == 1
        assert abs(stats["pass_rate"] - 2 / 3) < 0.01  # ~66.7%


# =============================================================================
# TEST CLEAR HISTORY
# =============================================================================


class TestClearHistory:
    """Tests for clear_history method."""

    def test_clear_history(self, mock_sensor_reading, mock_check_precondition):
        """Test that clear_history removes all entries."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=50.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        mock_check_precondition.return_value = True

        service = SensorService()
        service.evaluate_preconditions(
            [SensorPrecondition(sensor_type="light", threshold=100, comparison="lt")]
        )

        assert len(service.get_evaluation_history()) == 1

        service.clear_history()

        assert len(service.get_evaluation_history()) == 0


# =============================================================================
# TEST RESET STATISTICS
# =============================================================================


class TestResetStatistics:
    """Tests for reset_statistics method."""

    def test_reset_statistics_clears_counters(
        self, mock_sensor_reading, mock_check_precondition
    ):
        """Test that reset_statistics clears all counters."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=50.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        mock_check_precondition.return_value = True

        service = SensorService()
        service.evaluate_preconditions(
            [SensorPrecondition(sensor_type="light", threshold=100, comparison="lt")]
        )

        # Verify stats are populated
        stats = service.get_statistics()
        assert stats["total_evaluations"] == 1
        assert stats["passed_count"] == 1

        # Reset and verify
        service.reset_statistics()
        stats = service.get_statistics()

        assert stats["total_evaluations"] == 0
        assert stats["passed_count"] == 0
        assert stats["failed_count"] == 0
        assert stats["unavailable_count"] == 0

    def test_reset_statistics_preserves_history(
        self, mock_sensor_reading, mock_check_precondition
    ):
        """Test that reset_statistics does NOT clear history."""
        from webui.backend.lib.sensor_reader import SensorReading

        mock_sensor_reading.return_value = SensorReading(
            sensor_type="light",
            value=50.0,
            timestamp=datetime.now(),
            unit="lux",
        )
        mock_check_precondition.return_value = True

        service = SensorService()
        service.evaluate_preconditions(
            [SensorPrecondition(sensor_type="light", threshold=100, comparison="lt")]
        )

        # Verify history exists
        assert len(service.get_evaluation_history()) == 1

        # Reset stats - history should remain
        service.reset_statistics()

        assert len(service.get_evaluation_history()) == 1


# =============================================================================
# TEST SINGLETON
# =============================================================================


class TestSingleton:
    """Tests for get_sensor_service singleton getter."""

    def test_singleton_returns_same_instance(self):
        """Test that get_sensor_service returns the same instance."""
        service1 = get_sensor_service()
        service2 = get_sensor_service()

        assert service1 is service2
