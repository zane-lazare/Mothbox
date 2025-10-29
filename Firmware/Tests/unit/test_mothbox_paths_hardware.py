"""
Unit tests for mothbox_paths.py hardware configuration functions.

This test module addresses Gap #1 from Issue #13 by providing comprehensive
test coverage for hardware configuration loading functions that previously
had no automated tests.

Test Coverage:
- get_control_values(): Configuration file parser (12 tests)
- get_gpio_pins(): Relay GPIO pin configuration (11 tests)
- get_epaper_pins(): E-paper display pin configuration (9 tests)
- get_mux_pins(): Multiplexer pin configuration (9 tests)
- get_hardware_config(): Complete hardware configuration (15 tests)

Each function is tested for:
1. Normal operation with valid configuration
2. Missing configuration file (fallback to defaults)
3. Invalid values (type errors, out-of-range values)
4. Partial configuration (some keys missing)
5. Edge cases (malformed files, special characters, whitespace)

Fixtures:
- temp_controls_file: Isolated controls.txt for testing (from conftest.py)
- controls_file_factory: Factory for creating custom configs (from conftest.py)
- assert_gpio_pins_equal: Helper for GPIO pin comparison (from conftest.py)

Related:
- Issue #13: https://github.com/zane-lazare/Mothbox/issues/13
- mothbox_paths.py: /home/zane/projects/Mothbox/Firmware/mothbox_paths.py
"""

import pytest
import sys
from pathlib import Path

# Add backend to path (standard pattern)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestGetControlValues:
    """
    Test get_control_values() function for parsing controls.txt.

    Function location: mothbox_paths.py:108-129

    Returns: Dict[str, str] of key-value pairs

    Edge cases:
    - Missing file returns empty dict
    - Comment lines (starting with #) are skipped
    - Empty lines are skipped
    - Values can contain '=' character (maxsplit=1)
    - Whitespace is stripped from keys and values (Issue #13 bug fix)
    """

    def test_reads_simple_key_value_pairs(self, temp_controls_file):
        """Test basic parsing of key=value format"""
        temp_controls_file.write_text(
            "key1=value1\n"
            "key2=value2\n"
            "key3=value3\n"
        )

        from mothbox_paths import get_control_values
        values = get_control_values(temp_controls_file)

        assert len(values) == 3
        assert values['key1'] == 'value1'
        assert values['key2'] == 'value2'
        assert values['key3'] == 'value3'
        print("\n✓ Basic key=value parsing works")

    def test_skips_comment_lines(self, temp_controls_file):
        """Should skip lines starting with #"""
        temp_controls_file.write_text(
            "# This is a comment\n"
            "key1=value1\n"
            "# Another comment\n"
            "key2=value2\n"
            "## Multiple hashes\n"
        )

        from mothbox_paths import get_control_values
        values = get_control_values(temp_controls_file)

        assert len(values) == 2
        assert '#' not in str(values)
        assert values['key1'] == 'value1'
        assert values['key2'] == 'value2'
        print("✓ Comment lines skipped")

    def test_skips_blank_lines(self, temp_controls_file):
        """Should skip empty lines"""
        temp_controls_file.write_text(
            "key1=value1\n"
            "\n"
            "   \n"  # Whitespace-only line
            "key2=value2\n"
            "\n"
        )

        from mothbox_paths import get_control_values
        values = get_control_values(temp_controls_file)

        assert len(values) == 2
        assert values['key1'] == 'value1'
        assert values['key2'] == 'value2'
        print("✓ Blank lines skipped")

    def test_handles_missing_file(self, tmp_path):
        """Should return empty dict for non-existent file"""
        non_existent = tmp_path / "missing.txt"

        from mothbox_paths import get_control_values
        values = get_control_values(non_existent)

        assert values == {}
        print("✓ Missing file returns empty dict")

    def test_preserves_values_with_equals_signs(self, temp_controls_file):
        """Test that values containing = are preserved correctly"""
        temp_controls_file.write_text(
            "equation=E=mc^2\n"
            "formula=a=b+c\n"
            "url=https://example.com?key=value\n"
        )

        from mothbox_paths import get_control_values
        values = get_control_values(temp_controls_file)

        assert values['equation'] == 'E=mc^2'
        assert values['formula'] == 'a=b+c'
        assert values['url'] == 'https://example.com?key=value'
        print("✓ Values with = preserved (maxsplit=1)")

    def test_strips_whitespace_from_keys_and_values(self, temp_controls_file):
        """Test that whitespace around keys and values is stripped (Issue #13 bug fix)"""
        temp_controls_file.write_text(
            " key1 = value1 \n"  # Leading/trailing spaces
            "key2=  value2  \n"  # Spaces in value only
            "  key3=value3\n"     # Leading space on key
        )

        from mothbox_paths import get_control_values
        values = get_control_values(temp_controls_file)

        # After bug fix, whitespace should be stripped
        assert values['key1'] == 'value1', "Whitespace should be stripped from key and value"
        assert values['key2'] == 'value2', "Whitespace should be stripped from value"
        assert values['key3'] == 'value3', "Leading whitespace should be stripped from key"
        print("✓ Whitespace stripped from keys and values")

    def test_handles_empty_file(self, temp_controls_file):
        """Should return empty dict for empty file"""
        temp_controls_file.write_text("")

        from mothbox_paths import get_control_values
        values = get_control_values(temp_controls_file)

        assert values == {}
        print("✓ Empty file returns empty dict")

    def test_handles_lines_without_equals(self, temp_controls_file):
        """Malformed lines without = should be skipped"""
        temp_controls_file.write_text(
            "key1=value1\n"
            "this line has no equals\n"
            "key2=value2\n"
            "another bad line\n"
        )

        from mothbox_paths import get_control_values
        values = get_control_values(temp_controls_file)

        assert len(values) == 2
        assert values['key1'] == 'value1'
        assert values['key2'] == 'value2'
        print("✓ Lines without = skipped")

    def test_handles_empty_values(self, temp_controls_file):
        """Should handle key= (empty value)"""
        temp_controls_file.write_text(
            "key1=\n"
            "key2=value2\n"
            "key3=  \n"  # Whitespace-only value
        )

        from mothbox_paths import get_control_values
        values = get_control_values(temp_controls_file)

        assert values['key1'] == ''
        assert values['key2'] == 'value2'
        assert values['key3'] == ''  # Stripped to empty
        print("✓ Empty values handled")

    def test_handles_unicode_characters(self, temp_controls_file):
        """Should handle non-ASCII characters in values"""
        temp_controls_file.write_text(
            "name=Mosquitō\n"
            "location=São Paulo\n"
            "emoji=🦟\n"
        )

        from mothbox_paths import get_control_values
        values = get_control_values(temp_controls_file)

        assert values['name'] == 'Mosquitō'
        assert values['location'] == 'São Paulo'
        assert values['emoji'] == '🦟'
        print("✓ Unicode characters handled")

    def test_handles_very_long_lines(self, temp_controls_file):
        """Should handle very long lines without arbitrary limits"""
        long_value = "A" * 5000
        temp_controls_file.write_text(f"long_key={long_value}\n")

        from mothbox_paths import get_control_values
        values = get_control_values(temp_controls_file)

        assert values['long_key'] == long_value
        assert len(values['long_key']) == 5000
        print("✓ Long lines handled (5000 characters)")

    def test_multiple_files(self, controls_file_factory):
        """Can parse different files"""
        config1 = controls_file_factory("key=value1\n")
        config2 = controls_file_factory("key=value2\n")

        from mothbox_paths import get_control_values
        values1 = get_control_values(config1)
        values2 = get_control_values(config2)

        assert values1['key'] == 'value1'
        assert values2['key'] == 'value2'
        print("✓ Multiple files can be parsed")


class TestGetGpioPins:
    """
    Test get_gpio_pins() function for relay GPIO pin configuration.

    Function location: mothbox_paths.py:239-267

    Returns: {'Relay_Ch1': int, 'Relay_Ch2': int, 'Relay_Ch3': int}

    Default behavior: Falls back to 4.x firmware defaults (26/20/21) on error

    Configuration keys:
    - Relay_Ch1: Channel 1 GPIO pin (BCM numbering)
    - Relay_Ch2: Channel 2 GPIO pin (BCM numbering)
    - Relay_Ch3: Channel 3 GPIO pin (BCM numbering)

    Error handling: Returns defaults on FileNotFoundError, ValueError, KeyError
    GPIO validation: Pins must be in range 0-27 (BCM mode)
    """

    def test_returns_defaults_when_file_missing(self, tmp_path, monkeypatch):
        """Test that missing controls.txt returns 4.x defaults"""
        import mothbox_paths

        # Point to non-existent file
        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        # Verify 4.x defaults
        assert pins == {
            'Relay_Ch1': 26,
            'Relay_Ch2': 20,
            'Relay_Ch3': 21
        }
        print("\n✓ 4.x defaults (26/20/21) returned when file missing")

    def test_reads_relay_ch1_from_config(self, temp_controls_file, monkeypatch):
        """Should read custom Relay_Ch1 value"""
        temp_controls_file.write_text("Relay_Ch1=5\n")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        assert pins['Relay_Ch1'] == 5
        print("✓ Custom Relay_Ch1=5 read from config")

    def test_reads_relay_ch2_from_config(self, temp_controls_file, monkeypatch):
        """Should read custom Relay_Ch2 value"""
        temp_controls_file.write_text("Relay_Ch2=19\n")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        assert pins['Relay_Ch2'] == 19
        print("✓ Custom Relay_Ch2=19 read from config")

    def test_reads_relay_ch3_from_config(self, temp_controls_file, monkeypatch):
        """Should read custom Relay_Ch3 value"""
        temp_controls_file.write_text("Relay_Ch3=9\n")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        assert pins['Relay_Ch3'] == 9
        print("✓ Custom Relay_Ch3=9 read from config")

    def test_reads_all_three_channels(self, temp_controls_file, monkeypatch):
        """Should read complete custom configuration"""
        temp_controls_file.write_text(
            "Relay_Ch1=5\n"
            "Relay_Ch2=19\n"
            "Relay_Ch3=9\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        assert pins == {
            'Relay_Ch1': 5,
            'Relay_Ch2': 19,
            'Relay_Ch3': 9
        }
        print("✓ All 3 channels read (5.x firmware config)")

    def test_uses_default_when_key_missing(self, temp_controls_file, monkeypatch):
        """Should use default for missing keys in partial config"""
        temp_controls_file.write_text("Relay_Ch1=5\n")  # Only Ch1

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        assert pins['Relay_Ch1'] == 5      # Custom
        assert pins['Relay_Ch2'] == 20     # Default
        assert pins['Relay_Ch3'] == 21     # Default
        print("✓ Partial config: Ch1 custom, Ch2/Ch3 defaults")

    def test_converts_string_to_integer(self, temp_controls_file, monkeypatch):
        """Should convert string values to integers"""
        temp_controls_file.write_text(
            "Relay_Ch1=5\n"
            "Relay_Ch2=19\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        assert isinstance(pins['Relay_Ch1'], int)
        assert isinstance(pins['Relay_Ch2'], int)
        assert isinstance(pins['Relay_Ch3'], int)
        print("✓ Values converted to integers")

    def test_handles_invalid_pin_value_gracefully(self, temp_controls_file, monkeypatch):
        """Should fall back to defaults on ValueError (invalid int)"""
        temp_controls_file.write_text("Relay_Ch1=not_a_number\n")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        # Should fall back to defaults
        assert pins == {
            'Relay_Ch1': 26,
            'Relay_Ch2': 20,
            'Relay_Ch3': 21
        }
        print("✓ Invalid value triggers fallback to defaults")

    def test_handles_whitespace_in_values(self, temp_controls_file, monkeypatch):
        """Should handle whitespace around values (tests bug fix)"""
        temp_controls_file.write_text(
            "Relay_Ch1= 5 \n"
            "Relay_Ch2=19  \n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        assert pins['Relay_Ch1'] == 5
        assert pins['Relay_Ch2'] == 19
        print("✓ Whitespace stripped before int conversion")

    def test_rejects_invalid_gpio_pins(self, temp_controls_file, monkeypatch):
        """Should reject GPIO pins outside valid BCM range (Issue #13 validation)"""
        temp_controls_file.write_text("Relay_Ch1=100\n")  # Way out of range

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        # Should fall back to defaults when validation fails
        assert pins == {
            'Relay_Ch1': 26,
            'Relay_Ch2': 20,
            'Relay_Ch3': 21
        }
        print("✓ Out-of-range pin (100) triggers fallback to defaults")

    def test_returns_dict_with_three_keys(self, temp_controls_file, monkeypatch):
        """Should always return dict with exactly 3 keys"""
        temp_controls_file.write_text("")  # Empty config

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        assert len(pins) == 3
        assert 'Relay_Ch1' in pins
        assert 'Relay_Ch2' in pins
        assert 'Relay_Ch3' in pins
        print("✓ Always returns 3 keys")

    def test_warns_about_i2c_reserved_pins(self, temp_controls_file, monkeypatch, capfd):
        """Should warn when using GPIO 0 or 1 (typically reserved for I2C)"""
        temp_controls_file.write_text("Relay_Ch1=0\n")  # GPIO 0 is I2C

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_gpio_pins
        pins = get_gpio_pins()

        # Should accept but warn
        assert pins['Relay_Ch1'] == 0

        # Check warning was printed to stderr
        captured = capfd.readouterr()
        assert 'Warning:' in captured.err
        assert 'I2C' in captured.err
        print("✓ Warning issued for I2C reserved pins (0, 1)")


class TestGetEpaperPins:
    """
    Test get_epaper_pins() function for e-paper display pin configuration.

    Function location: mothbox_paths.py:270-302

    Returns: {'RST_PIN': int, 'DC_PIN': int, 'CS_PIN': int, 'BUSY_PIN': int, 'PWR_PIN': int}

    Default pins for Waveshare 2.13" e-paper display:
    - RST_PIN: 17
    - DC_PIN: 25
    - CS_PIN: 8
    - BUSY_PIN: 24
    - PWR_PIN: 18

    Config key mapping:
    - epaper_rst_pin → RST_PIN
    - epaper_dc_pin → DC_PIN
    - epaper_cs_pin → CS_PIN
    - epaper_busy_pin → BUSY_PIN
    - epaper_pwr_pin → PWR_PIN

    GPIO validation: Pins must be in range 0-27 (BCM mode)
    """

    def test_returns_all_five_pins(self, temp_controls_file, monkeypatch):
        """Should return dict with all 5 pin keys"""
        temp_controls_file.write_text("")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_epaper_pins
        pins = get_epaper_pins()

        assert len(pins) == 5
        assert 'RST_PIN' in pins
        assert 'DC_PIN' in pins
        assert 'CS_PIN' in pins
        assert 'BUSY_PIN' in pins
        assert 'PWR_PIN' in pins
        print("\n✓ All 5 e-paper pins present")

    def test_default_pin_values(self, tmp_path, monkeypatch):
        """Should return default Waveshare 2.13\" pin values"""
        import mothbox_paths

        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_epaper_pins
        pins = get_epaper_pins()

        assert pins == {
            'RST_PIN': 17,
            'DC_PIN': 25,
            'CS_PIN': 8,
            'BUSY_PIN': 24,
            'PWR_PIN': 18,
        }
        print("✓ Waveshare 2.13\" defaults (17/25/8/24/18)")

    def test_reads_from_controls_file(self, temp_controls_file, monkeypatch):
        """Should read custom pin values from config"""
        temp_controls_file.write_text(
            "epaper_rst_pin=22\n"
            "epaper_dc_pin=27\n"
            "epaper_cs_pin=7\n"
            "epaper_busy_pin=23\n"
            "epaper_pwr_pin=16\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_epaper_pins
        pins = get_epaper_pins()

        assert pins['RST_PIN'] == 22
        assert pins['DC_PIN'] == 27
        assert pins['CS_PIN'] == 7
        assert pins['BUSY_PIN'] == 23
        assert pins['PWR_PIN'] == 16
        print("✓ Custom e-paper pins read from config")

    def test_correct_config_key_mapping(self, temp_controls_file, monkeypatch):
        """Verify config key naming (epaper_*_pin → *_PIN)"""
        temp_controls_file.write_text("epaper_rst_pin=10\n")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_epaper_pins
        pins = get_epaper_pins()

        # Config uses lowercase snake_case, return uses UPPER_CASE
        assert pins['RST_PIN'] == 10
        print("✓ Config key mapping: epaper_rst_pin → RST_PIN")

    def test_applies_defaults_for_missing_keys(self, temp_controls_file, monkeypatch):
        """Should use defaults for missing keys in partial config"""
        temp_controls_file.write_text("epaper_rst_pin=10\n")  # Only RST

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_epaper_pins
        pins = get_epaper_pins()

        assert pins['RST_PIN'] == 10    # Custom
        assert pins['DC_PIN'] == 25     # Default
        assert pins['CS_PIN'] == 8      # Default
        assert pins['BUSY_PIN'] == 24   # Default
        assert pins['PWR_PIN'] == 18    # Default
        print("✓ Partial config: RST custom, others default")

    def test_handles_invalid_values(self, temp_controls_file, monkeypatch):
        """Should fall back to defaults on invalid values"""
        temp_controls_file.write_text("epaper_rst_pin=invalid\n")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_epaper_pins
        pins = get_epaper_pins()

        # Should fall back to all defaults
        assert pins == {
            'RST_PIN': 17,
            'DC_PIN': 25,
            'CS_PIN': 8,
            'BUSY_PIN': 24,
            'PWR_PIN': 18,
        }
        print("✓ Invalid value triggers fallback to defaults")

    def test_handles_missing_file(self, tmp_path, monkeypatch):
        """Should return defaults when file doesn't exist"""
        import mothbox_paths

        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_epaper_pins
        pins = get_epaper_pins()

        assert len(pins) == 5
        assert pins['RST_PIN'] == 17
        print("✓ Missing file returns defaults")

    def test_type_conversion(self, temp_controls_file, monkeypatch):
        """Values should be converted to integers"""
        temp_controls_file.write_text("epaper_rst_pin=17\n")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_epaper_pins
        pins = get_epaper_pins()

        for pin_name, pin_value in pins.items():
            assert isinstance(pin_value, int), f"{pin_name} should be int"
        print("✓ All pin values are integers")

    def test_rejects_invalid_gpio_pins(self, temp_controls_file, monkeypatch):
        """Should reject GPIO pins outside valid BCM range"""
        temp_controls_file.write_text("epaper_rst_pin=50\n")  # Out of range

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_epaper_pins
        pins = get_epaper_pins()

        # Should fall back to defaults
        assert pins['RST_PIN'] == 17
        print("✓ Out-of-range pin (50) triggers fallback")


class TestGetMuxPins:
    """
    Test get_mux_pins() function for multiplexer pin configuration.

    Function location: mothbox_paths.py:305-341

    Returns: 7 keys {'EN_A', 'EN_B', 'S0', 'S1', 'S2', 'S3', 'SIG'}

    Default pins for CD74HC4067 dual multiplexer:
    - EN_A: 31, EN_B: 29, S0: 33, S1: 13, S2: 12, S3: 15, SIG: 36

    Config key mapping:
    - mux_en_a → EN_A
    - mux_en_b → EN_B
    - mux_s0 → S0
    - mux_s1 → S1
    - mux_s2 → S2
    - mux_s3 → S3
    - mux_sig → SIG

    Important: BOARD mode numbering (physical pins 1-40), not BCM!
    """

    def test_returns_all_seven_pins(self, temp_controls_file, monkeypatch):
        """Should return dict with all 7 multiplexer pins"""
        temp_controls_file.write_text("")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_mux_pins
        pins = get_mux_pins()

        assert len(pins) == 7
        assert 'EN_A' in pins
        assert 'EN_B' in pins
        assert 'S0' in pins
        assert 'S1' in pins
        assert 'S2' in pins
        assert 'S3' in pins
        assert 'SIG' in pins
        print("\n✓ All 7 multiplexer pins present")

    def test_default_pin_values(self, tmp_path, monkeypatch):
        """Should return default CD74HC4067 pin values"""
        import mothbox_paths

        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_mux_pins
        pins = get_mux_pins()

        assert pins == {
            'EN_A': 31,
            'EN_B': 29,
            'S0': 33,
            'S1': 13,
            'S2': 12,
            'S3': 15,
            'SIG': 36,
        }
        print("✓ CD74HC4067 defaults (31/29/33/13/12/15/36)")

    def test_reads_from_controls_file(self, temp_controls_file, monkeypatch):
        """Should read custom multiplexer pins from config"""
        temp_controls_file.write_text(
            "mux_en_a=11\n"
            "mux_en_b=13\n"
            "mux_s0=15\n"
            "mux_s1=16\n"
            "mux_s2=18\n"
            "mux_s3=22\n"
            "mux_sig=7\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_mux_pins
        pins = get_mux_pins()

        assert pins['EN_A'] == 11
        assert pins['EN_B'] == 13
        assert pins['S0'] == 15
        assert pins['S1'] == 16
        assert pins['S2'] == 18
        assert pins['S3'] == 22
        assert pins['SIG'] == 7
        print("✓ Custom multiplexer pins read from config")

    def test_correct_config_key_mapping(self, temp_controls_file, monkeypatch):
        """Verify config key naming (mux_* → UPPER_CASE)"""
        temp_controls_file.write_text("mux_en_a=11\n")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_mux_pins
        pins = get_mux_pins()

        assert pins['EN_A'] == 11
        print("✓ Config key mapping: mux_en_a → EN_A")

    def test_applies_defaults_for_missing_keys(self, temp_controls_file, monkeypatch):
        """Should use defaults for missing keys in partial config"""
        temp_controls_file.write_text("mux_en_a=11\n")  # Only EN_A

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_mux_pins
        pins = get_mux_pins()

        assert pins['EN_A'] == 11    # Custom
        assert pins['EN_B'] == 29    # Default
        assert pins['S0'] == 33      # Default
        print("✓ Partial config: EN_A custom, others default")

    def test_handles_invalid_values(self, temp_controls_file, monkeypatch):
        """Should fall back to defaults on invalid values"""
        temp_controls_file.write_text("mux_en_a=invalid\n")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_mux_pins
        pins = get_mux_pins()

        # Should fall back to all defaults
        assert pins == {
            'EN_A': 31,
            'EN_B': 29,
            'S0': 33,
            'S1': 13,
            'S2': 12,
            'S3': 15,
            'SIG': 36,
        }
        print("✓ Invalid value triggers fallback to defaults")

    def test_handles_missing_file(self, tmp_path, monkeypatch):
        """Should return defaults when file doesn't exist"""
        import mothbox_paths

        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_mux_pins
        pins = get_mux_pins()

        assert len(pins) == 7
        assert pins['EN_A'] == 31
        print("✓ Missing file returns defaults")

    def test_type_conversion(self, temp_controls_file, monkeypatch):
        """Values should be converted to integers"""
        temp_controls_file.write_text("mux_en_a=31\n")

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_mux_pins
        pins = get_mux_pins()

        for pin_name, pin_value in pins.items():
            assert isinstance(pin_value, int), f"{pin_name} should be int"
        print("✓ All pin values are integers")

    def test_board_mode_pin_numbers(self, tmp_path, monkeypatch):
        """Multiplexer uses BOARD mode (1-40), not BCM (0-27)"""
        import mothbox_paths

        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_mux_pins
        pins = get_mux_pins()

        # BOARD mode allows values > 27 (up to 40)
        assert pins['EN_A'] == 31  # Valid in BOARD mode (pin 31)
        assert pins['S0'] == 33    # Valid in BOARD mode (pin 33)
        assert pins['SIG'] == 36   # Valid in BOARD mode (pin 36)
        print("✓ BOARD mode pins (31, 33, 36) accepted")

    def test_rejects_board_mode_out_of_range(self, temp_controls_file, monkeypatch):
        """Should reject BOARD mode pins outside 1-40 range"""
        temp_controls_file.write_text("mux_en_a=50\n")  # Out of BOARD range

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_mux_pins
        pins = get_mux_pins()

        # Should fall back to defaults
        assert pins['EN_A'] == 31
        print("✓ BOARD mode out-of-range pin (50) triggers fallback")


class TestGetHardwareConfig:
    """
    Test get_hardware_config() function for complete hardware configuration.

    Function location: mothbox_paths.py:344-449

    Returns: Dict with 32 keys covering 7 hardware modules:
    1. Relay Module (1 key): relay_enabled
    2. INA260 Power Sensor (2 keys): ina260_enabled, ina260_address
    3. E-paper Display (6 keys): epaper_enabled + 5 pins
    4. GPS Module (9 keys): gps_enabled + device + baudrate + 5 timeouts
    5. Light Sensor (3 keys): light_sensor_enabled + type + address
    6. PCA9536 GPIO Expander (2 keys): pca9536_enabled + address
    7. Multiplexer (10 keys): mux_enabled + type + address + 7 pins

    Important parsing rules:
    - Boolean: config.get().lower() == 'true' (case-INsensitive due to .lower())
    - Hex addresses: Require '0x' prefix (parsed with base 16)
    - Integers: Standard decimal parsing
    - Strings: Preserved as-is (device paths, sensor types)

    Defaults:
    - relay_enabled: True (only module enabled by default)
    - All other modules: False (disabled by default)
    """

    def test_returns_all_32_keys(self, tmp_path, monkeypatch):
        """Should return dict with all 32 hardware configuration keys"""
        import mothbox_paths

        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        # Should have exactly 32 keys
        assert len(config) == 32, f"Expected 32 keys, got {len(config)}"
        print(f"\n✓ All 32 hardware config keys present")

    def test_relay_enabled_defaults_true(self, tmp_path, monkeypatch):
        """Relay module should be enabled by default"""
        import mothbox_paths

        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert config['relay_enabled'] is True
        print("✓ relay_enabled defaults to True")

    def test_other_modules_disabled_by_default(self, tmp_path, monkeypatch):
        """All non-relay modules should be disabled by default"""
        import mothbox_paths

        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert config['ina260_enabled'] is False
        assert config['epaper_enabled'] is False
        assert config['gps_enabled'] is False
        assert config['light_sensor_enabled'] is False
        assert config['pca9536_enabled'] is False
        assert config['mux_enabled'] is False
        print("✓ All non-relay modules disabled by default")

    def test_boolean_parsing_case_insensitive(self, temp_controls_file, monkeypatch):
        """Boolean parsing is case-insensitive due to .lower() before comparison"""
        temp_controls_file.write_text(
            "relay_enabled=true\n"       # Lowercase - should work
            "ina260_enabled=True\n"      # Uppercase T - works (converted to lowercase)
            "gps_enabled=TRUE\n"         # All caps - works (converted to lowercase)
            "epaper_enabled=false\n"     # Anything but 'true' is false
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert config['relay_enabled'] is True       # 'true' works
        assert config['ina260_enabled'] is True      # 'True' → 'true' works
        assert config['gps_enabled'] is True         # 'TRUE' → 'true' works
        assert config['epaper_enabled'] is False     # 'false' != 'true'
        print("✓ Boolean parsing is case-insensitive (.lower() before comparison)")

    def test_hex_address_parsing(self, temp_controls_file, monkeypatch):
        """Hex addresses should be correctly parsed with 0x prefix"""
        temp_controls_file.write_text(
            "ina260_address=0x40\n"
            "light_sensor_address=0x29\n"
            "pca9536_address=0x21\n"
            "mux_address=0x20\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert config['ina260_address'] == 64         # 0x40 = 64
        assert config['light_sensor_address'] == 41   # 0x29 = 41
        assert config['pca9536_address'] == 33        # 0x21 = 33
        assert config['mux_address'] == 32            # 0x20 = 32
        print("✓ Hex addresses parsed correctly (0x40 = 64)")

    def test_hex_address_requires_0x_prefix(self, temp_controls_file, monkeypatch):
        """Hex addresses need 0x prefix (without it, still parsed as hex base 16)"""
        temp_controls_file.write_text("ina260_address=40\n")  # No 0x prefix

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        # int('40', 16) = 64, not 40!
        assert config['ina260_address'] == 64
        print("✓ '40' without 0x still parsed as hex (base 16)")

    def test_integer_parsing(self, temp_controls_file, monkeypatch):
        """Integer values should be parsed correctly"""
        temp_controls_file.write_text(
            "gps_baudrate=115200\n"
            "gps_timeout=120\n"
            "gps_timeout_hot=30\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert config['gps_baudrate'] == 115200
        assert config['gps_timeout'] == 120
        assert config['gps_timeout_hot'] == 30
        assert isinstance(config['gps_baudrate'], int)
        print("✓ Integer values parsed correctly")

    def test_string_values_preserved(self, temp_controls_file, monkeypatch):
        """String values should be preserved as-is"""
        temp_controls_file.write_text(
            "gps_device=/dev/ttyUSB0\n"
            "light_sensor_type=BH1750\n"
            "mux_type=gpio\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert config['gps_device'] == '/dev/ttyUSB0'
        assert config['light_sensor_type'] == 'BH1750'
        assert config['mux_type'] == 'gpio'
        print("✓ String values preserved")

    def test_gps_adaptive_timeouts_all_present(self, tmp_path, monkeypatch):
        """GPS module should have all 5 adaptive timeout keys"""
        import mothbox_paths

        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        # 5 GPS timeout keys
        assert 'gps_timeout' in config           # General timeout
        assert 'gps_timeout_hot' in config       # < 4 hours
        assert 'gps_timeout_warm' in config      # 4h - 6d
        assert 'gps_timeout_cold' in config      # 6d - 28d
        assert 'gps_timeout_almanac' in config   # > 28d

        # Verify defaults
        assert config['gps_timeout'] == 60
        assert config['gps_timeout_hot'] == 15
        assert config['gps_timeout_warm'] == 60
        assert config['gps_timeout_cold'] == 90
        assert config['gps_timeout_almanac'] == 1200
        print("✓ All 5 GPS adaptive timeouts present with defaults")

    def test_handles_missing_controls_file(self, tmp_path, monkeypatch):
        """Should return defaults when controls.txt doesn't exist"""
        import mothbox_paths

        non_existent = tmp_path / "missing.txt"
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', non_existent)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert len(config) == 32
        assert config['relay_enabled'] is True
        assert config['gps_device'] == '/dev/ttyAMA0'
        print("✓ Missing file returns all 32 defaults")

    def test_handles_partial_configuration(self, temp_controls_file, monkeypatch):
        """Should use defaults for missing keys in partial config"""
        temp_controls_file.write_text(
            "ina260_enabled=true\n"
            "ina260_address=0x40\n"
            # GPS keys missing - should use defaults
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        # Verify custom INA260 config
        assert config['ina260_enabled'] is True
        assert config['ina260_address'] == 64

        # Verify GPS defaults applied
        assert config['gps_enabled'] is False
        assert config['gps_device'] == '/dev/ttyAMA0'
        assert config['gps_baudrate'] == 9600
        print("✓ Partial config: INA260 custom, GPS defaults")

    def test_ina260_configuration(self, temp_controls_file, monkeypatch):
        """Test INA260 power sensor configuration"""
        temp_controls_file.write_text(
            "ina260_enabled=true\n"
            "ina260_address=0x40\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert config['ina260_enabled'] is True
        assert config['ina260_address'] == 64  # 0x40
        print("✓ INA260 configuration (enabled + address)")

    def test_epaper_configuration(self, temp_controls_file, monkeypatch):
        """Test e-paper display configuration (1 flag + 5 pins)"""
        temp_controls_file.write_text(
            "epaper_enabled=true\n"
            "epaper_rst_pin=17\n"
            "epaper_dc_pin=25\n"
            "epaper_cs_pin=8\n"
            "epaper_busy_pin=24\n"
            "epaper_pwr_pin=18\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert config['epaper_enabled'] is True
        assert config['epaper_rst_pin'] == 17
        assert config['epaper_dc_pin'] == 25
        assert config['epaper_cs_pin'] == 8
        assert config['epaper_busy_pin'] == 24
        assert config['epaper_pwr_pin'] == 18
        print("✓ E-paper configuration (enabled + 5 pins)")

    def test_light_sensor_configuration(self, temp_controls_file, monkeypatch):
        """Test light sensor configuration (enabled + type + address)"""
        temp_controls_file.write_text(
            "light_sensor_enabled=true\n"
            "light_sensor_type=BH1750\n"
            "light_sensor_address=0x23\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert config['light_sensor_enabled'] is True
        assert config['light_sensor_type'] == 'BH1750'
        assert config['light_sensor_address'] == 35  # 0x23
        print("✓ Light sensor configuration (enabled + type + address)")

    def test_multiplexer_configuration(self, temp_controls_file, monkeypatch):
        """Test multiplexer configuration (enabled + type + address + 7 pins)"""
        temp_controls_file.write_text(
            "mux_enabled=true\n"
            "mux_type=i2c\n"
            "mux_address=0x20\n"
            "mux_en_a=31\n"
            "mux_en_b=29\n"
            "mux_s0=33\n"
            "mux_s1=13\n"
            "mux_s2=12\n"
            "mux_s3=15\n"
            "mux_sig=36\n"
        )

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'CONTROLS_FILE', temp_controls_file)

        from mothbox_paths import get_hardware_config
        config = get_hardware_config()

        assert config['mux_enabled'] is True
        assert config['mux_type'] == 'i2c'
        assert config['mux_address'] == 32  # 0x20
        assert config['mux_en_a'] == 31
        assert config['mux_en_b'] == 29
        assert config['mux_s0'] == 33
        print("✓ Multiplexer configuration (enabled + type + address + 7 pins)")
