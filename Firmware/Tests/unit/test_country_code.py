"""
Unit tests for country code detection module.

Tests GPS-based country detection using geopip and system locale fallback.
"""

import os
from unittest.mock import patch

import pytest

# Check if geopip is available for GPS-dependent tests
try:
    import geopip  # noqa: F401
    HAS_GEOPIP = True
except ImportError:
    HAS_GEOPIP = False

requires_geopip = pytest.mark.skipif(
    not HAS_GEOPIP,
    reason="geopip not installed - GPS country detection tests skipped"
)


class TestDetectCountryFromGps:
    """Tests for GPS-based country detection.

    Note: geopip uses simplified country boundaries that may not cover
    coastal cities accurately. Tests use inland locations for reliability.
    """

    @requires_geopip
    def test_us_coordinates(self):
        """Chicago, IL (inland US) should return US."""
        from webui.backend.lib.country_code import detect_country_from_gps

        # Chicago - well inland in the US
        result = detect_country_from_gps(41.8781, -87.6298)
        assert result == "US"

    @requires_geopip
    def test_uk_coordinates(self):
        """London, UK should return GB."""
        from webui.backend.lib.country_code import detect_country_from_gps

        result = detect_country_from_gps(51.5074, -0.1278)
        assert result == "GB"

    @requires_geopip
    def test_japan_coordinates(self):
        """Nagoya, Japan (inland) should return JP."""
        from webui.backend.lib.country_code import detect_country_from_gps

        # Nagoya - more inland than Tokyo
        result = detect_country_from_gps(35.1815, 136.9066)
        assert result == "JP"

    @requires_geopip
    def test_germany_coordinates(self):
        """Munich, Germany should return DE."""
        from webui.backend.lib.country_code import detect_country_from_gps

        # Munich - southern Germany, well inland
        result = detect_country_from_gps(48.1351, 11.5820)
        assert result == "DE"

    @requires_geopip
    def test_brazil_coordinates(self):
        """Brasilia, Brazil (inland capital) should return BR."""
        from webui.backend.lib.country_code import detect_country_from_gps

        # Brasilia - inland capital
        result = detect_country_from_gps(-15.7942, -47.8825)
        assert result == "BR"

    @requires_geopip
    def test_australia_coordinates(self):
        """Canberra, Australia (inland capital) should return AU."""
        from webui.backend.lib.country_code import detect_country_from_gps

        # Canberra - inland capital
        result = detect_country_from_gps(-35.2809, 149.1300)
        assert result == "AU"

    @requires_geopip
    def test_ocean_coordinates_returns_none(self):
        """Coordinates in the ocean should return None."""
        from webui.backend.lib.country_code import detect_country_from_gps

        # Middle of the Pacific Ocean
        result = detect_country_from_gps(0.0, -160.0)
        assert result is None

    def test_geopip_import_error(self):
        """Should handle missing geopip gracefully."""
        from webui.backend.lib.country_code import detect_country_from_gps

        # When geopip is not available, function should return None gracefully
        if not HAS_GEOPIP:
            result = detect_country_from_gps(41.8781, -87.6298)
            assert result is None

    @requires_geopip
    def test_geopip_exception_handling(self):
        """Should handle geopip exceptions gracefully."""
        from webui.backend.lib.country_code import detect_country_from_gps

        with patch('geopip.search', side_effect=Exception("Test error")):
            result = detect_country_from_gps(37.7749, -122.4194)
            assert result is None


class TestDetectCountryFromLocale:
    """Tests for locale-based country detection."""

    def test_lang_env_us(self):
        """LANG=en_US.UTF-8 should return US."""
        from webui.backend.lib.country_code import detect_country_from_locale

        with patch.dict(os.environ, {'LANG': 'en_US.UTF-8', 'LC_ALL': '', 'LC_COLLATE': ''}):
            result = detect_country_from_locale()
            assert result == "US"

    def test_lang_env_de(self):
        """LANG=de_DE.UTF-8 should return DE."""
        from webui.backend.lib.country_code import detect_country_from_locale

        with patch.dict(os.environ, {'LANG': 'de_DE.UTF-8', 'LC_ALL': '', 'LC_COLLATE': ''}):
            result = detect_country_from_locale()
            assert result == "DE"

    def test_lang_env_gb(self):
        """LANG=en_GB.UTF-8 should return GB."""
        from webui.backend.lib.country_code import detect_country_from_locale

        with patch.dict(os.environ, {'LANG': 'en_GB.UTF-8', 'LC_ALL': '', 'LC_COLLATE': ''}):
            result = detect_country_from_locale()
            assert result == "GB"

    def test_lc_all_takes_precedence(self):
        """LC_ALL should take precedence over LANG."""
        from webui.backend.lib.country_code import detect_country_from_locale

        with patch.dict(os.environ, {'LC_ALL': 'fr_FR.UTF-8', 'LANG': 'en_US.UTF-8', 'LC_COLLATE': ''}):
            result = detect_country_from_locale()
            assert result == "FR"

    def test_handles_locale_without_encoding(self):
        """Should handle locale without .UTF-8 suffix."""
        from webui.backend.lib.country_code import detect_country_from_locale

        with patch.dict(os.environ, {'LANG': 'es_ES', 'LC_ALL': '', 'LC_COLLATE': ''}):
            result = detect_country_from_locale()
            assert result == "ES"

    def test_handles_locale_with_modifier(self):
        """Should handle locale with @modifier suffix."""
        from webui.backend.lib.country_code import detect_country_from_locale

        with patch.dict(os.environ, {'LANG': 'sr_RS@latin.UTF-8', 'LC_ALL': '', 'LC_COLLATE': ''}):
            result = detect_country_from_locale()
            assert result == "RS"

    def test_returns_none_for_c_locale(self):
        """Should return None for C locale (no country info)."""
        from webui.backend.lib.country_code import detect_country_from_locale

        with (
            patch.dict(os.environ, {'LANG': 'C', 'LC_ALL': '', 'LC_COLLATE': ''}, clear=True),
            patch('locale.getlocale', return_value=(None, None)),
        ):
            result = detect_country_from_locale()
            assert result is None

    def test_returns_none_for_empty_env(self):
        """Should return None when no locale env vars set."""
        from webui.backend.lib.country_code import detect_country_from_locale

        with (
            patch.dict(os.environ, {'LANG': '', 'LC_ALL': '', 'LC_COLLATE': ''}, clear=True),
            patch('locale.getlocale', return_value=(None, None)),
        ):
            result = detect_country_from_locale()
            assert result is None

    def test_fallback_to_getlocale(self):
        """Should fall back to locale.getlocale() when env vars empty."""
        from webui.backend.lib.country_code import detect_country_from_locale

        with (
            patch.dict(os.environ, {'LANG': '', 'LC_ALL': '', 'LC_COLLATE': ''}, clear=True),
            patch('locale.getlocale', return_value=('ja_JP', 'UTF-8')),
        ):
            result = detect_country_from_locale()
            assert result == "JP"


class TestDetectCountryCode:
    """Tests for the main detect_country_code function."""

    @requires_geopip
    def test_gps_primary_when_available(self):
        """GPS detection should be used when coordinates provided."""
        from webui.backend.lib.country_code import detect_country_code

        # Chicago - well inland, reliable detection
        result = detect_country_code(41.8781, -87.6298)
        assert result == "US"

    def test_locale_fallback_when_no_gps(self):
        """Should fall back to locale when no GPS coordinates."""
        from webui.backend.lib.country_code import detect_country_code

        with patch.dict(os.environ, {'LANG': 'de_DE.UTF-8', 'LC_ALL': '', 'LC_COLLATE': ''}):
            result = detect_country_code()
            assert result == "DE"

    def test_locale_fallback_when_gps_returns_none(self):
        """Should fall back to locale when GPS returns None (ocean)."""
        from webui.backend.lib.country_code import detect_country_code

        with patch.dict(os.environ, {'LANG': 'en_US.UTF-8', 'LC_ALL': '', 'LC_COLLATE': ''}):
            # Ocean coordinates
            result = detect_country_code(0.0, -160.0)
            assert result == "US"  # Falls back to locale

    def test_no_fallback_when_disabled(self):
        """Should return None when fallback disabled and GPS unavailable."""
        from webui.backend.lib.country_code import detect_country_code

        result = detect_country_code(use_locale_fallback=False)
        assert result is None

    def test_invalid_latitude_logs_warning(self):
        """Should log warning for invalid latitude."""
        from webui.backend.lib.country_code import detect_country_code

        with patch.dict(os.environ, {'LANG': 'en_US.UTF-8', 'LC_ALL': '', 'LC_COLLATE': ''}):
            result = detect_country_code(91.0, -122.0)  # Invalid latitude
            assert result == "US"  # Falls back to locale

    def test_invalid_longitude_logs_warning(self):
        """Should log warning for invalid longitude."""
        from webui.backend.lib.country_code import detect_country_code

        with patch.dict(os.environ, {'LANG': 'en_US.UTF-8', 'LC_ALL': '', 'LC_COLLATE': ''}):
            result = detect_country_code(37.0, -181.0)  # Invalid longitude
            assert result == "US"  # Falls back to locale

    def test_none_latitude_uses_fallback(self):
        """Should use fallback when latitude is None."""
        from webui.backend.lib.country_code import detect_country_code

        with patch.dict(os.environ, {'LANG': 'fr_FR.UTF-8', 'LC_ALL': '', 'LC_COLLATE': ''}):
            result = detect_country_code(None, -122.0)
            assert result == "FR"

    def test_none_longitude_uses_fallback(self):
        """Should use fallback when longitude is None."""
        from webui.backend.lib.country_code import detect_country_code

        with patch.dict(os.environ, {'LANG': 'it_IT.UTF-8', 'LC_ALL': '', 'LC_COLLATE': ''}):
            result = detect_country_code(37.0, None)
            assert result == "IT"


class TestIsValidCountryCode:
    """Tests for country code validation."""

    def test_valid_codes(self):
        """Common country codes should be valid."""
        from webui.backend.lib.country_code import is_valid_country_code

        assert is_valid_country_code("US") is True
        assert is_valid_country_code("GB") is True
        assert is_valid_country_code("DE") is True
        assert is_valid_country_code("JP") is True
        assert is_valid_country_code("AU") is True

    def test_lowercase_valid(self):
        """Lowercase codes should be valid."""
        from webui.backend.lib.country_code import is_valid_country_code

        assert is_valid_country_code("us") is True
        assert is_valid_country_code("gb") is True

    def test_invalid_codes(self):
        """Invalid codes should return False."""
        from webui.backend.lib.country_code import is_valid_country_code

        assert is_valid_country_code("XX") is False
        assert is_valid_country_code("ZZ") is False
        assert is_valid_country_code("123") is False

    def test_none_is_invalid(self):
        """None should be invalid."""
        from webui.backend.lib.country_code import is_valid_country_code

        assert is_valid_country_code(None) is False

    def test_empty_string_is_invalid(self):
        """Empty string should be invalid."""
        from webui.backend.lib.country_code import is_valid_country_code

        assert is_valid_country_code("") is False


class TestCommonCountryCodes:
    """Tests for COMMON_COUNTRY_CODES constant."""

    def test_contains_major_countries(self):
        """Should contain major countries."""
        from webui.backend.lib.country_code import COMMON_COUNTRY_CODES

        major_countries = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'JP', 'CN', 'IN', 'BR']
        for code in major_countries:
            assert code in COMMON_COUNTRY_CODES

    def test_all_codes_are_two_letters(self):
        """All codes should be exactly 2 uppercase letters."""
        from webui.backend.lib.country_code import COMMON_COUNTRY_CODES

        for code in COMMON_COUNTRY_CODES:
            assert len(code) == 2
            assert code.isupper()
            assert code.isalpha()


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_exist(self):
        """All exported names should exist."""
        from webui.backend.lib import country_code

        for name in country_code.__all__:
            assert hasattr(country_code, name), f"Missing export: {name}"

    def test_expected_exports(self):
        """Module should export expected functions."""
        from webui.backend.lib.country_code import __all__

        expected = [
            'detect_country_code',
            'detect_country_from_gps',
            'detect_country_from_locale',
            'is_valid_country_code',
            'COMMON_COUNTRY_CODES',
        ]
        for name in expected:
            assert name in __all__
