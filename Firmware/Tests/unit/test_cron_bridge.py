"""Unit tests for cron_bridge module - Subtask 1: Data structures."""

from datetime import date, datetime
from unittest.mock import mock_open, patch

import pytest

from webui.backend.lib.cron_bridge import (
    CronBridgeResult,
    CronEntry,
    apply_to_system,
    calculate_next_from_entries,
    calculate_next_waketime,
    clear_rtc_wakealarm,
    fixed_time_trigger_to_cron,
    get_next_events,
    get_solar_execution_time,
    interval_trigger_to_cron,
    is_moon_phase_active,
    moon_phase_trigger_to_cron,
    remove_from_system,
    routine_to_cron_entries,
    schedule_to_cron,
    sensor_trigger_to_cron,
    set_rtc_wakealarm,
    solar_trigger_to_cron,
)
from webui.backend.lib.schedule_schema import (
    Action,
    FixedTimeTrigger,
    IntervalTrigger,
    MoonPhaseTrigger,
    Routine,
    Schedule,
    SensorTrigger,
    SolarTrigger,
    TimeWindow,
)


class TestCronEntryDataclass:
    """Test CronEntry dataclass."""

    def test_instantiation_minimal(self):
        """CronEntry can be created with minimal args."""
        entry = CronEntry(expression="0 21 * * *", command="/usr/bin/python3 /opt/mothbox/TakePhoto.py")
        assert entry.expression == "0 21 * * *"
        assert entry.command == "/usr/bin/python3 /opt/mothbox/TakePhoto.py"
        assert entry.comment == ""  # default
        assert entry.enabled is True  # default

    def test_instantiation_full(self):
        """CronEntry can be created with all args."""
        entry = CronEntry(
            expression="*/5 * * * *",
            command="/usr/bin/python3 /opt/mothbox/script.py",
            comment="Mothbox: Take photo every 5 minutes",
            enabled=False,
        )
        assert entry.expression == "*/5 * * * *"
        assert entry.comment == "Mothbox: Take photo every 5 minutes"
        assert entry.enabled is False

    def test_to_cron_line_format(self):
        """CronEntry.to_cron_line() returns valid crontab format."""
        entry = CronEntry(expression="0 21 * * *", command="cmd", comment="Test job")
        line = entry.to_cron_line()
        # Format: # comment\nexpression command
        assert "# Test job" in line
        assert "0 21 * * *" in line
        assert "cmd" in line

    def test_to_cron_line_no_comment(self):
        """CronEntry without comment omits comment line."""
        entry = CronEntry(expression="0 21 * * *", command="cmd")
        line = entry.to_cron_line()
        assert line.strip() == "0 21 * * * cmd"

    def test_to_cron_line_disabled(self):
        """Disabled entry should have commented-out command."""
        entry = CronEntry(expression="0 21 * * *", command="cmd", enabled=False)
        line = entry.to_cron_line()
        # Disabled entries should start with #
        assert "# 0 21 * * * cmd" in line or line.strip().startswith("#")

    def test_to_cron_line_sanitizes_comment(self):
        """CronEntry.to_cron_line() sanitizes comments to prevent injection."""
        # Test newline removal
        entry = CronEntry(
            expression="0 21 * * *",
            command="cmd",
            comment="Line1\nLine2\nLine3",
        )
        line = entry.to_cron_line()
        assert "\n" not in line.split("\n")[0]  # First line (comment) has no newlines in content
        assert "Line1 Line2 Line3" in line

        # Test hash removal
        entry2 = CronEntry(
            expression="0 21 * * *",
            command="cmd",
            comment="Test # injection # attempt",
        )
        line2 = entry2.to_cron_line()
        # The sanitized comment should not have extra # characters
        comment_line = line2.split("\n")[0]
        assert comment_line.count("#") == 1  # Only the leading #

    def test_is_valid_expression_valid(self):
        """CronEntry.is_valid_expression() accepts valid cron syntax."""
        assert CronEntry.is_valid_expression("0 21 * * *") is True
        assert CronEntry.is_valid_expression("*/5 * * * *") is True
        assert CronEntry.is_valid_expression("0,30 9-17 * * 1-5") is True
        assert CronEntry.is_valid_expression("0 0 1 1 *") is True
        # Single-value range (start == end) should be valid
        assert CronEntry.is_valid_expression("0 9-9 * * *") is True

    def test_is_valid_expression_invalid(self):
        """CronEntry.is_valid_expression() rejects invalid cron syntax."""
        assert CronEntry.is_valid_expression("invalid") is False
        assert CronEntry.is_valid_expression("60 24 * * *") is False  # Invalid minute/hour
        assert CronEntry.is_valid_expression("") is False
        assert CronEntry.is_valid_expression("* * *") is False  # Too few fields


class TestCronBridgeResult:
    """Test CronBridgeResult dataclass."""

    def test_instantiation(self):
        """CronBridgeResult contains entries and metadata."""
        result = CronBridgeResult(entries=[], rtc_waketime=None, schedule_id="test-123")
        assert result.entries == []
        assert result.rtc_waketime is None
        assert result.schedule_id == "test-123"
        assert result.errors == []

    def test_with_entries_and_errors(self):
        """CronBridgeResult can hold entries and errors."""
        entry = CronEntry(expression="0 21 * * *", command="cmd")
        result = CronBridgeResult(
            entries=[entry],
            rtc_waketime=1718463600,
            schedule_id="test-456",
            errors=["Warning: polar region"]
        )
        assert len(result.entries) == 1
        assert result.rtc_waketime == 1718463600
        assert len(result.errors) == 1


class TestFixedTimeTriggerConversion:
    """Test fixed_time_trigger_to_cron function."""

    def test_simple_daily_fixed_time(self):
        """Fixed time 21:00 daily becomes '0 21 * * *'."""
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        entries = fixed_time_trigger_to_cron(trigger, command="/usr/bin/python3 /opt/mothbox/TakePhoto.py")
        assert len(entries) == 1
        assert entries[0].expression == "0 21 * * *"
        assert "TakePhoto.py" in entries[0].command

    def test_fixed_time_with_days_mon_to_fri(self):
        """Fixed time with days_of_week restriction to weekdays."""
        # ISO weekday: 0=Mon, 1=Tue, ..., 6=Sun
        # Cron weekday: 0=Sun, 1=Mon, ..., 6=Sat
        trigger = FixedTimeTrigger(time="06:30", days_of_week=[0, 1, 2, 3, 4])  # Mon-Fri ISO
        entries = fixed_time_trigger_to_cron(trigger, command="cmd")
        assert len(entries) == 1
        # In cron: Mon=1, Tue=2, ..., Fri=5
        assert entries[0].expression == "30 6 * * 1,2,3,4,5"

    def test_midnight_time(self):
        """00:00 becomes '0 0 * * *'."""
        trigger = FixedTimeTrigger(time="00:00", days_of_week=None)
        entries = fixed_time_trigger_to_cron(trigger, command="cmd")
        assert entries[0].expression == "0 0 * * *"

    def test_weekend_only(self):
        """Saturday and Sunday only (ISO 5,6 -> cron 0,6)."""
        trigger = FixedTimeTrigger(time="09:00", days_of_week=[5, 6])  # Sat, Sun in ISO
        entries = fixed_time_trigger_to_cron(trigger, command="cmd")
        # Cron: Sat=6, Sun=0
        assert entries[0].expression == "0 9 * * 0,6"

    def test_single_day(self):
        """Single day (Wednesday only)."""
        trigger = FixedTimeTrigger(time="14:30", days_of_week=[2])  # Wed in ISO
        entries = fixed_time_trigger_to_cron(trigger, command="cmd")
        # Cron: Wed=3
        assert entries[0].expression == "30 14 * * 3"

    def test_custom_comment_prefix(self):
        """Custom comment prefix is used."""
        trigger = FixedTimeTrigger(time="12:00", days_of_week=None)
        entries = fixed_time_trigger_to_cron(trigger, command="cmd", comment_prefix="Custom:")
        assert "Custom:" in entries[0].comment
        assert "Fixed time 12:00" in entries[0].comment

    def test_cron_entry_properties(self):
        """CronEntry has correct properties (enabled, comment, command)."""
        trigger = FixedTimeTrigger(time="15:45", days_of_week=[0, 2, 4])  # Mon, Wed, Fri
        entries = fixed_time_trigger_to_cron(trigger, command="/usr/bin/test.py")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.enabled is True
        assert "Mothbox:" in entry.comment
        assert entry.command == "/usr/bin/test.py"
        assert entry.expression == "45 15 * * 1,3,5"

    def test_unsorted_days_are_sorted(self):
        """Days of week are sorted in output."""
        # Provide unsorted days
        trigger = FixedTimeTrigger(time="10:00", days_of_week=[4, 1, 3])  # Fri, Tue, Thu (unsorted)
        entries = fixed_time_trigger_to_cron(trigger, command="cmd")
        # Should output sorted: Tue=2, Thu=4, Fri=5
        assert entries[0].expression == "0 10 * * 2,4,5"


class TestIntervalTriggerConversion:
    """Test interval_trigger_to_cron function."""

    def test_hourly_interval_within_window(self):
        """60-minute interval within 21:00-05:00 window generates multiple entries."""
        window = TimeWindow(start_time="21:00", end_time="05:00")
        trigger = IntervalTrigger(interval_minutes=60, time_window=window)
        entries = interval_trigger_to_cron(trigger, command="cmd")
        # Should generate entries at 21:00, 22:00, 23:00, 00:00, 01:00, 02:00, 03:00, 04:00, 05:00
        assert len(entries) == 9
        hours = [int(e.expression.split()[1]) for e in entries]
        assert set(hours) == {21, 22, 23, 0, 1, 2, 3, 4, 5}

    def test_30_minute_interval_short_window(self):
        """30-minute interval in 2-hour window."""
        window = TimeWindow(start_time="20:00", end_time="22:00")
        trigger = IntervalTrigger(interval_minutes=30, time_window=window)
        entries = interval_trigger_to_cron(trigger, command="cmd")
        # 20:00, 20:30, 21:00, 21:30, 22:00 = 5 entries
        assert len(entries) == 5
        # Check times are correct
        expressions = [e.expression for e in entries]
        assert "0 20 * * *" in expressions
        assert "30 20 * * *" in expressions
        assert "0 21 * * *" in expressions
        assert "30 21 * * *" in expressions
        assert "0 22 * * *" in expressions

    def test_interval_with_days_of_week(self):
        """Interval restricted to specific days."""
        window = TimeWindow(start_time="21:00", end_time="23:00")
        trigger = IntervalTrigger(
            interval_minutes=60,
            time_window=window,
            days_of_week=[0, 1, 2, 3, 4],  # Mon-Fri ISO
        )
        entries = interval_trigger_to_cron(trigger, command="cmd")
        # Should have 3 entries (21:00, 22:00, 23:00), each with days_of_week
        assert len(entries) == 3
        for entry in entries:
            assert "1,2,3,4,5" in entry.expression  # Mon-Fri in cron format

    def test_overnight_window(self):
        """Window spanning midnight (22:00-02:00) handled correctly."""
        window = TimeWindow(start_time="22:00", end_time="02:00")
        trigger = IntervalTrigger(interval_minutes=60, time_window=window)
        entries = interval_trigger_to_cron(trigger, command="cmd")
        # 22:00, 23:00, 00:00, 01:00, 02:00 = 5 entries
        assert len(entries) == 5
        hours = [int(e.expression.split()[1]) for e in entries]
        assert 22 in hours
        assert 23 in hours
        assert 0 in hours
        assert 1 in hours
        assert 2 in hours

    def test_15_minute_interval(self):
        """15-minute interval within single hour."""
        window = TimeWindow(start_time="21:00", end_time="22:00")
        trigger = IntervalTrigger(interval_minutes=15, time_window=window)
        entries = interval_trigger_to_cron(trigger, command="cmd")
        # 21:00, 21:15, 21:30, 21:45, 22:00 = 5 entries
        assert len(entries) == 5
        expressions = [e.expression for e in entries]
        assert "0 21 * * *" in expressions
        assert "15 21 * * *" in expressions
        assert "30 21 * * *" in expressions
        assert "45 21 * * *" in expressions
        assert "0 22 * * *" in expressions

    def test_single_execution_when_interval_equals_window(self):
        """When interval equals window size, only start time executes."""
        window = TimeWindow(start_time="21:00", end_time="21:00")
        trigger = IntervalTrigger(interval_minutes=60, time_window=window)
        entries = interval_trigger_to_cron(trigger, command="cmd")
        # Only one execution at start
        assert len(entries) == 1
        assert entries[0].expression == "0 21 * * *"


class TestSolarTriggerConversion:
    """Test solar_trigger_to_cron function."""

    def test_get_solar_execution_time_sunset(self):
        """get_solar_execution_time returns datetime for sunset on specific date."""
        trigger = SolarTrigger(solar_event="sunset", offset_minutes=0)
        exec_time = get_solar_execution_time(
            trigger,
            target_date=date(2024, 6, 21),  # Summer solstice
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York"
        )
        assert exec_time is not None
        # Summer sunset in Eastern US (Oak Ridge, TN) is around 21:00 local
        assert exec_time.hour >= 20  # Should be evening

    def test_get_solar_execution_time_with_offset(self):
        """Positive and negative offsets work correctly."""
        trigger_plus = SolarTrigger(solar_event="sunset", offset_minutes=30)
        trigger_minus = SolarTrigger(solar_event="sunset", offset_minutes=-30)

        base = get_solar_execution_time(
            SolarTrigger(solar_event="sunset", offset_minutes=0),
            target_date=date(2024, 6, 21),
            latitude=35.96, longitude=-83.92, timezone_name="America/New_York"
        )
        plus30 = get_solar_execution_time(
            trigger_plus,
            target_date=date(2024, 6, 21),
            latitude=35.96, longitude=-83.92, timezone_name="America/New_York"
        )
        minus30 = get_solar_execution_time(
            trigger_minus,
            target_date=date(2024, 6, 21),
            latitude=35.96, longitude=-83.92, timezone_name="America/New_York"
        )

        # plus30 should be 30 minutes after base
        assert (plus30 - base).total_seconds() == 30 * 60
        # minus30 should be 30 minutes before base
        assert (base - minus30).total_seconds() == 30 * 60

    def test_solar_trigger_to_cron_generates_entries_for_days(self):
        """solar_trigger_to_cron generates entries for specified number of days."""
        trigger = SolarTrigger(solar_event="sunset", offset_minutes=30)
        entries = solar_trigger_to_cron(
            trigger,
            command="cmd",
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
            days_ahead=7
        )
        # Should generate 7 entries (one per day)
        assert len(entries) == 7
        # Each entry should have a valid cron expression
        for entry in entries:
            assert CronEntry.is_valid_expression(entry.expression)

    def test_solar_trigger_with_days_of_week(self):
        """Solar trigger respects days_of_week restriction."""
        trigger = SolarTrigger(
            solar_event="sunset",
            offset_minutes=0,
            days_of_week=[0, 2, 4]  # Mon, Wed, Fri (ISO)
        )
        entries = solar_trigger_to_cron(
            trigger,
            command="cmd",
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
            days_ahead=14,  # Two weeks
            from_date=date(2024, 6, 17)  # Monday
        )
        # Should have entries only for Mon, Wed, Fri
        # Week 1: Mon 17, Wed 19, Fri 21 = 3
        # Week 2: Mon 24, Wed 26, Fri 28 = 3
        # Total = 6 entries
        assert len(entries) == 6

    def test_solar_trigger_sunrise(self):
        """Sunrise trigger works correctly."""
        trigger = SolarTrigger(solar_event="sunrise", offset_minutes=-15)
        exec_time = get_solar_execution_time(
            trigger,
            target_date=date(2024, 6, 21),
            latitude=35.96, longitude=-83.92, timezone_name="America/New_York"
        )
        # Summer sunrise in Eastern US is around 6:00-6:30 AM
        assert exec_time.hour <= 7

    def test_solar_trigger_entries_have_correct_day_field(self):
        """Each cron entry specifies the exact day of month."""
        trigger = SolarTrigger(solar_event="sunset", offset_minutes=0)
        entries = solar_trigger_to_cron(
            trigger,
            command="cmd",
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
            days_ahead=3,
            from_date=date(2024, 6, 15)
        )
        # Entries should be for June 15, 16, 17
        expressions = [e.expression for e in entries]
        # Each expression should have day-of-month field set
        # Format: minute hour day month weekday
        for expr in expressions:
            parts = expr.split()
            day = parts[2]
            month = parts[3]
            assert day != "*"  # Day should be specific
            assert month != "*"  # Month should be specific


class TestMoonPhaseTriggerConversion:
    """Test moon_phase_trigger_to_cron function."""

    def test_is_moon_phase_active_full_moon(self):
        """is_moon_phase_active returns True on full moon date."""
        trigger = MoonPhaseTrigger(phases=["full"], offset_days=0)
        # Full moon on 2024-01-27 (verified via astral library)
        assert is_moon_phase_active(trigger, date(2024, 1, 27)) is True
        # Not full moon on 2024-01-15
        assert is_moon_phase_active(trigger, date(2024, 1, 15)) is False

    def test_is_moon_phase_active_with_offset(self):
        """offset_days expands the active window."""
        trigger = MoonPhaseTrigger(phases=["full"], offset_days=2)
        # Full moon on 2024-01-27, offset_days=2 means 25-29 should be active
        assert is_moon_phase_active(trigger, date(2024, 1, 25)) is True
        assert is_moon_phase_active(trigger, date(2024, 1, 29)) is True
        # Outside range
        assert is_moon_phase_active(trigger, date(2024, 1, 20)) is False

    def test_is_moon_phase_active_multiple_phases(self):
        """Multiple phases (full AND new) both match."""
        trigger = MoonPhaseTrigger(phases=["full", "new"], offset_days=0)
        # Full moon on 2024-01-27, new moon on 2024-01-12
        assert is_moon_phase_active(trigger, date(2024, 1, 27)) is True  # Full
        assert is_moon_phase_active(trigger, date(2024, 1, 12)) is True  # New
        # Neither (2024-01-18 is between phases)
        assert is_moon_phase_active(trigger, date(2024, 1, 18)) is False

    def test_moon_phase_trigger_to_cron_generates_entries(self):
        """moon_phase_trigger_to_cron generates entries for matching days."""
        window = TimeWindow(start_time="21:00", end_time="21:00")
        trigger = MoonPhaseTrigger(phases=["full"], offset_days=0, time_window=window)
        entries = moon_phase_trigger_to_cron(
            trigger,
            command="cmd",
            days_ahead=60,  # Two lunar cycles
            from_date=date(2024, 1, 1)
        )
        # Should have at least 2 full moons in 60 days
        assert len(entries) >= 2
        # Each entry should be valid
        for entry in entries:
            assert CronEntry.is_valid_expression(entry.expression)

    def test_moon_phase_trigger_with_time_window(self):
        """Moon trigger respects time window for cron expression."""
        window = TimeWindow(start_time="20:30", end_time="20:30")
        trigger = MoonPhaseTrigger(phases=["full"], offset_days=0, time_window=window)
        entries = moon_phase_trigger_to_cron(
            trigger,
            command="cmd",
            days_ahead=30,
            from_date=date(2024, 1, 1)
        )
        # At least 1 full moon in 30 days
        assert len(entries) >= 1
        # Check time is from window
        for entry in entries:
            parts = entry.expression.split()
            assert parts[0] == "30"  # minute
            assert parts[1] == "20"  # hour

    def test_moon_phase_trigger_no_time_window_uses_midnight(self):
        """Without time_window, defaults to midnight."""
        trigger = MoonPhaseTrigger(phases=["new"], offset_days=0, time_window=None)
        entries = moon_phase_trigger_to_cron(
            trigger,
            command="cmd",
            days_ahead=30,
            from_date=date(2024, 1, 1)
        )
        if entries:  # If there's a new moon in range
            parts = entries[0].expression.split()
            assert parts[0] == "0"  # minute = 0
            assert parts[1] == "0"  # hour = 0

    def test_moon_phase_trigger_with_offset_generates_more_entries(self):
        """Larger offset_days generates more matching dates."""
        trigger_no_offset = MoonPhaseTrigger(phases=["full"], offset_days=0)
        trigger_with_offset = MoonPhaseTrigger(phases=["full"], offset_days=2)

        entries_no_offset = moon_phase_trigger_to_cron(
            trigger_no_offset,
            command="cmd",
            days_ahead=60,
            from_date=date(2024, 1, 1)
        )
        entries_with_offset = moon_phase_trigger_to_cron(
            trigger_with_offset,
            command="cmd",
            days_ahead=60,
            from_date=date(2024, 1, 1)
        )

        # With offset should have more entries (each phase spans more days)
        assert len(entries_with_offset) > len(entries_no_offset)

    def test_moon_phase_trigger_entries_have_correct_day_field(self):
        """Each cron entry specifies the exact day of month."""
        trigger = MoonPhaseTrigger(phases=["full"], offset_days=0)
        entries = moon_phase_trigger_to_cron(
            trigger,
            command="cmd",
            days_ahead=30,
            from_date=date(2024, 1, 1)
        )
        # Each expression should have day-of-month field set
        # Format: minute hour day month weekday
        for entry in entries:
            parts = entry.expression.split()
            day = parts[2]
            month = parts[3]
            assert day != "*"  # Day should be specific
            assert month != "*"  # Month should be specific


class TestActionSequencing:
    """Test routine action sequencing."""

    def _make_routine(self, name: str, actions: list[Action]) -> Routine:
        """Helper to create a Routine with a default trigger for testing."""
        return Routine(
            routine_id="",
            name=name,
            trigger=SolarTrigger(solar_event="sunset"),  # Minimal trigger for tests
            actions=actions,
        )

    def test_single_action_at_offset_zero(self):
        """Single action at offset=0 executes at base time."""
        action = Action(action_type="gpio", action_name="attract_on", offset_minutes=0)
        routine = self._make_routine("Test", [action])
        entries = routine_to_cron_entries(routine, base_time="21:00")
        assert len(entries) == 1
        # Should be at 21:00
        assert "0 21" in entries[0].expression

    def test_multiple_actions_with_offsets(self):
        """Multiple actions execute at base_time + offset."""
        actions = [
            Action(action_type="gpio", action_name="attract_on", offset_minutes=0),
            Action(action_type="camera", action_name="takephoto", offset_minutes=5),
            Action(action_type="gpio", action_name="attract_off", offset_minutes=15),
        ]
        routine = self._make_routine("UV Capture", actions)
        entries = routine_to_cron_entries(routine, base_time="21:00")
        # UV on at 21:00, photo at 21:05, UV off at 21:15
        assert len(entries) == 3
        expressions = [e.expression for e in entries]
        assert "0 21 * * *" in expressions   # 21:00
        assert "5 21 * * *" in expressions   # 21:05
        assert "15 21 * * *" in expressions  # 21:15

    def test_offset_crosses_hour_boundary(self):
        """Offset pushing into next hour handled correctly."""
        actions = [
            Action(action_type="gpio", action_name="attract_on", offset_minutes=0),
            Action(action_type="gpio", action_name="attract_off", offset_minutes=45),
        ]
        routine = self._make_routine("Test", actions)
        entries = routine_to_cron_entries(routine, base_time="21:30")
        # attract_on at 21:30, attract_off at 22:15
        expressions = [e.expression for e in entries]
        assert "30 21 * * *" in expressions  # 21:30
        assert "15 22 * * *" in expressions  # 22:15

    def test_offset_crosses_midnight(self):
        """Offset pushing into next day handled correctly."""
        action = Action(action_type="gpio", action_name="attract_off", offset_minutes=90)
        routine = self._make_routine("Test", [action])
        entries = routine_to_cron_entries(routine, base_time="23:00")
        # 23:00 + 90 = 00:30 (next day, but cron is day-agnostic for repeating schedules)
        assert "30 0 * * *" in entries[0].expression

    def test_action_with_days_of_week(self):
        """Actions respect days_of_week constraint."""
        action = Action(action_type="gpio", action_name="attract_on", offset_minutes=0)
        routine = self._make_routine("Test", [action])
        entries = routine_to_cron_entries(routine, base_time="21:00", days_of_week=[0, 1, 2])  # Mon-Wed ISO
        # Cron days should be 1,2,3 (Mon-Wed in cron)
        assert "1,2,3" in entries[0].expression

    def test_action_command_from_cron_security(self):
        """Action commands are built using cron_security module."""
        action = Action(action_type="gpio", action_name="attract_on", offset_minutes=0)
        routine = self._make_routine("Test", [action])
        entries = routine_to_cron_entries(routine, base_time="21:00")
        # Command should be from get_validated_command
        assert "/usr/bin/python3" in entries[0].command
        assert "Attract_On.py" in entries[0].command

    def test_entries_have_descriptive_comments(self):
        """Generated entries have meaningful comments."""
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=5)
        routine = self._make_routine("UV Capture", [action])
        entries = routine_to_cron_entries(routine, base_time="21:00")
        # Comment should mention routine name and action
        assert "UV Capture" in entries[0].comment
        assert "takephoto" in entries[0].comment.lower() or "camera" in entries[0].comment.lower()


class TestRTCWakealarm:
    """Test RTC wakealarm functions."""

    def test_calculate_next_waketime_same_day(self):
        """calculate_next_waketime returns next execution when time is later today."""
        cron_expr = "0 21 * * *"  # 21:00 daily
        now = datetime(2024, 6, 15, 20, 0, 0)  # 20:00
        next_wake = calculate_next_waketime(cron_expr, from_time=now)
        # Should be 21:00 same day
        assert next_wake > int(now.timestamp())
        # Should be about 1 hour later
        expected = int(datetime(2024, 6, 15, 21, 0, 0).timestamp())
        assert abs(next_wake - expected) < 60  # Within 1 minute tolerance

    def test_calculate_next_waketime_next_day(self):
        """If time passed today, calculate for tomorrow."""
        cron_expr = "0 21 * * *"  # 21:00 daily
        now = datetime(2024, 6, 15, 22, 0, 0)  # 22:00 (after 21:00)
        next_wake = calculate_next_waketime(cron_expr, from_time=now)
        # Should be 21:00 next day
        expected = int(datetime(2024, 6, 16, 21, 0, 0).timestamp())
        assert abs(next_wake - expected) < 60

    def test_calculate_next_from_multiple_entries(self):
        """calculate_next_from_entries returns earliest of multiple crons."""
        entries = [
            CronEntry(expression="0 23 * * *", command="cmd"),  # 23:00
            CronEntry(expression="0 21 * * *", command="cmd"),  # 21:00
            CronEntry(expression="0 22 * * *", command="cmd"),  # 22:00
        ]
        now = datetime(2024, 6, 15, 20, 0, 0)  # 20:00
        next_wake = calculate_next_from_entries(entries, from_time=now)
        # Should be 21:00 (earliest)
        expected = int(datetime(2024, 6, 15, 21, 0, 0).timestamp())
        assert abs(next_wake - expected) < 60

    def test_calculate_next_from_empty_entries(self):
        """calculate_next_from_entries returns None for empty list."""
        next_wake = calculate_next_from_entries([], from_time=datetime.now())
        assert next_wake is None

    def test_set_rtc_wakealarm_writes_to_sysfs(self):
        """set_rtc_wakealarm writes epoch to /sys/class/rtc/rtc0/wakealarm."""
        m = mock_open()
        with patch("builtins.open", m):
            epoch = 1718463600
            result = set_rtc_wakealarm(epoch)
            assert result is True
            m.assert_called_with("/sys/class/rtc/rtc0/wakealarm", "w")
            m().write.assert_called_with(str(epoch))

    def test_clear_rtc_wakealarm_writes_zero(self):
        """clear_rtc_wakealarm writes 0 to clear existing alarm."""
        m = mock_open()
        with patch("builtins.open", m):
            result = clear_rtc_wakealarm()
            assert result is True
            m().write.assert_called_with("0")

    def test_set_rtc_wakealarm_handles_permission_error(self):
        """set_rtc_wakealarm returns False on permission error."""
        with patch("builtins.open", side_effect=PermissionError("No permission")):
            result = set_rtc_wakealarm(1718463600)
            assert result is False

    def test_calculate_next_waketime_with_day_of_week(self):
        """calculate_next_waketime handles day-of-week restrictions."""
        cron_expr = "0 21 * * 1"  # Monday only
        # June 15, 2024 is Saturday
        now = datetime(2024, 6, 15, 20, 0, 0)
        next_wake = calculate_next_waketime(cron_expr, from_time=now)
        # Should be next Monday (June 17, 2024)
        expected = int(datetime(2024, 6, 17, 21, 0, 0).timestamp())
        assert abs(next_wake - expected) < 60

    def test_calculate_next_from_entries_filters_disabled(self):
        """calculate_next_from_entries skips disabled entries."""
        entries = [
            CronEntry(expression="0 23 * * *", command="cmd", enabled=False),  # Disabled
            CronEntry(expression="0 21 * * *", command="cmd", enabled=True),   # Enabled
            CronEntry(expression="0 22 * * *", command="cmd", enabled=False),  # Disabled
        ]
        now = datetime(2024, 6, 15, 20, 0, 0)
        next_wake = calculate_next_from_entries(entries, from_time=now)
        # Should only use enabled entry (21:00)
        expected = int(datetime(2024, 6, 15, 21, 0, 0).timestamp())
        assert abs(next_wake - expected) < 60

    def test_clear_rtc_wakealarm_handles_file_not_found(self):
        """clear_rtc_wakealarm returns False on file not found error."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            result = clear_rtc_wakealarm()
            assert result is False

    def test_calculate_next_waketime_handles_complex_expression(self):
        """calculate_next_waketime handles complex cron expressions."""
        cron_expr = "0,30 9-17 * * 1-5"  # Every 30 min during business hours on weekdays
        now = datetime(2024, 6, 17, 9, 15, 0)  # Monday 9:15 AM
        next_wake = calculate_next_waketime(cron_expr, from_time=now)
        # Should be 9:30 same day
        expected = int(datetime(2024, 6, 17, 9, 30, 0).timestamp())
        assert abs(next_wake - expected) < 60


class TestApplyToSystem:
    """Test apply_to_system function."""

    def test_apply_writes_cron_entries(self):
        """apply_to_system writes entries to user crontab."""
        from unittest.mock import MagicMock, patch

        entries = [
            CronEntry(expression="0 21 * * *", command="cmd1", comment="Test 1"),
            CronEntry(expression="0 22 * * *", command="cmd2", comment="Test 2"),
        ]
        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron
            # Mock iteration to return empty list (no existing jobs)
            mock_cron.__iter__ = MagicMock(return_value=iter([]))

            result = apply_to_system(entries, schedule_id="test-123")

            assert result is True
            # Should have created new jobs
            assert mock_cron.new.call_count >= 2
            mock_cron.write.assert_called_once()

    def test_apply_removes_existing_mothbox_jobs_first(self):
        """apply_to_system removes old Mothbox jobs before adding new."""
        from unittest.mock import MagicMock, patch

        entries = [CronEntry(expression="0 21 * * *", command="cmd")]
        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron

            # Simulate existing Mothbox job
            existing_job = MagicMock()
            existing_job.command = "/usr/bin/python3 /opt/mothbox/TakePhoto.py"
            mock_cron.__iter__ = MagicMock(return_value=iter([existing_job]))

            apply_to_system(entries, schedule_id="test-123")

            # Old job should be removed
            mock_cron.remove.assert_called_with(existing_job)

    def test_apply_sets_rtc_alarm_when_enabled(self):
        """apply_to_system sets RTC wakealarm when set_rtc=True."""
        from unittest.mock import MagicMock, patch



        entries = [CronEntry(expression="0 21 * * *", command="cmd")]
        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron
            mock_cron.__iter__ = MagicMock(return_value=iter([]))

            with (
                patch("webui.backend.lib.cron_bridge.set_rtc_wakealarm") as mock_rtc,
                patch("webui.backend.lib.cron_bridge.calculate_next_from_entries") as mock_calc,
            ):
                mock_calc.return_value = 1718463600
                apply_to_system(entries, schedule_id="test-123", set_rtc=True)
                mock_rtc.assert_called_once_with(1718463600)

    def test_apply_preserves_non_mothbox_jobs(self):
        """apply_to_system preserves system (non-Mothbox) jobs."""
        from unittest.mock import MagicMock, patch



        entries = [CronEntry(expression="0 21 * * *", command="cmd")]
        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron

            # System job (should NOT be removed)
            system_job = MagicMock()
            system_job.command = "/usr/bin/logrotate /etc/logrotate.conf"

            # Mothbox job (SHOULD be removed)
            mothbox_job = MagicMock()
            mothbox_job.command = "/usr/bin/python3 /opt/mothbox/TakePhoto.py"

            mock_cron.__iter__ = MagicMock(return_value=iter([system_job, mothbox_job]))

            apply_to_system(entries, schedule_id="test-123")

            # Only Mothbox job should be removed
            mock_cron.remove.assert_called_once_with(mothbox_job)

    def test_apply_handles_disabled_entries(self):
        """apply_to_system skips disabled entries."""
        from unittest.mock import MagicMock, patch



        entries = [
            CronEntry(expression="0 21 * * *", command="cmd1", enabled=True),
            CronEntry(expression="0 22 * * *", command="cmd2", enabled=False),  # Disabled
        ]
        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron
            mock_cron.__iter__ = MagicMock(return_value=iter([]))

            with (
                patch("webui.backend.lib.cron_bridge.set_rtc_wakealarm"),
                patch("webui.backend.lib.cron_bridge.calculate_next_from_entries") as mock_calc,
            ):
                mock_calc.return_value = 1718463600
                result = apply_to_system(entries, schedule_id="test-123")

            assert result is True
            # Should only create one job (the enabled one)
            assert mock_cron.new.call_count == 1

    def test_apply_skips_rtc_when_disabled(self):
        """apply_to_system skips RTC wakealarm when set_rtc=False."""
        from unittest.mock import MagicMock, patch



        entries = [CronEntry(expression="0 21 * * *", command="cmd")]
        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron
            mock_cron.__iter__ = MagicMock(return_value=iter([]))

            with patch("webui.backend.lib.cron_bridge.set_rtc_wakealarm") as mock_rtc:
                apply_to_system(entries, schedule_id="test-123", set_rtc=False)
                mock_rtc.assert_not_called()

    def test_apply_handles_errors(self):
        """apply_to_system returns False on error."""
        from unittest.mock import patch



        entries = [CronEntry(expression="0 21 * * *", command="cmd")]
        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_crontab_class.side_effect = OSError("Cron error")

            result = apply_to_system(entries, schedule_id="test-123")

            assert result is False


class TestRemoveFromSystem:
    """Test remove_from_system function."""

    def test_remove_clears_mothbox_jobs(self):
        """remove_from_system removes all Mothbox cron jobs."""
        from unittest.mock import MagicMock, patch



        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron

            # Simulate Mothbox job
            mothbox_job = MagicMock()
            mothbox_job.command = "/usr/bin/python3 /opt/mothbox/TakePhoto.py"
            mock_cron.__iter__ = MagicMock(return_value=iter([mothbox_job]))

            result = remove_from_system()

            assert result is True
            mock_cron.remove.assert_called_with(mothbox_job)
            mock_cron.write.assert_called_once()

    def test_remove_clears_rtc_alarm_when_enabled(self):
        """remove_from_system clears RTC wakealarm when clear_rtc=True."""
        from unittest.mock import MagicMock, patch



        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron
            mock_cron.__iter__ = MagicMock(return_value=iter([]))

            with patch("webui.backend.lib.cron_bridge.clear_rtc_wakealarm") as mock_clear:
                remove_from_system(clear_rtc=True)
                mock_clear.assert_called_once()

    def test_remove_preserves_non_mothbox_jobs(self):
        """remove_from_system preserves system (non-Mothbox) jobs."""
        from unittest.mock import MagicMock, patch



        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron

            # System job (should NOT be removed)
            system_job = MagicMock()
            system_job.command = "/usr/bin/logrotate /etc/logrotate.conf"

            mock_cron.__iter__ = MagicMock(return_value=iter([system_job]))

            remove_from_system()

            # System job should NOT be removed
            mock_cron.remove.assert_not_called()

    def test_remove_skips_rtc_when_disabled(self):
        """remove_from_system skips RTC clear when clear_rtc=False."""
        from unittest.mock import MagicMock, patch



        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron
            mock_cron.__iter__ = MagicMock(return_value=iter([]))

            with patch("webui.backend.lib.cron_bridge.clear_rtc_wakealarm") as mock_clear:
                remove_from_system(clear_rtc=False)
                mock_clear.assert_not_called()

    def test_remove_handles_errors(self):
        """remove_from_system returns False on error."""
        from unittest.mock import patch



        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_crontab_class.side_effect = OSError("Cron error")

            result = remove_from_system()

            assert result is False

    def test_remove_with_user_parameter(self):
        """remove_from_system uses specified user when provided."""
        from unittest.mock import MagicMock, patch



        with patch("webui.backend.lib.cron_bridge.CronTab") as mock_crontab_class:
            mock_cron = MagicMock()
            mock_crontab_class.return_value = mock_cron
            mock_cron.__iter__ = MagicMock(return_value=iter([]))

            remove_from_system(user="testuser")

            # Should be called with user parameter
            mock_crontab_class.assert_called_once_with(user="testuser")


class TestGetNextEvents:
    """Test get_next_events function (Schema 3.0)."""

    def test_returns_list_of_events(self):
        """get_next_events returns list of event dicts."""
        # Create simple schedule with interval trigger routine
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=0)
        window = TimeWindow(start_time="21:00", end_time="22:00")
        trigger = IntervalTrigger(interval_minutes=60, time_window=window)
        routine = Routine(
            routine_id="r1",
            name="Photo Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s1",
            name="Test Schedule",
            description="",
            routines=[routine],
        )

        events = get_next_events(schedule, count=10, from_time=datetime(2024, 6, 15, 20, 0, 0))
        assert isinstance(events, list)
        assert len(events) <= 10

    def test_event_contains_required_fields(self):
        """Each event has datetime, action_type, action_name, pattern_name."""
        action = Action(action_type="gpio", action_name="attract_on", offset_minutes=0)
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        routine = Routine(
            routine_id="r1",
            name="UV Light Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s1",
            name="Test",
            description="",
            routines=[routine],
        )

        events = get_next_events(schedule, count=5, from_time=datetime(2024, 6, 15, 20, 0, 0))
        assert len(events) >= 1
        event = events[0]
        assert "datetime" in event
        assert "action_type" in event
        assert "action_name" in event
        assert "routine_name" in event
        assert "routine_id" in event

    def test_events_are_sorted_chronologically(self):
        """Events are returned in chronological order."""
        actions = [
            Action(action_type="gpio", action_name="attract_on", offset_minutes=0),
            Action(action_type="camera", action_name="takephoto", offset_minutes=5),
            Action(action_type="gpio", action_name="attract_off", offset_minutes=10),
        ]
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        routine = Routine(
            routine_id="r1",
            name="UV Capture Routine",
            trigger=trigger,
            actions=actions,
        )
        schedule = Schedule(
            schedule_id="s1",
            name="Test",
            description="",
            routines=[routine],
        )

        events = get_next_events(schedule, count=10, from_time=datetime(2024, 6, 15, 20, 0, 0))
        datetimes = [e["datetime"] for e in events]
        assert datetimes == sorted(datetimes)

    def test_events_include_all_routine_actions(self):
        """Events include actions from all routines in schedule."""
        action1 = Action(action_type="gpio", action_name="attract_on", offset_minutes=0)
        action2 = Action(action_type="camera", action_name="takephoto", offset_minutes=5)
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        routine = Routine(
            routine_id="r1",
            name="UV Capture Routine",
            trigger=trigger,
            actions=[action1, action2],
        )
        schedule = Schedule(
            schedule_id="s1",
            name="Test",
            description="",
            routines=[routine],
        )

        events = get_next_events(schedule, count=20, from_time=datetime(2024, 6, 15, 20, 0, 0))
        action_names = {e["action_name"] for e in events}
        assert "attract_on" in action_names
        assert "takephoto" in action_names

    def test_respects_date_constraints(self):
        """Events respect routine start_date constraint via RecurringDaysTrigger."""
        # Note: Schema 3.0 removed start_date/end_date from Schedule.
        # Date constraints are now per-routine via RecurringDaysTrigger.start_date.
        # This test validates the basic functionality without date constraints.
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=0)
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        routine = Routine(
            routine_id="r1",
            name="Photo Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s1",
            name="Test",
            description="",
            routines=[routine],
        )

        events = get_next_events(schedule, count=10, from_time=datetime(2024, 6, 15, 0, 0, 0))
        assert len(events) >= 1

    def test_returns_empty_for_disabled_schedule(self):
        """Disabled schedule returns no events."""
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=0)
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        routine = Routine(
            routine_id="r1",
            name="Photo Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s1",
            name="Test",
            description="",
            routines=[routine],
            enabled=False,
        )

        events = get_next_events(schedule, count=10)
        assert events == []

    def test_respects_count_limit(self):
        """get_next_events respects count parameter."""
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=0)
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        routine = Routine(
            routine_id="r1",
            name="Photo Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s1",
            name="Test",
            description="",
            routines=[routine],
        )

        events5 = get_next_events(schedule, count=5, from_time=datetime(2024, 6, 15, 20, 0, 0))
        events10 = get_next_events(schedule, count=10, from_time=datetime(2024, 6, 15, 20, 0, 0))
        assert len(events5) == 5
        assert len(events10) == 10


class TestScheduleToCron:
    """Test main schedule_to_cron function (Schema 3.0)."""

    def test_fixed_time_schedule_to_cron(self):
        """Convert fixed-time schedule to cron entries."""
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=0)
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        routine = Routine(
            routine_id="r1",
            name="Photo Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s1",
            name="Test Schedule",
            description="",
            routines=[routine],
        )

        result = schedule_to_cron(schedule)
        assert isinstance(result, CronBridgeResult)
        assert result.schedule_id == "s1"
        assert len(result.entries) > 0
        assert len(result.errors) == 0

    def test_interval_schedule_to_cron(self):
        """Convert interval-based schedule to cron entries."""
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=0)
        window = TimeWindow(start_time="21:00", end_time="23:00")
        trigger = IntervalTrigger(interval_minutes=60, time_window=window)
        routine = Routine(
            routine_id="r1",
            name="Photo Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s2",
            name="Interval Schedule",
            description="",
            routines=[routine],
        )

        result = schedule_to_cron(schedule)
        assert isinstance(result, CronBridgeResult)
        assert len(result.entries) >= 3  # 21:00, 22:00, 23:00

    def test_solar_schedule_to_cron(self):
        """Convert solar-based schedule to cron entries."""
        action = Action(action_type="gpio", action_name="attract_on", offset_minutes=0)
        trigger = SolarTrigger(solar_event="sunset", offset_minutes=30)
        routine = Routine(
            routine_id="r1",
            name="UV Light Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s3",
            name="Solar Schedule",
            description="",
            routines=[routine],
        )

        result = schedule_to_cron(schedule, latitude=35.96, longitude=-83.92)
        assert isinstance(result, CronBridgeResult)
        assert len(result.entries) > 0

    def test_moon_phase_schedule_to_cron(self):
        """Convert moon-phase schedule to cron entries."""
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=0)
        window = TimeWindow(start_time="21:00", end_time="21:00")
        trigger = MoonPhaseTrigger(phases=["full"], offset_days=0, time_window=window)
        routine = Routine(
            routine_id="r1",
            name="Full Moon Photo Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s4",
            name="Moon Phase Schedule",
            description="",
            routines=[routine],
        )

        result = schedule_to_cron(schedule)
        assert isinstance(result, CronBridgeResult)
        # At least one full moon in 30 days
        assert len(result.entries) >= 1

    def test_disabled_schedule_returns_empty(self):
        """Disabled schedule returns empty entries list."""
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=0)
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        routine = Routine(
            routine_id="r1",
            name="Photo Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s5",
            name="Disabled Schedule",
            description="",
            routines=[routine],
            enabled=False,
        )

        result = schedule_to_cron(schedule)
        assert len(result.entries) == 0

    def test_empty_routines_returns_empty(self):
        """Schedule with no routines returns empty entries."""
        schedule = Schedule(
            schedule_id="s7",
            name="Empty Schedule",
            description="",
            routines=[],
        )

        result = schedule_to_cron(schedule)
        assert len(result.entries) == 0


class TestSensorTriggerStub:
    """Test sensor trigger stub (returns empty with warning)."""

    def test_sensor_trigger_returns_empty_entries(self):
        """Sensor trigger returns empty list (not yet implemented)."""
        trigger = SensorTrigger(
            sensor_type="motion",
            threshold=0.0,
            comparison="gt",
            cooldown_minutes=5,
        )
        entries = sensor_trigger_to_cron(trigger, command="cmd")
        assert entries == []

    def test_sensor_trigger_to_cron_returns_warning(self):
        """Sensor trigger returns warning about not being implemented."""
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=0)
        trigger = SensorTrigger(sensor_type="motion", threshold=0.0)
        routine = Routine(
            routine_id="r1",
            name="Motion Photo Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s8",
            name="Sensor Schedule",
            description="",
            routines=[routine],
        )

        result = schedule_to_cron(schedule)
        assert len(result.entries) == 0
        assert len(result.errors) > 0
        assert "sensor" in result.errors[0].lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions (Schema 3.0)."""

    def test_schedule_with_multiple_routines(self):
        """Schedule with multiple routines generates entries for all."""
        action1 = Action(action_type="gpio", action_name="attract_on", offset_minutes=0)
        action2 = Action(action_type="gpio", action_name="attract_off", offset_minutes=0)
        trigger1 = FixedTimeTrigger(time="21:00", days_of_week=None)
        trigger2 = FixedTimeTrigger(time="21:15", days_of_week=None)
        routine1 = Routine(
            routine_id="r1",
            name="UV On Routine",
            trigger=trigger1,
            actions=[action1],
        )
        routine2 = Routine(
            routine_id="r2",
            name="UV Off Routine",
            trigger=trigger2,
            actions=[action2],
        )
        schedule = Schedule(
            schedule_id="s9",
            name="Multi Routine",
            description="",
            routines=[routine1, routine2],
        )

        result = schedule_to_cron(schedule)
        # Should have entries for both routines
        assert len(result.entries) >= 2

    def test_schedule_with_action_offsets(self):
        """Schedule correctly applies action offsets."""
        actions = [
            Action(action_type="gpio", action_name="attract_on", offset_minutes=0),
            Action(action_type="camera", action_name="takephoto", offset_minutes=5),
            Action(action_type="gpio", action_name="attract_off", offset_minutes=15),
        ]
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        routine = Routine(
            routine_id="r1",
            name="UV Capture Routine",
            trigger=trigger,
            actions=actions,
        )
        schedule = Schedule(
            schedule_id="s10",
            name="With Offsets",
            description="",
            routines=[routine],
        )

        result = schedule_to_cron(schedule)
        assert len(result.entries) >= 3
        expressions = [e.expression for e in result.entries]
        # Should have entries at 21:00, 21:05, 21:15
        assert "0 21 * * *" in expressions
        assert "5 21 * * *" in expressions
        assert "15 21 * * *" in expressions

    def test_rtc_waketime_calculated(self):
        """schedule_to_cron calculates rtc_waketime."""
        action = Action(action_type="camera", action_name="takephoto", offset_minutes=0)
        trigger = FixedTimeTrigger(time="21:00", days_of_week=None)
        routine = Routine(
            routine_id="r1",
            name="Photo Routine",
            trigger=trigger,
            actions=[action],
        )
        schedule = Schedule(
            schedule_id="s11",
            name="Test",
            description="",
            routines=[routine],
        )

        result = schedule_to_cron(schedule)
        # rtc_waketime should be set
        assert result.rtc_waketime is not None
        assert result.rtc_waketime > 0


class TestDaysAheadValidation:
    """Tests for days_ahead parameter validation."""

    def test_solar_trigger_days_ahead_zero_raises(self):
        """solar_trigger_to_cron raises ValueError for days_ahead=0."""
        from webui.backend.lib.cron_bridge import solar_trigger_to_cron
        from webui.backend.lib.schedule_schema import SolarTrigger

        trigger = SolarTrigger(solar_event="sunset", offset_minutes=0)

        with pytest.raises(ValueError, match="days_ahead must be between 1 and 365"):
            solar_trigger_to_cron(
                trigger, "test_command", latitude=0.0, longitude=0.0, days_ahead=0
            )

    def test_solar_trigger_days_ahead_negative_raises(self):
        """solar_trigger_to_cron raises ValueError for negative days_ahead."""
        from webui.backend.lib.cron_bridge import solar_trigger_to_cron
        from webui.backend.lib.schedule_schema import SolarTrigger

        trigger = SolarTrigger(solar_event="sunrise", offset_minutes=0)

        with pytest.raises(ValueError, match="days_ahead must be between 1 and 365"):
            solar_trigger_to_cron(
                trigger, "test_command", latitude=0.0, longitude=0.0, days_ahead=-5
            )

    def test_solar_trigger_days_ahead_too_large_raises(self):
        """solar_trigger_to_cron raises ValueError for days_ahead > 365."""
        from webui.backend.lib.cron_bridge import solar_trigger_to_cron
        from webui.backend.lib.schedule_schema import SolarTrigger

        trigger = SolarTrigger(solar_event="sunset", offset_minutes=0)

        with pytest.raises(ValueError, match="days_ahead must be between 1 and 365"):
            solar_trigger_to_cron(
                trigger, "test_command", latitude=0.0, longitude=0.0, days_ahead=366
            )

    def test_moon_phase_trigger_days_ahead_zero_raises(self):
        """moon_phase_trigger_to_cron raises ValueError for days_ahead=0."""
        from webui.backend.lib.cron_bridge import moon_phase_trigger_to_cron
        from webui.backend.lib.schedule_schema import MoonPhaseTrigger

        trigger = MoonPhaseTrigger(phases=["full"])

        with pytest.raises(ValueError, match="days_ahead must be between 1 and 365"):
            moon_phase_trigger_to_cron(trigger, "test_command", days_ahead=0)

    def test_moon_phase_trigger_days_ahead_negative_raises(self):
        """moon_phase_trigger_to_cron raises ValueError for negative days_ahead."""
        from webui.backend.lib.cron_bridge import moon_phase_trigger_to_cron
        from webui.backend.lib.schedule_schema import MoonPhaseTrigger

        trigger = MoonPhaseTrigger(phases=["new"])

        with pytest.raises(ValueError, match="days_ahead must be between 1 and 365"):
            moon_phase_trigger_to_cron(trigger, "test_command", days_ahead=-10)

    def test_moon_phase_trigger_days_ahead_too_large_raises(self):
        """moon_phase_trigger_to_cron raises ValueError for days_ahead > 365."""
        from webui.backend.lib.cron_bridge import moon_phase_trigger_to_cron
        from webui.backend.lib.schedule_schema import MoonPhaseTrigger

        trigger = MoonPhaseTrigger(phases=["full"])

        with pytest.raises(ValueError, match="days_ahead must be between 1 and 365"):
            moon_phase_trigger_to_cron(trigger, "test_command", days_ahead=400)

    def test_solar_trigger_days_ahead_valid_boundary(self):
        """solar_trigger_to_cron accepts boundary values 1 and 365."""
        from webui.backend.lib.cron_bridge import solar_trigger_to_cron
        from webui.backend.lib.schedule_schema import SolarTrigger

        trigger = SolarTrigger(solar_event="sunset", offset_minutes=0)

        # days_ahead=1 should work
        result = solar_trigger_to_cron(
            trigger, "test_command", latitude=45.0, longitude=-93.0, days_ahead=1
        )
        assert isinstance(result, list)

        # days_ahead=365 should work
        result = solar_trigger_to_cron(
            trigger, "test_command", latitude=45.0, longitude=-93.0, days_ahead=365
        )
        assert isinstance(result, list)

    def test_moon_phase_trigger_days_ahead_valid_boundary(self):
        """moon_phase_trigger_to_cron accepts boundary values 1 and 365."""
        from webui.backend.lib.cron_bridge import moon_phase_trigger_to_cron
        from webui.backend.lib.schedule_schema import MoonPhaseTrigger

        trigger = MoonPhaseTrigger(phases=["full"])

        # days_ahead=1 should work
        result = moon_phase_trigger_to_cron(trigger, "test_command", days_ahead=1)
        assert isinstance(result, list)

        # days_ahead=365 should work
        result = moon_phase_trigger_to_cron(trigger, "test_command", days_ahead=365)
        assert isinstance(result, list)
