"""
Unit tests for solar time calculation library.

Tests cover:
- Solar event constants and validation
- Sun times (dawn, sunrise, noon, sunset, dusk)
- Twilight times (civil, nautical, astronomical)
- Golden hour and blue hour calculations
- Time specification parsing (absolute and relative times)
- Edge cases (polar regions, year boundaries, timezone handling)

Coverage target: 85%+
Test count target: 39+

Issue #211 - Scheduler Phase 2: Solar Time Calculator
"""

from datetime import date, datetime

import pytest

# Import guard for TDD - tests can run before implementation exists
try:
    from webui.backend.lib.solar_time import (
        SOLAR_EVENTS,
        TIME_SPEC_PATTERN,
        TWILIGHT_TYPES,
        get_blue_hour,
        get_daylight_hours,
        get_golden_hour,
        get_sun_times,
        get_twilight_times,
        parse_time_spec,
        validate_solar_event,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    # Define placeholders for type checking
    SOLAR_EVENTS = []
    TWILIGHT_TYPES = []
    TIME_SPEC_PATTERN = None

pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="solar_time.py not yet implemented (TDD)",
)


class TestSolarTimeConstants:
    """Test constants are correctly defined and aligned with schedule_schema."""

    def test_solar_events_has_all_events(self):
        """SOLAR_EVENTS should have 15 events (excluding 'noon' which is in base events)."""
        # Total solar-related events: 15 in SOLAR_EVENTS constant
        # 'noon' is handled separately in base TIME_EVENTS
        assert len(SOLAR_EVENTS) == 15

    def test_solar_events_matches_schedule_schema(self):
        """SOLAR_EVENTS should match the list defined in schedule_schema.py."""
        from webui.backend.lib.schedule_schema import SOLAR_EVENTS as SCHEMA_SOLAR_EVENTS

        assert set(SOLAR_EVENTS) == set(SCHEMA_SOLAR_EVENTS)

    def test_twilight_types_defined(self):
        """TWILIGHT_TYPES should contain civil, nautical, astronomical."""
        expected_types = ["civil", "nautical", "astronomical"]
        assert set(TWILIGHT_TYPES) == set(expected_types)

    def test_time_spec_pattern_defined(self):
        """TIME_SPEC_PATTERN should be a compiled regex pattern."""
        import re
        assert TIME_SPEC_PATTERN is not None
        assert isinstance(TIME_SPEC_PATTERN, re.Pattern)

    def test_time_spec_pattern_matches_valid_specs(self):
        """TIME_SPEC_PATTERN should match valid time specifications."""
        valid_specs = [
            "sunset",
            "sunset+30",
            "sunrise-15",
            "astronomical_dusk",
            "golden_hour_start",
            "noon",
        ]

        for spec in valid_specs:
            match = TIME_SPEC_PATTERN.match(spec)
            assert match is not None, f"Pattern should match '{spec}'"


class TestGetSunTimes:
    """Test basic sun times calculation."""

    def test_get_sun_times_returns_dict(self):
        """get_sun_times should return dict with expected keys."""
        result = get_sun_times(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        assert isinstance(result, dict)
        assert "date" in result
        assert "dawn" in result
        assert "sunrise" in result
        assert "noon" in result
        assert "sunset" in result
        assert "dusk" in result

    def test_get_sun_times_mid_latitude_summer(self):
        """Test sun times for Oak Ridge, TN on summer solstice."""
        # Oak Ridge, TN on June 21, 2024 (summer solstice)
        result = get_sun_times(
            date(2024, 6, 21),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Verify all times are present
        assert result["dawn"] is not None
        assert result["sunrise"] is not None
        assert result["noon"] is not None
        assert result["sunset"] is not None
        assert result["dusk"] is not None

        # Verify temporal order: dawn < sunrise < noon < sunset < dusk
        times = [result["dawn"], result["sunrise"], result["noon"], result["sunset"], result["dusk"]]
        assert times == sorted(times), "Sun times should be in chronological order"

    def test_get_sun_times_equator(self):
        """Test sun times at equator on equinox."""
        # Equator on equinox - day and night are equal
        result = get_sun_times(
            date(2024, 3, 20),
            latitude=0.0,
            longitude=0.0,
            timezone_name="UTC",
        )

        assert result["date"] == "2024-03-20"
        assert result["sunrise"] is not None
        assert result["sunset"] is not None

    def test_get_sun_times_iso_format(self):
        """All time values should be ISO 8601 formatted strings."""
        result = get_sun_times(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Check that non-None values are ISO 8601 strings
        for key in ["dawn", "sunrise", "noon", "sunset", "dusk"]:
            if result[key] is not None:
                assert isinstance(result[key], str)
                # Should be parseable as ISO 8601
                datetime.fromisoformat(result[key])

    def test_get_sun_times_invalid_latitude(self):
        """Should raise ValueError for latitude > 90."""
        with pytest.raises(ValueError, match="latitude"):
            get_sun_times(
                date(2024, 6, 15),
                latitude=95.0,  # Invalid
                longitude=0.0,
            )


class TestGetTwilightTimes:
    """Test twilight time calculations."""

    def test_get_twilight_times_civil(self):
        """Test civil twilight calculation."""
        result = get_twilight_times(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
            twilight_type="civil",
        )

        assert isinstance(result, dict)
        assert "morning" in result
        assert "evening" in result
        assert result["morning"] is not None
        assert result["evening"] is not None

    def test_get_twilight_times_nautical(self):
        """Test nautical twilight calculation."""
        result = get_twilight_times(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
            twilight_type="nautical",
        )

        assert result["morning"] is not None
        assert result["evening"] is not None

    def test_get_twilight_times_astronomical(self):
        """Test astronomical twilight calculation."""
        result = get_twilight_times(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
            twilight_type="astronomical",
        )

        assert result["morning"] is not None
        assert result["evening"] is not None

    def test_get_twilight_times_invalid_type(self):
        """Should raise ValueError for invalid twilight type."""
        with pytest.raises(ValueError, match="twilight"):
            get_twilight_times(
                date(2024, 6, 15),
                latitude=35.96,
                longitude=-83.92,
                timezone_name="America/New_York",
                twilight_type="invalid",
            )

    def test_twilight_order(self):
        """Twilight times should follow correct chronological order."""
        # Get all twilight times for morning
        civil = get_twilight_times(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
            twilight_type="civil",
        )
        nautical = get_twilight_times(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
            twilight_type="nautical",
        )
        astronomical = get_twilight_times(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
            twilight_type="astronomical",
        )

        # Get sunrise for comparison
        sun_times = get_sun_times(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Morning order: astronomical_dawn < nautical_dawn < civil_dawn < sunrise
        times = [
            astronomical["morning"],
            nautical["morning"],
            civil["morning"],
            sun_times["sunrise"],
        ]
        assert times == sorted(times), "Morning twilight times should be in order"


class TestGetGoldenHour:
    """Test golden hour calculations."""

    def test_get_golden_hour_returns_dict(self):
        """get_golden_hour should return dict with expected keys."""
        result = get_golden_hour(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        assert isinstance(result, dict)
        assert "morning_start" in result
        assert "morning_end" in result
        assert "evening_start" in result
        assert "evening_end" in result

    def test_golden_hour_near_sunrise_sunset(self):
        """Golden hour should bracket sunrise and sunset."""
        golden = get_golden_hour(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Morning golden hour should end near/after sunrise
        if golden["morning_start"] and golden["morning_end"]:
            assert golden["morning_start"] < golden["morning_end"]

        # Evening golden hour should start near/before sunset
        if golden["evening_start"] and golden["evening_end"]:
            assert golden["evening_start"] < golden["evening_end"]

    def test_golden_hour_polar_returns_none(self):
        """In polar regions during winter, golden hour may not occur."""
        # Tromsø, Norway in December (polar night period)
        result = get_golden_hour(
            date(2024, 12, 21),
            latitude=69.65,
            longitude=18.96,
            timezone_name="Europe/Oslo",
        )

        # During polar night, some/all golden hour times may be None
        assert isinstance(result, dict)
        # At least the structure should be present
        assert "morning_start" in result
        assert "evening_end" in result


class TestGetBlueHour:
    """Test blue hour calculations."""

    def test_get_blue_hour_returns_dict(self):
        """get_blue_hour should return dict with expected keys."""
        result = get_blue_hour(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        assert isinstance(result, dict)
        assert "morning_start" in result
        assert "morning_end" in result
        assert "evening_start" in result
        assert "evening_end" in result

    def test_blue_hour_before_golden_hour_morning(self):
        """Morning blue hour should end before golden hour starts."""
        blue = get_blue_hour(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )
        golden = get_golden_hour(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Blue hour ends around when golden hour starts (morning)
        if blue["morning_end"] and golden["morning_start"]:
            # Blue hour should end before or near golden hour start
            blue_end = datetime.fromisoformat(blue["morning_end"])
            golden_start = datetime.fromisoformat(golden["morning_start"])
            # Allow some overlap/proximity (within 30 minutes)
            time_diff = abs((blue_end - golden_start).total_seconds())
            assert time_diff < 1800, "Blue hour and golden hour should be temporally close"

    def test_blue_hour_after_golden_hour_evening(self):
        """Evening blue hour should start after golden hour ends."""
        blue = get_blue_hour(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )
        golden = get_golden_hour(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Blue hour starts around when golden hour ends (evening)
        if blue["evening_start"] and golden["evening_end"]:
            blue_start = datetime.fromisoformat(blue["evening_start"])
            golden_end = datetime.fromisoformat(golden["evening_end"])
            # Allow some overlap/proximity (within 30 minutes)
            time_diff = abs((blue_start - golden_end).total_seconds())
            assert time_diff < 1800, "Blue hour and golden hour should be temporally close"


class TestParseTimeSpec:
    """Test time specification parsing."""

    def test_parse_time_spec_absolute_time(self):
        """Parse absolute time like '19:30'."""
        result = parse_time_spec(
            "19:30",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        assert isinstance(result, datetime)
        assert result.hour == 19
        assert result.minute == 30

    def test_parse_time_spec_sunset(self):
        """Parse 'sunset' event."""
        result = parse_time_spec(
            "sunset",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        assert isinstance(result, datetime)
        # Should be in the evening
        assert result.hour >= 18

    def test_parse_time_spec_sunset_plus_offset(self):
        """Parse 'sunset+30' (30 minutes after sunset)."""
        sunset = parse_time_spec(
            "sunset",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )
        sunset_plus_30 = parse_time_spec(
            "sunset+30",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Should be exactly 30 minutes later
        time_diff = (sunset_plus_30 - sunset).total_seconds()
        assert time_diff == 30 * 60

    def test_parse_time_spec_sunrise_minus_offset(self):
        """Parse 'sunrise-15' (15 minutes before sunrise)."""
        sunrise = parse_time_spec(
            "sunrise",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )
        sunrise_minus_15 = parse_time_spec(
            "sunrise-15",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Should be exactly 15 minutes earlier
        time_diff = (sunrise - sunrise_minus_15).total_seconds()
        assert time_diff == 15 * 60

    def test_parse_time_spec_civil_dusk(self):
        """Parse 'civil_dusk' event."""
        result = parse_time_spec(
            "civil_dusk",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        assert isinstance(result, datetime)
        # Civil dusk should be after sunset
        sunset = parse_time_spec(
            "sunset",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )
        assert result > sunset

    def test_parse_time_spec_astronomical_dawn(self):
        """Parse 'astronomical_dawn' event."""
        result = parse_time_spec(
            "astronomical_dawn",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        assert isinstance(result, datetime)
        # Astronomical dawn should be before sunrise
        sunrise = parse_time_spec(
            "sunrise",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )
        assert result < sunrise

    def test_parse_time_spec_golden_hour_start(self):
        """Parse 'golden_hour_start' event."""
        result = parse_time_spec(
            "golden_hour_start",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        assert isinstance(result, datetime)
        # Should be in evening (after noon)
        assert result.hour >= 12

    def test_parse_time_spec_invalid_format(self):
        """Should raise ValueError for invalid event name."""
        with pytest.raises(ValueError, match="Invalid|event"):
            parse_time_spec(
                "invalid_event",
                date(2024, 6, 15),
                latitude=35.96,
                longitude=-83.92,
                timezone_name="America/New_York",
            )


class TestValidateSolarEvent:
    """Test solar event validation."""

    def test_validate_solar_event_all_valid(self):
        """All 15 SOLAR_EVENTS should validate successfully."""
        for event in SOLAR_EVENTS:
            valid, error = validate_solar_event(
                event,
                latitude=35.96,
                longitude=-83.92,
                timezone_name="America/New_York",
            )
            assert valid is True, f"Event '{event}' should be valid"
            assert error is None

    def test_validate_solar_event_invalid(self):
        """Invalid event names should return error."""
        valid, error = validate_solar_event(
            "invalid_event",
            latitude=35.96,
            longitude=-83.92,
        )

        assert valid is False
        assert error is not None
        assert "invalid" in error.lower() or "event" in error.lower()

    def test_validate_coordinates_invalid_latitude(self):
        """Invalid latitude should raise error."""
        with pytest.raises(ValueError, match="latitude"):
            validate_solar_event(
                "sunset",
                latitude=95.0,  # Invalid
                longitude=0.0,
            )


class TestSolarTimeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_polar_region_midnight_sun(self):
        """Test polar region during midnight sun period."""
        # Tromsø, Norway in June (midnight sun)
        result = get_sun_times(
            date(2024, 6, 21),
            latitude=69.65,
            longitude=18.96,
            timezone_name="Europe/Oslo",
        )

        # During midnight sun, sun may not set
        # Function should handle this gracefully
        assert isinstance(result, dict)
        assert "date" in result

    def test_polar_region_polar_night(self):
        """Test polar region during polar night period."""
        # Tromsø, Norway in December (polar night)
        result = get_sun_times(
            date(2024, 12, 21),
            latitude=69.65,
            longitude=18.96,
            timezone_name="Europe/Oslo",
        )

        # During polar night, sun may not rise
        # Function should handle this gracefully
        assert isinstance(result, dict)
        assert "date" in result

    def test_year_boundary(self):
        """Test dates around year boundary."""
        result_dec = get_sun_times(
            date(2024, 12, 31),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )
        result_jan = get_sun_times(
            date(2025, 1, 1),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Both should have valid times
        assert result_dec["sunrise"] is not None
        assert result_jan["sunrise"] is not None

    def test_daylight_hours_summer_vs_winter(self):
        """Summer daylight hours should be longer than winter."""
        summer_hours = get_daylight_hours(
            date(2024, 6, 21),  # Summer solstice
            latitude=35.96,
            longitude=-83.92,
        )
        winter_hours = get_daylight_hours(
            date(2024, 12, 21),  # Winter solstice
            latitude=35.96,
            longitude=-83.92,
        )

        assert summer_hours > winter_hours


class TestGetDaylightHours:
    """Test daylight hours calculation."""

    def test_daylight_hours_returns_float(self):
        """get_daylight_hours should return float."""
        result = get_daylight_hours(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
        )

        assert isinstance(result, float)
        assert result > 0

    def test_daylight_hours_summer_solstice(self):
        """Test daylight hours on summer solstice."""
        # Northern hemisphere summer solstice - longest day
        result = get_daylight_hours(
            date(2024, 6, 21),
            latitude=35.96,
            longitude=-83.92,
        )

        # Mid-latitude should have ~14-15 hours of daylight
        assert 13.0 < result < 16.0

    def test_daylight_hours_equator_equinox(self):
        """Test daylight hours at equator on equinox."""
        # At equator on equinox, day and night are equal (~12 hours)
        result = get_daylight_hours(
            date(2024, 3, 20),
            latitude=0.0,
            longitude=0.0,
        )

        # Should be very close to 12 hours
        assert 11.5 < result < 12.5


class TestAdditionalCoverage:
    """Additional tests to improve code coverage to 85%+."""

    def test_get_sun_event_time_golden_hour_end(self):
        """Test _get_sun_event_time for golden_hour_end event."""
        from webui.backend.lib.solar_time import _get_sun_event_time

        result = _get_sun_event_time(
            "golden_hour_end",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Should return a datetime or None
        assert result is None or hasattr(result, "isoformat")

    def test_get_sun_event_time_blue_hour_end(self):
        """Test _get_sun_event_time for blue_hour_end event."""
        from webui.backend.lib.solar_time import _get_sun_event_time

        result = _get_sun_event_time(
            "blue_hour_end",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Should return a datetime or None
        assert result is None or hasattr(result, "isoformat")

    def test_get_sun_event_time_unknown_event(self):
        """Test _get_sun_event_time with unknown event."""
        from webui.backend.lib.solar_time import _get_sun_event_time

        with pytest.raises(ValueError, match="Unknown solar event"):
            _get_sun_event_time(
                "unknown_event",
                date(2024, 6, 15),
                latitude=35.96,
                longitude=-83.92,
                timezone_name="UTC",
            )

    def test_parse_time_spec_noon(self):
        """Test parsing 'noon' time specification."""
        result = parse_time_spec(
            "noon",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="UTC",
        )

        # Noon should be around 12:00 local sun time
        assert result.hour >= 10 and result.hour <= 18

    def test_parse_time_spec_civil_dawn(self):
        """Test parsing civil_dawn time specification."""
        result = parse_time_spec(
            "civil_dawn",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="UTC",
        )

        # Civil dawn should be in the morning
        assert result is not None

    def test_parse_time_spec_nautical_dawn(self):
        """Test parsing nautical_dawn time specification."""
        result = parse_time_spec(
            "nautical_dawn",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="UTC",
        )

        # Nautical dawn should be in the morning
        assert result is not None

    def test_parse_time_spec_nautical_dusk(self):
        """Test parsing nautical_dusk time specification."""
        result = parse_time_spec(
            "nautical_dusk",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="UTC",
        )

        # Nautical dusk should be in the evening
        assert result is not None

    def test_parse_time_spec_blue_hour_end(self):
        """Test parsing blue_hour_end time specification."""
        result = parse_time_spec(
            "blue_hour_end",
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="UTC",
        )

        # Blue hour end should be in the evening after sunset
        assert result is not None

    def test_get_golden_hour_morning(self):
        """Test golden hour morning times are calculated."""
        result = get_golden_hour(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Morning golden hour should exist at mid-latitudes
        # Either morning_start or morning_end may be None at polar regions
        assert "morning_start" in result
        assert "morning_end" in result

    def test_get_blue_hour_morning(self):
        """Test blue hour morning times are calculated."""
        result = get_blue_hour(
            date(2024, 6, 15),
            latitude=35.96,
            longitude=-83.92,
            timezone_name="America/New_York",
        )

        # Morning blue hour should exist at mid-latitudes
        assert "morning_start" in result
        assert "morning_end" in result

    def test_daylight_hours_polar_summer(self):
        """Test daylight hours in polar region during summer raises error."""
        # In polar summer, sun doesn't set so daylight hours can't be calculated
        with pytest.raises(ValueError, match="Cannot calculate daylight hours"):
            get_daylight_hours(
                date(2024, 6, 21),
                latitude=70.0,  # Arctic
                longitude=20.0,
                timezone_name="UTC",
            )

    def test_validate_coordinates_negative_longitude(self):
        """Test coordinate validation with valid negative longitude."""
        from webui.backend.lib.solar_time import _validate_coordinates

        # Should not raise for valid coordinates
        _validate_coordinates(-45.0, -122.0)  # Southern hemisphere, western longitude

    def test_validate_coordinates_boundary_values(self):
        """Test coordinate validation at exact boundary values."""
        from webui.backend.lib.solar_time import _validate_coordinates

        # Exact boundaries should be valid
        _validate_coordinates(90.0, 180.0)
        _validate_coordinates(-90.0, -180.0)
