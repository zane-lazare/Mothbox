"""Tests for camera_settings_schema — shared type definitions."""

import pytest

from camera_settings_schema import (
    ALL_KNOWN_SETTINGS,
    BOOL_STRING_SETTINGS,
    FLOAT_SETTINGS,
    INT_SETTINGS,
    STRING_SETTINGS,
    WEBUI_ONLY_SETTINGS,
)

TYPE_SETS = [INT_SETTINGS, FLOAT_SETTINGS, BOOL_STRING_SETTINGS, STRING_SETTINGS]


class TestSetIntegrity:
    """Verify the type sets are well-formed and non-overlapping."""

    def test_no_overlapping_type_sets(self):
        """INT, FLOAT, BOOL_STRING, and STRING sets must be pairwise disjoint."""
        names = ["INT_SETTINGS", "FLOAT_SETTINGS", "BOOL_STRING_SETTINGS", "STRING_SETTINGS"]
        for i, (name_a, set_a) in enumerate(zip(names, TYPE_SETS, strict=True)):
            for name_b, set_b in zip(names[i + 1 :], TYPE_SETS[i + 1 :], strict=True):
                overlap = set_a & set_b
                assert not overlap, f"{name_a} and {name_b} overlap: {overlap}"

    def test_all_known_settings_is_complete_union(self):
        """ALL_KNOWN_SETTINGS must equal the union of all four type sets."""
        expected = INT_SETTINGS | FLOAT_SETTINGS | BOOL_STRING_SETTINGS | STRING_SETTINGS
        assert expected == ALL_KNOWN_SETTINGS

    def test_webui_only_settings_subset_of_all_known(self):
        """Every WEBUI_ONLY setting must be defined in a type set."""
        missing = WEBUI_ONLY_SETTINGS - ALL_KNOWN_SETTINGS
        assert not missing, f"WEBUI_ONLY_SETTINGS not in any type set: {missing}"

    def test_sets_are_non_empty(self):
        """Each type set should contain at least one setting."""
        assert len(INT_SETTINGS) > 0
        assert len(FLOAT_SETTINGS) > 0
        assert len(BOOL_STRING_SETTINGS) > 0
        assert len(STRING_SETTINGS) > 0
        assert len(WEBUI_ONLY_SETTINGS) > 0
        assert len(ALL_KNOWN_SETTINGS) > 0


class TestKnownSettingTypes:
    """Spot-check that well-known settings are in the correct type set."""

    @pytest.mark.parametrize(
        "setting",
        ["ExposureTime", "AfMode", "HDR", "NoiseReductionMode"],
    )
    def test_int_settings(self, setting):
        assert setting in INT_SETTINGS

    @pytest.mark.parametrize(
        "setting",
        ["LensPosition", "Sharpness", "AnalogueGain", "ExposureValue"],
    )
    def test_float_settings(self, setting):
        assert setting in FLOAT_SETTINGS

    @pytest.mark.parametrize(
        "setting",
        ["AeEnable", "AwbEnable", "LensShadingEnable"],
    )
    def test_bool_string_settings(self, setting):
        assert setting in BOOL_STRING_SETTINGS

    @pytest.mark.parametrize(
        "setting",
        ["Name", "FocusPeakingColour"],
    )
    def test_string_settings(self, setting):
        assert setting in STRING_SETTINGS
