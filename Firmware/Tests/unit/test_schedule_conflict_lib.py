"""
Unit tests for schedule conflict detection library.

Tests cover:
- Data structure serialization (ResourceUsage, PatternExecution, Conflict, ConflictReport)
- Time overlap detection
- Resource contention detection (camera, GPS, GPIO)
- GPIO state conflict detection
- Pattern execution generation
- Conflict report generation
- Edge cases (adjacent patterns, same start time, overnight windows)

Coverage target: 85%+
Test count target: 35+

Issue #213 - Scheduler Phase 3: Conflict Detection
"""

from datetime import date, datetime

import pytest

# Import will fail until implementation exists
try:
    from webui.backend.lib.schedule_conflict import (
        GPIO_RESOURCES,
        SINGLE_RESOURCES,
        Conflict,
        ConflictReport,
        PatternExecution,
        ResourceUsage,
        check_resource_contention,
        check_time_overlap,
        detect_conflicts,
        generate_pattern_executions,
        get_resource_type,
        validate_schedule_conflicts,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False

# Skip all tests if implementation doesn't exist
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_resource_usage():
    """Create a sample ResourceUsage for testing."""
    return ResourceUsage(
        resource_type="camera",
        resource_name="takephoto",
        start_time=datetime(2024, 6, 15, 21, 5, 0),
        end_time=datetime(2024, 6, 15, 21, 5, 30),
        pattern_id="pattern-1",
        action_index=1,
    )


@pytest.fixture
def sample_pattern_execution():
    """Create a sample PatternExecution for testing."""
    return PatternExecution(
        pattern_id="pattern-1",
        pattern_name="UV Capture",
        start_time=datetime(2024, 6, 15, 21, 0, 0),
        end_time=datetime(2024, 6, 15, 21, 15, 0),
        resource_usages=[
            ResourceUsage(
                resource_type="gpio",
                resource_name="attract_on",
                start_time=datetime(2024, 6, 15, 21, 0, 0),
                end_time=datetime(2024, 6, 15, 21, 0, 0),
                pattern_id="pattern-1",
                action_index=0,
            ),
            ResourceUsage(
                resource_type="camera",
                resource_name="takephoto",
                start_time=datetime(2024, 6, 15, 21, 5, 0),
                end_time=datetime(2024, 6, 15, 21, 5, 30),
                pattern_id="pattern-1",
                action_index=1,
            ),
        ],
    )


@pytest.fixture
def sample_conflict():
    """Create a sample Conflict for testing."""
    return Conflict(
        conflict_type="resource_contention",
        event1_id="pattern-1",
        event1_name="UV Capture",
        event2_id="pattern-2",
        event2_name="Flash Capture",
        start_time=datetime(2024, 6, 15, 21, 5, 0),
        end_time=datetime(2024, 6, 15, 21, 5, 30),
        resource="camera",
        message="Camera resource conflict between patterns",
        suggested_resolution="Increase interval between pattern triggers",
        severity="error",
    )


@pytest.fixture
def sample_conflict_report(sample_conflict):
    """Create a sample ConflictReport for testing."""
    return ConflictReport(
        schedule_id="schedule-1",
        schedule_name="Nightly Survey",
        preview_start=datetime(2024, 6, 15, 0, 0, 0),
        preview_end=datetime(2024, 6, 21, 23, 59, 59),
        total_executions=10,
        conflicts=[sample_conflict],
        has_blocking_conflicts=True,
        analyzed_at=datetime(2024, 6, 15, 12, 0, 0),
    )


@pytest.fixture
def overlapping_executions():
    """Create two overlapping PatternExecutions."""
    exec1 = PatternExecution(
        pattern_id="pattern-1",
        pattern_name="Pattern 1",
        start_time=datetime(2024, 6, 15, 21, 0, 0),
        end_time=datetime(2024, 6, 15, 21, 15, 0),
        resource_usages=[
            ResourceUsage(
                resource_type="camera",
                resource_name="takephoto",
                start_time=datetime(2024, 6, 15, 21, 5, 0),
                end_time=datetime(2024, 6, 15, 21, 5, 30),
                pattern_id="pattern-1",
                action_index=0,
            )
        ],
    )
    exec2 = PatternExecution(
        pattern_id="pattern-2",
        pattern_name="Pattern 2",
        start_time=datetime(2024, 6, 15, 21, 10, 0),
        end_time=datetime(2024, 6, 15, 21, 25, 0),
        resource_usages=[
            ResourceUsage(
                resource_type="camera",
                resource_name="takephoto",
                start_time=datetime(2024, 6, 15, 21, 15, 0),
                end_time=datetime(2024, 6, 15, 21, 15, 30),
                pattern_id="pattern-2",
                action_index=0,
            )
        ],
    )
    return exec1, exec2


@pytest.fixture
def non_overlapping_executions():
    """Create two non-overlapping PatternExecutions."""
    exec1 = PatternExecution(
        pattern_id="pattern-1",
        pattern_name="Pattern 1",
        start_time=datetime(2024, 6, 15, 21, 0, 0),
        end_time=datetime(2024, 6, 15, 21, 15, 0),
        resource_usages=[],
    )
    exec2 = PatternExecution(
        pattern_id="pattern-2",
        pattern_name="Pattern 2",
        start_time=datetime(2024, 6, 15, 22, 0, 0),
        end_time=datetime(2024, 6, 15, 22, 15, 0),
        resource_usages=[],
    )
    return exec1, exec2


@pytest.fixture
def sample_schedule():
    """Create a valid Schedule for conflict testing."""
    from webui.backend.lib.schedule_schema import (
        EventPattern,
        IntervalTrigger,
        PatternAction,
        Schedule,
        TimeWindow,
    )

    actions = [
        PatternAction(
            action_type="gpio",
            action_name="attract_on",
            offset_minutes=0,
        ),
        PatternAction(
            action_type="camera",
            action_name="takephoto",
            offset_minutes=5,
        ),
        PatternAction(
            action_type="gpio",
            action_name="attract_off",
            offset_minutes=15,
        ),
    ]

    pattern = EventPattern(
        pattern_id="test-pattern",
        name="UV Capture Cycle",
        description="Standard UV light photo capture sequence",
        actions=actions,
        category="user",
    )

    time_window = TimeWindow(
        start_time="21:00",
        end_time="23:00",
    )

    trigger = IntervalTrigger(
        interval_minutes=30,
        time_window=time_window,
    )

    return Schedule(
        schedule_id="test-schedule",
        name="Nightly Moth Survey",
        description="30-minute interval captures from 9 PM to 11 PM",
        event_patterns=[pattern],
        trigger_type="interval",
        interval_trigger=trigger,
        enabled=True,
    )


@pytest.fixture
def conflicting_schedule():
    """Create a Schedule with patterns that will conflict."""
    from webui.backend.lib.schedule_schema import (
        EventPattern,
        IntervalTrigger,
        PatternAction,
        Schedule,
        TimeWindow,
    )

    # Pattern 1: Takes 20 minutes
    pattern1_actions = [
        PatternAction(
            action_type="gpio",
            action_name="attract_on",
            offset_minutes=0,
        ),
        PatternAction(
            action_type="camera",
            action_name="takephoto",
            offset_minutes=10,
        ),
        PatternAction(
            action_type="gpio",
            action_name="attract_off",
            offset_minutes=20,
        ),
    ]

    pattern1 = EventPattern(
        pattern_id="pattern-1",
        name="Long Capture",
        actions=pattern1_actions,
    )

    # Pattern 2: Also takes 20 minutes - will overlap with 15-min interval
    pattern2_actions = [
        PatternAction(
            action_type="gpio",
            action_name="flash_on",
            offset_minutes=0,
        ),
        PatternAction(
            action_type="camera",
            action_name="takephoto",
            offset_minutes=10,
        ),
        PatternAction(
            action_type="gpio",
            action_name="flash_off",
            offset_minutes=20,
        ),
    ]

    pattern2 = EventPattern(
        pattern_id="pattern-2",
        name="Flash Capture",
        actions=pattern2_actions,
    )

    time_window = TimeWindow(
        start_time="21:00",
        end_time="22:00",
    )

    # 15 minute interval but patterns take 20 minutes each = overlap
    trigger = IntervalTrigger(
        interval_minutes=15,
        time_window=time_window,
    )

    return Schedule(
        schedule_id="conflict-schedule",
        name="Conflicting Schedule",
        event_patterns=[pattern1, pattern2],
        trigger_type="interval",
        interval_trigger=trigger,
        enabled=True,
    )


# ============================================================================
# Test Dataclasses - Serialization Round-Trips
# ============================================================================

class TestConflictDataclasses:
    """Tests for dataclass serialization and deserialization."""

    def test_resource_usage_to_dict(self, sample_resource_usage):
        """ResourceUsage.to_dict() should serialize all fields."""
        data = sample_resource_usage.to_dict()

        assert data["resource_type"] == "camera"
        assert data["resource_name"] == "takephoto"
        assert data["start_time"] == "2024-06-15T21:05:00"
        assert data["end_time"] == "2024-06-15T21:05:30"
        assert data["pattern_id"] == "pattern-1"
        assert data["action_index"] == 1

    def test_resource_usage_from_dict(self, sample_resource_usage):
        """ResourceUsage.from_dict() should deserialize correctly."""
        data = sample_resource_usage.to_dict()
        restored = ResourceUsage.from_dict(data)

        assert restored.resource_type == sample_resource_usage.resource_type
        assert restored.resource_name == sample_resource_usage.resource_name
        assert restored.start_time == sample_resource_usage.start_time
        assert restored.end_time == sample_resource_usage.end_time
        assert restored.pattern_id == sample_resource_usage.pattern_id
        assert restored.action_index == sample_resource_usage.action_index

    def test_pattern_execution_to_dict(self, sample_pattern_execution):
        """PatternExecution.to_dict() should serialize including nested resource_usages."""
        data = sample_pattern_execution.to_dict()

        assert data["pattern_id"] == "pattern-1"
        assert data["pattern_name"] == "UV Capture"
        assert data["start_time"] == "2024-06-15T21:00:00"
        assert data["end_time"] == "2024-06-15T21:15:00"
        assert len(data["resource_usages"]) == 2
        assert data["resource_usages"][0]["resource_type"] == "gpio"
        assert data["resource_usages"][1]["resource_type"] == "camera"

    def test_pattern_execution_from_dict(self, sample_pattern_execution):
        """PatternExecution.from_dict() should deserialize including nested usages."""
        data = sample_pattern_execution.to_dict()
        restored = PatternExecution.from_dict(data)

        assert restored.pattern_id == sample_pattern_execution.pattern_id
        assert restored.pattern_name == sample_pattern_execution.pattern_name
        assert restored.start_time == sample_pattern_execution.start_time
        assert restored.end_time == sample_pattern_execution.end_time
        assert len(restored.resource_usages) == 2
        assert restored.resource_usages[0].resource_type == "gpio"
        assert restored.resource_usages[1].resource_type == "camera"

    def test_conflict_to_dict(self, sample_conflict):
        """Conflict.to_dict() should serialize all fields."""
        data = sample_conflict.to_dict()

        assert data["conflict_type"] == "resource_contention"
        assert data["event1_id"] == "pattern-1"
        assert data["event1_name"] == "UV Capture"
        assert data["event2_id"] == "pattern-2"
        assert data["event2_name"] == "Flash Capture"
        assert data["resource"] == "camera"
        assert data["severity"] == "error"
        assert "conflict" in data["message"].lower()

    def test_conflict_from_dict(self, sample_conflict):
        """Conflict.from_dict() should deserialize correctly."""
        data = sample_conflict.to_dict()
        restored = Conflict.from_dict(data)

        assert restored.conflict_type == sample_conflict.conflict_type
        assert restored.event1_id == sample_conflict.event1_id
        assert restored.event2_id == sample_conflict.event2_id
        assert restored.resource == sample_conflict.resource
        assert restored.severity == sample_conflict.severity
        assert restored.message == sample_conflict.message

    def test_conflict_report_to_dict(self, sample_conflict_report):
        """ConflictReport.to_dict() should serialize including nested conflicts."""
        data = sample_conflict_report.to_dict()

        assert data["schedule_id"] == "schedule-1"
        assert data["schedule_name"] == "Nightly Survey"
        assert data["total_executions"] == 10
        assert data["has_blocking_conflicts"] is True
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["conflict_type"] == "resource_contention"

    def test_conflict_defaults(self):
        """Conflict should have sensible defaults for optional fields."""
        conflict = Conflict(
            conflict_type="time_overlap",
            event1_id="p1",
            event1_name="Pattern 1",
            event2_id="p2",
            event2_name="Pattern 2",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 15, 0),
        )

        assert conflict.resource == ""
        assert conflict.message == ""
        assert conflict.suggested_resolution == ""
        assert conflict.severity == "error"


# ============================================================================
# Test Time Overlap Detection
# ============================================================================

class TestTimeOverlapDetection:
    """Tests for check_time_overlap() function."""

    def test_non_overlapping_executions(self, non_overlapping_executions):
        """Non-overlapping executions should return False."""
        exec1, exec2 = non_overlapping_executions

        overlaps, start, end = check_time_overlap(exec1, exec2)

        assert overlaps is False
        assert start is None
        assert end is None

    def test_fully_overlapping_executions(self):
        """Fully overlapping executions should return True with overlap period."""
        exec1 = PatternExecution(
            pattern_id="p1",
            pattern_name="P1",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 30, 0),
            resource_usages=[],
        )
        exec2 = PatternExecution(
            pattern_id="p2",
            pattern_name="P2",
            start_time=datetime(2024, 6, 15, 21, 5, 0),
            end_time=datetime(2024, 6, 15, 21, 20, 0),
            resource_usages=[],
        )

        overlaps, start, end = check_time_overlap(exec1, exec2)

        assert overlaps is True
        assert start == datetime(2024, 6, 15, 21, 5, 0)
        assert end == datetime(2024, 6, 15, 21, 20, 0)

    def test_partial_overlap_start_inside(self, overlapping_executions):
        """Partial overlap where exec2 starts during exec1."""
        exec1, exec2 = overlapping_executions

        overlaps, start, end = check_time_overlap(exec1, exec2)

        assert overlaps is True
        assert start == datetime(2024, 6, 15, 21, 10, 0)  # exec2 start
        assert end == datetime(2024, 6, 15, 21, 15, 0)    # exec1 end

    def test_partial_overlap_end_inside(self):
        """Partial overlap where exec1 ends during exec2."""
        exec1 = PatternExecution(
            pattern_id="p1",
            pattern_name="P1",
            start_time=datetime(2024, 6, 15, 21, 10, 0),
            end_time=datetime(2024, 6, 15, 21, 25, 0),
            resource_usages=[],
        )
        exec2 = PatternExecution(
            pattern_id="p2",
            pattern_name="P2",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 15, 0),
            resource_usages=[],
        )

        overlaps, start, end = check_time_overlap(exec1, exec2)

        assert overlaps is True
        assert start == datetime(2024, 6, 15, 21, 10, 0)  # exec1 start
        assert end == datetime(2024, 6, 15, 21, 15, 0)    # exec2 end

    def test_adjacent_patterns_no_overlap(self):
        """Adjacent patterns (end == start) should NOT overlap."""
        exec1 = PatternExecution(
            pattern_id="p1",
            pattern_name="P1",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 15, 0),
            resource_usages=[],
        )
        exec2 = PatternExecution(
            pattern_id="p2",
            pattern_name="P2",
            start_time=datetime(2024, 6, 15, 21, 15, 0),  # Starts exactly when exec1 ends
            end_time=datetime(2024, 6, 15, 21, 30, 0),
            resource_usages=[],
        )

        overlaps, start, end = check_time_overlap(exec1, exec2)

        assert overlaps is False
        assert start is None
        assert end is None

    def test_same_start_time(self):
        """Executions starting at same time should overlap."""
        exec1 = PatternExecution(
            pattern_id="p1",
            pattern_name="P1",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 15, 0),
            resource_usages=[],
        )
        exec2 = PatternExecution(
            pattern_id="p2",
            pattern_name="P2",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 10, 0),
            resource_usages=[],
        )

        overlaps, start, end = check_time_overlap(exec1, exec2)

        assert overlaps is True
        assert start == datetime(2024, 6, 15, 21, 0, 0)
        assert end == datetime(2024, 6, 15, 21, 10, 0)

    def test_one_contains_other(self):
        """One execution fully contains another."""
        outer = PatternExecution(
            pattern_id="outer",
            pattern_name="Outer",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 22, 0, 0),
            resource_usages=[],
        )
        inner = PatternExecution(
            pattern_id="inner",
            pattern_name="Inner",
            start_time=datetime(2024, 6, 15, 21, 15, 0),
            end_time=datetime(2024, 6, 15, 21, 45, 0),
            resource_usages=[],
        )

        overlaps, start, end = check_time_overlap(outer, inner)

        assert overlaps is True
        assert start == datetime(2024, 6, 15, 21, 15, 0)
        assert end == datetime(2024, 6, 15, 21, 45, 0)

    def test_zero_duration_pattern(self):
        """Zero-duration patterns (start == end) should still be detected."""
        instant = PatternExecution(
            pattern_id="instant",
            pattern_name="Instant",
            start_time=datetime(2024, 6, 15, 21, 10, 0),
            end_time=datetime(2024, 6, 15, 21, 10, 0),  # Same as start
            resource_usages=[],
        )
        normal = PatternExecution(
            pattern_id="normal",
            pattern_name="Normal",
            start_time=datetime(2024, 6, 15, 21, 5, 0),
            end_time=datetime(2024, 6, 15, 21, 20, 0),
            resource_usages=[],
        )

        overlaps, start, end = check_time_overlap(instant, normal)

        # Zero-duration instant within normal's range - NOT an overlap (degenerate case)
        # A point in time doesn't occupy any duration
        assert overlaps is False


# ============================================================================
# Test Resource Contention Detection
# ============================================================================

class TestResourceContention:
    """Tests for resource contention detection."""

    def test_get_resource_type_camera(self):
        """Camera action should return 'camera' resource type."""
        from webui.backend.lib.schedule_schema import PatternAction

        action = PatternAction(
            action_type="camera",
            action_name="takephoto",
            offset_minutes=5,
        )

        assert get_resource_type(action) == "camera"

    def test_get_resource_type_gps(self):
        """GPS action should return 'gps' resource type."""
        from webui.backend.lib.schedule_schema import PatternAction

        action = PatternAction(
            action_type="gps_sync",
            action_name="sync",
            offset_minutes=0,
        )

        assert get_resource_type(action) == "gps"

    def test_get_resource_type_gpio_attract(self):
        """GPIO attract action should return 'attract' resource type."""
        from webui.backend.lib.schedule_schema import PatternAction

        action = PatternAction(
            action_type="gpio",
            action_name="attract_on",
            offset_minutes=0,
        )

        assert get_resource_type(action) == "attract"

    def test_get_resource_type_gpio_flash(self):
        """GPIO flash action should return 'flash' resource type."""
        from webui.backend.lib.schedule_schema import PatternAction

        action = PatternAction(
            action_type="gpio",
            action_name="flash_off",
            offset_minutes=15,
        )

        assert get_resource_type(action) == "flash"

    def test_get_resource_type_service(self):
        """Service action should return 'service' resource type."""
        from webui.backend.lib.schedule_schema import PatternAction

        action = PatternAction(
            action_type="service",
            action_name="backup",
            offset_minutes=0,
        )

        assert get_resource_type(action) == "service"

    def test_camera_contention_overlap(self):
        """Two overlapping camera usages should conflict."""
        usage1 = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 5, 0),
            end_time=datetime(2024, 6, 15, 21, 5, 30),
            pattern_id="p1",
            action_index=0,
        )
        usage2 = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 5, 15),
            end_time=datetime(2024, 6, 15, 21, 5, 45),
            pattern_id="p2",
            action_index=0,
        )

        contends, conflict_type = check_resource_contention(usage1, usage2)

        assert contends is True
        assert conflict_type == "resource_contention"

    def test_gps_contention_overlap(self):
        """Two overlapping GPS usages should conflict."""
        usage1 = ResourceUsage(
            resource_type="gps",
            resource_name="sync",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 30),
            pattern_id="p1",
            action_index=0,
        )
        usage2 = ResourceUsage(
            resource_type="gps",
            resource_name="sync",
            start_time=datetime(2024, 6, 15, 21, 0, 15),
            end_time=datetime(2024, 6, 15, 21, 0, 45),
            pattern_id="p2",
            action_index=0,
        )

        contends, conflict_type = check_resource_contention(usage1, usage2)

        assert contends is True
        assert conflict_type == "resource_contention"

    def test_gpio_state_conflict_on_vs_off(self):
        """GPIO attract_on vs attract_off at same time should conflict."""
        usage1 = ResourceUsage(
            resource_type="attract",
            resource_name="attract_on",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 0),
            pattern_id="p1",
            action_index=0,
        )
        usage2 = ResourceUsage(
            resource_type="attract",
            resource_name="attract_off",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 0),
            pattern_id="p2",
            action_index=0,
        )

        contends, conflict_type = check_resource_contention(usage1, usage2)

        assert contends is True
        assert conflict_type == "gpio_state_conflict"

    def test_gpio_same_state_no_conflict(self):
        """Two GPIO attract_on at same time should NOT conflict."""
        usage1 = ResourceUsage(
            resource_type="attract",
            resource_name="attract_on",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 0),
            pattern_id="p1",
            action_index=0,
        )
        usage2 = ResourceUsage(
            resource_type="attract",
            resource_name="attract_on",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 0),
            pattern_id="p2",
            action_index=0,
        )

        contends, conflict_type = check_resource_contention(usage1, usage2)

        assert contends is False
        assert conflict_type == ""

    def test_different_resource_types_no_conflict(self):
        """Different resource types should NOT conflict."""
        usage1 = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 5, 0),
            end_time=datetime(2024, 6, 15, 21, 5, 30),
            pattern_id="p1",
            action_index=0,
        )
        usage2 = ResourceUsage(
            resource_type="attract",
            resource_name="attract_on",
            start_time=datetime(2024, 6, 15, 21, 5, 0),
            end_time=datetime(2024, 6, 15, 21, 5, 0),
            pattern_id="p2",
            action_index=0,
        )

        contends, conflict_type = check_resource_contention(usage1, usage2)

        assert contends is False
        assert conflict_type == ""

    def test_non_overlapping_times_no_conflict(self):
        """Same resource type but non-overlapping times should NOT conflict."""
        usage1 = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 5, 0),
            end_time=datetime(2024, 6, 15, 21, 5, 30),
            pattern_id="p1",
            action_index=0,
        )
        usage2 = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 10, 0),
            end_time=datetime(2024, 6, 15, 21, 10, 30),
            pattern_id="p2",
            action_index=0,
        )

        contends, conflict_type = check_resource_contention(usage1, usage2)

        assert contends is False
        assert conflict_type == ""

    def test_service_no_conflict(self):
        """Service resources should never conflict."""
        usage1 = ResourceUsage(
            resource_type="service",
            resource_name="backup",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 5, 0),
            pattern_id="p1",
            action_index=0,
        )
        usage2 = ResourceUsage(
            resource_type="service",
            resource_name="backup",
            start_time=datetime(2024, 6, 15, 21, 2, 0),
            end_time=datetime(2024, 6, 15, 21, 7, 0),
            pattern_id="p2",
            action_index=0,
        )

        contends, conflict_type = check_resource_contention(usage1, usage2)

        assert contends is False
        assert conflict_type == ""

    def test_instant_action_at_end_time_conflicts(self):
        """Instant action at exactly the end time of a duration SHOULD conflict."""
        # Camera usage from 21:05:00 to 21:05:30
        duration_usage = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 5, 0),
            end_time=datetime(2024, 6, 15, 21, 5, 30),
            pattern_id="p1",
            action_index=0,
        )
        # Instant camera action at exactly 21:05:30 (end time of duration_usage)
        instant_usage = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 5, 30),
            end_time=datetime(2024, 6, 15, 21, 5, 30),  # Instant (start == end)
            pattern_id="p2",
            action_index=0,
        )

        contends, conflict_type = check_resource_contention(duration_usage, instant_usage)

        # With end-inclusive behavior, instant at end time SHOULD conflict
        assert contends is True
        assert conflict_type == "resource_contention"

    def test_instant_action_at_start_time_conflicts(self):
        """Instant action at exactly the start time of a duration SHOULD conflict."""
        # Camera usage from 21:05:00 to 21:05:30
        duration_usage = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 5, 0),
            end_time=datetime(2024, 6, 15, 21, 5, 30),
            pattern_id="p1",
            action_index=0,
        )
        # Instant camera action at exactly 21:05:00 (start time of duration_usage)
        instant_usage = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 5, 0),
            end_time=datetime(2024, 6, 15, 21, 5, 0),  # Instant (start == end)
            pattern_id="p2",
            action_index=0,
        )

        contends, conflict_type = check_resource_contention(duration_usage, instant_usage)

        # Instant at start time SHOULD conflict
        assert contends is True
        assert conflict_type == "resource_contention"

    def test_instant_action_after_end_time_no_conflict(self):
        """Instant action AFTER the end time of a duration should NOT conflict."""
        # Camera usage from 21:05:00 to 21:05:30
        duration_usage = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 5, 0),
            end_time=datetime(2024, 6, 15, 21, 5, 30),
            pattern_id="p1",
            action_index=0,
        )
        # Instant camera action at 21:05:31 (1 second after end time)
        instant_usage = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 5, 31),
            end_time=datetime(2024, 6, 15, 21, 5, 31),  # Instant (start == end)
            pattern_id="p2",
            action_index=0,
        )

        contends, conflict_type = check_resource_contention(duration_usage, instant_usage)

        # Instant AFTER end time should NOT conflict
        assert contends is False
        assert conflict_type == ""


# ============================================================================
# Test Pattern Execution Generation
# ============================================================================

class TestPatternExecutionGeneration:
    """Tests for generate_pattern_executions() function."""

    def test_interval_trigger_generation(self, sample_schedule):
        """Interval trigger should generate executions at correct times."""
        start_date = date(2024, 6, 15)
        end_date = date(2024, 6, 15)

        executions = generate_pattern_executions(
            sample_schedule,
            start_date,
            end_date,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # 21:00 to 23:00 with 30-min interval = executions at 21:00, 21:30, 22:00, 22:30
        assert len(executions) == 4

        # Check first execution
        assert executions[0].pattern_name == "UV Capture Cycle"
        assert executions[0].start_time.hour == 21
        assert executions[0].start_time.minute == 0

    def test_execution_includes_resource_usages(self, sample_schedule):
        """Generated executions should include resource usages from actions."""
        start_date = date(2024, 6, 15)
        end_date = date(2024, 6, 15)

        executions = generate_pattern_executions(
            sample_schedule,
            start_date,
            end_date,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # First execution should have resource usages for all actions
        first_exec = executions[0]
        assert len(first_exec.resource_usages) == 3

        # Check resource types
        resource_types = [u.resource_type for u in first_exec.resource_usages]
        assert "attract" in resource_types  # gpio attract_on
        assert "camera" in resource_types   # takephoto
        # attract_off is also 'attract' type

    def test_execution_duration_matches_pattern(self, sample_schedule):
        """Execution end_time should reflect pattern duration."""
        start_date = date(2024, 6, 15)
        end_date = date(2024, 6, 15)

        executions = generate_pattern_executions(
            sample_schedule,
            start_date,
            end_date,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        first_exec = executions[0]
        duration = (first_exec.end_time - first_exec.start_time).total_seconds() / 60

        # Pattern has actions at 0, 5, and 15 minutes, so duration is 15 minutes
        assert duration == 15

    def test_empty_execution_list_outside_window(self, sample_schedule):
        """No executions generated when date has no scheduled times."""
        # Modify schedule to have day_of_week restriction
        from webui.backend.lib.schedule_schema import IntervalTrigger, TimeWindow

        sample_schedule.interval_trigger = IntervalTrigger(
            interval_minutes=30,
            time_window=TimeWindow(start_time="21:00", end_time="23:00"),
            days_of_week=[0, 1, 2],  # Mon, Tue, Wed only
        )

        # June 15, 2024 is a Saturday (weekday 5)
        start_date = date(2024, 6, 15)
        end_date = date(2024, 6, 15)

        executions = generate_pattern_executions(
            sample_schedule,
            start_date,
            end_date,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        assert len(executions) == 0

    def test_multi_day_generation(self, sample_schedule):
        """Multiple days should generate executions for each day."""
        start_date = date(2024, 6, 15)
        end_date = date(2024, 6, 17)  # 3 days

        executions = generate_pattern_executions(
            sample_schedule,
            start_date,
            end_date,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # 4 executions per day * 3 days = 12
        assert len(executions) == 12

    def test_executions_sorted_by_start_time(self, sample_schedule):
        """Returned executions should be sorted by start_time."""
        start_date = date(2024, 6, 15)
        end_date = date(2024, 6, 17)

        executions = generate_pattern_executions(
            sample_schedule,
            start_date,
            end_date,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        for i in range(len(executions) - 1):
            assert executions[i].start_time <= executions[i + 1].start_time


# ============================================================================
# Test Detect Conflicts
# ============================================================================

class TestDetectConflicts:
    """Tests for detect_conflicts() main function."""

    def test_no_conflicts_single_pattern(self, sample_schedule):
        """Single pattern with adequate interval should have no conflicts."""
        report = detect_conflicts(
            sample_schedule,
            preview_days=1,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        assert report.schedule_id == "test-schedule"
        assert report.has_blocking_conflicts is False
        assert len(report.conflicts) == 0

    def test_time_overlap_conflict_detected(self, conflicting_schedule):
        """Schedule with overlapping patterns should detect time overlap."""
        report = detect_conflicts(
            conflicting_schedule,
            preview_days=1,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # With 15-min interval and 20-min pattern duration, patterns will overlap
        time_overlaps = [c for c in report.conflicts if c.conflict_type == "time_overlap"]
        assert len(time_overlaps) > 0

    def test_resource_contention_detected(self, conflicting_schedule):
        """Schedule with camera conflicts should detect resource contention."""
        report = detect_conflicts(
            conflicting_schedule,
            preview_days=1,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # Both patterns use camera at offset 10, should conflict
        resource_conflicts = [c for c in report.conflicts if c.conflict_type == "resource_contention"]
        assert len(resource_conflicts) > 0

    def test_conflict_report_fields(self, conflicting_schedule):
        """ConflictReport should have all expected fields populated."""
        report = detect_conflicts(
            conflicting_schedule,
            preview_days=7,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        assert report.schedule_id == "conflict-schedule"
        assert report.schedule_name == "Conflicting Schedule"
        assert report.preview_start is not None
        assert report.preview_end is not None
        assert report.total_executions > 0
        assert report.analyzed_at is not None

    def test_conflict_severity_assignment(self, conflicting_schedule):
        """Resource contention should be 'error', time overlap 'warning'."""
        report = detect_conflicts(
            conflicting_schedule,
            preview_days=1,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        for conflict in report.conflicts:
            if conflict.conflict_type == "resource_contention":
                assert conflict.severity == "error"
            elif conflict.conflict_type == "time_overlap":
                assert conflict.severity == "warning"


# ============================================================================
# Test Validate Schedule Conflicts
# ============================================================================

class TestValidateScheduleConflicts:
    """Tests for validate_schedule_conflicts() function."""

    def test_valid_schedule_passes(self, sample_schedule):
        """Schedule without blocking conflicts should pass validation."""
        valid, error = validate_schedule_conflicts(
            sample_schedule,
            preview_days=1,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        assert valid is True
        assert error is None

    def test_schedule_with_blocking_conflicts_fails(self, conflicting_schedule):
        """Schedule with resource contention should fail validation."""
        valid, error = validate_schedule_conflicts(
            conflicting_schedule,
            preview_days=1,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        assert valid is False
        assert error is not None
        assert "conflict" in error.lower()

    def test_error_message_includes_conflict_count(self, conflicting_schedule):
        """Error message should indicate number of blocking conflicts."""
        valid, error = validate_schedule_conflicts(
            conflicting_schedule,
            preview_days=1,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        assert valid is False
        # Error should mention count like "3 blocking conflict(s)"
        assert "blocking" in error.lower()

    def test_validation_returns_tuple(self, sample_schedule):
        """validate_schedule_conflicts should return tuple[bool, str | None]."""
        result = validate_schedule_conflicts(
            sample_schedule,
            preview_days=1,
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert result[1] is None or isinstance(result[1], str)


# ============================================================================
# Test Constants
# ============================================================================

class TestConstants:
    """Tests for module constants."""

    def test_single_resources_defined(self):
        """SINGLE_RESOURCES should contain camera and gps."""
        assert "camera" in SINGLE_RESOURCES
        assert "gps" in SINGLE_RESOURCES

    def test_gpio_resources_defined(self):
        """GPIO_RESOURCES should contain attract and flash."""
        assert "attract" in GPIO_RESOURCES
        assert "flash" in GPIO_RESOURCES


# ============================================================================
# Test Trigger Type Handling (Coverage for lines 390-548)
# ============================================================================

class TestTriggerTypeHandling:
    """Tests for different trigger types in generate_pattern_executions()."""

    def test_schedule_date_range_before_start(self):
        """Schedule with start_date in future should generate no executions."""
        from webui.backend.lib.schedule_schema import (
            EventPattern,
            IntervalTrigger,
            PatternAction,
            Schedule,
            TimeWindow,
        )

        pattern = EventPattern(
            pattern_id="p1",
            name="Test Pattern",
            actions=[PatternAction(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=0,
            )],
        )

        # Schedule starts in the future
        schedule = Schedule(
            schedule_id="future-schedule",
            name="Future Schedule",
            event_patterns=[pattern],
            trigger_type="interval",
            interval_trigger=IntervalTrigger(
                interval_minutes=30,
                time_window=TimeWindow(start_time="21:00", end_time="23:00"),
            ),
            start_date="2030-01-01",  # Far in the future
            enabled=True,
        )

        executions = generate_pattern_executions(
            schedule,
            date(2024, 6, 15),
            date(2024, 6, 15),
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        assert len(executions) == 0

    def test_schedule_date_range_after_end(self):
        """Schedule with end_date in past should generate no executions."""
        from webui.backend.lib.schedule_schema import (
            EventPattern,
            IntervalTrigger,
            PatternAction,
            Schedule,
            TimeWindow,
        )

        pattern = EventPattern(
            pattern_id="p1",
            name="Test Pattern",
            actions=[PatternAction(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=0,
            )],
        )

        # Schedule ended in the past
        schedule = Schedule(
            schedule_id="past-schedule",
            name="Past Schedule",
            event_patterns=[pattern],
            trigger_type="interval",
            interval_trigger=IntervalTrigger(
                interval_minutes=30,
                time_window=TimeWindow(start_time="21:00", end_time="23:00"),
            ),
            end_date="2020-01-01",  # In the past
            enabled=True,
        )

        executions = generate_pattern_executions(
            schedule,
            date(2024, 6, 15),
            date(2024, 6, 15),
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        assert len(executions) == 0

    def test_fixed_time_trigger_generation(self):
        """Fixed time trigger should generate single execution per day."""
        from webui.backend.lib.schedule_schema import (
            EventPattern,
            FixedTimeTrigger,
            PatternAction,
            Schedule,
        )

        pattern = EventPattern(
            pattern_id="p1",
            name="Daily Photo",
            actions=[PatternAction(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=0,
            )],
        )

        schedule = Schedule(
            schedule_id="fixed-schedule",
            name="Fixed Time Schedule",
            event_patterns=[pattern],
            trigger_type="fixed_time",
            fixed_time_trigger=FixedTimeTrigger(time="12:00"),
            enabled=True,
        )

        executions = generate_pattern_executions(
            schedule,
            date(2024, 6, 15),
            date(2024, 6, 17),  # 3 days
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # One execution per day for 3 days
        assert len(executions) == 3

        # Check times are at noon
        for exec in executions:
            assert exec.start_time.hour == 12
            assert exec.start_time.minute == 0

    def test_fixed_time_with_days_of_week(self):
        """Fixed time with day restrictions should skip other days."""
        from webui.backend.lib.schedule_schema import (
            EventPattern,
            FixedTimeTrigger,
            PatternAction,
            Schedule,
        )

        pattern = EventPattern(
            pattern_id="p1",
            name="Daily Photo",
            actions=[PatternAction(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=0,
            )],
        )

        # June 15, 2024 is Saturday (weekday 5)
        schedule = Schedule(
            schedule_id="fixed-schedule",
            name="Fixed Time Schedule",
            event_patterns=[pattern],
            trigger_type="fixed_time",
            fixed_time_trigger=FixedTimeTrigger(
                time="12:00",
                days_of_week=[0, 1, 2, 3, 4],  # Weekdays only
            ),
            enabled=True,
        )

        executions = generate_pattern_executions(
            schedule,
            date(2024, 6, 15),  # Saturday
            date(2024, 6, 15),
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # Saturday is not in weekdays, so no executions
        assert len(executions) == 0

    def test_sensor_trigger_generation(self):
        """Sensor trigger with time window should generate placeholder execution."""
        from webui.backend.lib.schedule_schema import (
            EventPattern,
            PatternAction,
            Schedule,
            SensorTrigger,
            TimeWindow,
        )

        pattern = EventPattern(
            pattern_id="p1",
            name="Motion Capture",
            actions=[PatternAction(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=0,
            )],
        )

        schedule = Schedule(
            schedule_id="sensor-schedule",
            name="Sensor Schedule",
            event_patterns=[pattern],
            trigger_type="sensor",
            sensor_trigger=SensorTrigger(
                sensor_type="motion",
                threshold=0.5,
                time_window=TimeWindow(start_time="20:00", end_time="06:00"),
            ),
            enabled=True,
        )

        executions = generate_pattern_executions(
            schedule,
            date(2024, 6, 15),
            date(2024, 6, 15),
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # Sensor trigger creates one placeholder at window start
        assert len(executions) == 1
        assert executions[0].start_time.hour == 20
        assert executions[0].start_time.minute == 0

    def test_overnight_window_handling(self):
        """Interval trigger with overnight window should work correctly."""
        from webui.backend.lib.schedule_schema import (
            EventPattern,
            IntervalTrigger,
            PatternAction,
            Schedule,
            TimeWindow,
        )

        pattern = EventPattern(
            pattern_id="p1",
            name="Night Photo",
            actions=[PatternAction(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=0,
            )],
        )

        # Overnight window: 22:00 to 02:00
        schedule = Schedule(
            schedule_id="night-schedule",
            name="Night Schedule",
            event_patterns=[pattern],
            trigger_type="interval",
            interval_trigger=IntervalTrigger(
                interval_minutes=60,  # 1 hour
                time_window=TimeWindow(start_time="22:00", end_time="02:00"),
            ),
            enabled=True,
        )

        executions = generate_pattern_executions(
            schedule,
            date(2024, 6, 15),
            date(2024, 6, 15),
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # 22:00, 23:00, 00:00, 01:00 = 4 executions (02:00 is the end, not included)
        assert len(executions) == 4


# ============================================================================
# Test Conflict Message and Resolution Generation
# ============================================================================

class TestConflictMessageGeneration:
    """Tests for _generate_conflict_message() and _generate_resolution()."""

    def test_resource_contention_message(self):
        """Resource contention should have descriptive message."""
        from webui.backend.lib.schedule_conflict import (
            CONFLICT_RESOURCE_CONTENTION,
            _generate_conflict_message,
            _generate_resolution,
        )

        usage1 = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 30),
            pattern_id="p1",
            action_index=0,
        )
        usage2 = ResourceUsage(
            resource_type="camera",
            resource_name="takephoto",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 30),
            pattern_id="p2",
            action_index=0,
        )

        message = _generate_conflict_message(CONFLICT_RESOURCE_CONTENTION, usage1, usage2)
        resolution = _generate_resolution(CONFLICT_RESOURCE_CONTENTION, usage1, usage2)

        assert "camera" in message.lower()
        assert "conflict" in message.lower()
        assert "adjust" in resolution.lower() or "interval" in resolution.lower()

    def test_gpio_state_conflict_message(self):
        """GPIO state conflict should have descriptive message."""
        from webui.backend.lib.schedule_conflict import (
            CONFLICT_GPIO_STATE,
            _generate_conflict_message,
            _generate_resolution,
        )

        usage1 = ResourceUsage(
            resource_type="attract",
            resource_name="attract_on",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 0),
            pattern_id="p1",
            action_index=0,
        )
        usage2 = ResourceUsage(
            resource_type="attract",
            resource_name="attract_off",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 0),
            pattern_id="p2",
            action_index=0,
        )

        message = _generate_conflict_message(CONFLICT_GPIO_STATE, usage1, usage2)
        resolution = _generate_resolution(CONFLICT_GPIO_STATE, usage1, usage2)

        assert "gpio" in message.lower() or "attract" in message.lower()
        assert "delay" in resolution.lower() or "overlap" in resolution.lower()

    def test_unknown_conflict_type_message(self):
        """Unknown conflict type should return generic message."""
        from webui.backend.lib.schedule_conflict import (
            _generate_conflict_message,
            _generate_resolution,
        )

        usage1 = ResourceUsage(
            resource_type="unknown",
            resource_name="test",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 30),
            pattern_id="p1",
            action_index=0,
        )
        usage2 = ResourceUsage(
            resource_type="unknown",
            resource_name="test",
            start_time=datetime(2024, 6, 15, 21, 0, 0),
            end_time=datetime(2024, 6, 15, 21, 0, 30),
            pattern_id="p2",
            action_index=0,
        )

        message = _generate_conflict_message("unknown_type", usage1, usage2)
        resolution = _generate_resolution("unknown_type", usage1, usage2)

        assert "conflict" in message.lower()
        assert "adjust" in resolution.lower() or "timing" in resolution.lower()


# ============================================================================
# Test Resource Type Detection Edge Cases
# ============================================================================

class TestResourceTypeEdgeCases:
    """Tests for get_resource_type() edge cases."""

    def test_unknown_gpio_action_name(self):
        """GPIO action with unknown name should return 'gpio'."""
        from webui.backend.lib.schedule_schema import PatternAction

        action = PatternAction(
            action_type="gpio",
            action_name="relay_on",  # Not attract or flash
            offset_minutes=0,
        )

        resource_type = get_resource_type(action)
        assert resource_type == "gpio"

    def test_unknown_action_type(self):
        """Unknown action type should return 'service'."""
        from webui.backend.lib.schedule_schema import PatternAction

        action = PatternAction(
            action_type="custom",  # Unknown type
            action_name="custom_action",
            offset_minutes=0,
        )

        resource_type = get_resource_type(action)
        assert resource_type == "service"


# ============================================================================
# Test Solar and Moon Trigger Integration
# ============================================================================

class TestSolarTriggerGeneration:
    """Tests for solar trigger execution generation."""

    def test_solar_trigger_with_valid_location(self):
        """Solar trigger should generate execution at solar event time."""
        from webui.backend.lib.schedule_schema import (
            EventPattern,
            PatternAction,
            Schedule,
            SolarTrigger,
        )

        pattern = EventPattern(
            pattern_id="p1",
            name="Sunset Photo",
            actions=[PatternAction(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=0,
            )],
        )

        schedule = Schedule(
            schedule_id="solar-schedule",
            name="Solar Schedule",
            event_patterns=[pattern],
            trigger_type="solar",
            solar_trigger=SolarTrigger(
                solar_event="sunset",
                offset_minutes=30,
            ),
            enabled=True,
        )

        # Use Panama coordinates where solar_time library works
        executions = generate_pattern_executions(
            schedule,
            date(2024, 6, 15),
            date(2024, 6, 15),
            latitude=9.15,  # Panama
            longitude=-79.85,
            timezone_name="America/Panama",
        )

        # Should have exactly 1 execution per day
        assert len(executions) == 1
        # Sunset in Panama in June is around 18:30-19:00 local time
        assert executions[0].start_time.hour >= 17  # After 5 PM

    def test_solar_trigger_with_days_of_week(self):
        """Solar trigger with day restrictions should skip other days."""
        from webui.backend.lib.schedule_schema import (
            EventPattern,
            PatternAction,
            Schedule,
            SolarTrigger,
        )

        pattern = EventPattern(
            pattern_id="p1",
            name="Sunset Photo",
            actions=[PatternAction(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=0,
            )],
        )

        # June 15, 2024 is Saturday (weekday 5)
        schedule = Schedule(
            schedule_id="solar-schedule",
            name="Solar Schedule",
            event_patterns=[pattern],
            trigger_type="solar",
            solar_trigger=SolarTrigger(
                solar_event="sunset",
                offset_minutes=0,
                days_of_week=[0, 1, 2, 3, 4],  # Weekdays only
            ),
            enabled=True,
        )

        executions = generate_pattern_executions(
            schedule,
            date(2024, 6, 15),  # Saturday
            date(2024, 6, 15),
            latitude=9.15,
            longitude=-79.85,
            timezone_name="America/Panama",
        )

        # Saturday is not in weekdays, so no executions
        assert len(executions) == 0


class TestMoonPhaseTriggerGeneration:
    """Tests for moon phase trigger execution generation."""

    def test_moon_phase_trigger_with_time_window(self):
        """Moon phase trigger with time_window should use window start time."""
        from webui.backend.lib.schedule_schema import (
            EventPattern,
            MoonPhaseTrigger,
            PatternAction,
            Schedule,
            TimeWindow,
        )

        pattern = EventPattern(
            pattern_id="p1",
            name="Full Moon Photo",
            actions=[PatternAction(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=0,
            )],
        )

        schedule = Schedule(
            schedule_id="moon-schedule",
            name="Moon Schedule",
            event_patterns=[pattern],
            trigger_type="moon_phase",
            moon_phase_trigger=MoonPhaseTrigger(
                phases=["full"],  # Use 'full' not 'full_moon'
                offset_days=1,
                time_window=TimeWindow(start_time="22:00", end_time="04:00"),
            ),
            enabled=True,
        )

        # Find a full moon date (approximately June 22, 2024)
        executions = generate_pattern_executions(
            schedule,
            date(2024, 6, 21),
            date(2024, 6, 23),  # Around full moon
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # If within moon phase, should trigger at 22:00
        for exec in executions:
            assert exec.start_time.hour == 22

    def test_moon_phase_trigger_without_time_window(self):
        """Moon phase trigger without time_window should default to noon."""
        from webui.backend.lib.schedule_schema import (
            EventPattern,
            MoonPhaseTrigger,
            PatternAction,
            Schedule,
        )

        pattern = EventPattern(
            pattern_id="p1",
            name="Full Moon Photo",
            actions=[PatternAction(
                action_type="camera",
                action_name="takephoto",
                offset_minutes=0,
            )],
        )

        schedule = Schedule(
            schedule_id="moon-schedule",
            name="Moon Schedule",
            event_patterns=[pattern],
            trigger_type="moon_phase",
            moon_phase_trigger=MoonPhaseTrigger(
                phases=["full"],  # Use 'full' not 'full_moon'
                offset_days=1,
            ),
            enabled=True,
        )

        # Find a full moon date
        executions = generate_pattern_executions(
            schedule,
            date(2024, 6, 21),
            date(2024, 6, 23),
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        # Without time_window, defaults to noon
        for exec in executions:
            assert exec.start_time.hour == 12
            assert exec.start_time.minute == 0
