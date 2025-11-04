import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

"""
Regression test suite for capture_focus_bracket.py

This file contains permanent tests for bugs that were discovered and fixed
in the Mothbox focus bracket capture system. Each test should:

1. Reference the bug/issue number if available
2. Explain what broke and how
3. Verify the fix prevents regression
4. Include the date the bug was fixed

Regression tests should NEVER be removed, even if code is refactored.
They serve as permanent documentation and verification of historical bugs.

Related: Issue #13 4 - Focus bracket regression testing
"""

import pytest
import sys
import os as os_module  # Import os module for use in tests
from pathlib import Path
from unittest.mock import MagicMock

# Mock hardware dependencies before importing capture_focus_bracket
sys.modules['cv2'] = MagicMock()
sys.modules['picamera2'] = MagicMock()
sys.modules['picamera2.picamera2'] = MagicMock()
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['exif'] = MagicMock()
sys.modules['libcamera'] = MagicMock()
sys.modules['libcamera.controls'] = MagicMock()

# Add webui backend to path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend" / "scripts"))


class TestHistoricalBugs:
    """
    Tests for bugs that were fixed in production

    This test class contains permanent regression tests for critical bugs
    discovered during development and deployment. Each test documents a
    real bug, explains the impact, and verifies the fix.

    IMPORTANT: These tests should NEVER be deleted. They protect against
    regressions and serve as historical documentation.
    """

    def test_regression_line_109_undefined_root_variable(self, tmp_path, monkeypatch):
        """
        Regression test for critical bug on line 109 (Fixed: 2025-11-02)

        BUG DESCRIPTION:
        Line 109 of capture_focus_bracket.py used undefined variable 'root'
        instead of 'path' when constructing the path to camera_settings.csv
        on external media.

        CODE: file_path = os.path.join(root, "camera_settings.csv")
        FIX:  file_path = os.path.join(path, "camera_settings.csv")

        IMPACT:
        - Script crashed with NameError when external media was detected
        - Any USB drive with camera_settings.csv would cause system failure
        - Prevented field updates via USB configuration

        ROOT CAUSE:
        Variable naming inconsistency - loop variable was 'path' but code
        referenced 'root' (likely copied from os.walk() pattern)

        TEST VERIFIES:
        External media CSV detection works without NameError crash.

        Related: Issue #13 0 - Critical bug fix
        """
        # Create external camera_settings.csv
        external_csv = tmp_path / "camera_settings.csv"
        external_csv.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,10000,External settings\n"
            "AnalogueGain,2.5,External gain\n"
        )

        # Mock os.listdir to simulate finding camera_settings.csv in /media
        def mock_listdir(path_str):
            """Mock directory listing to return camera_settings.csv when checking /media"""
            if path_str == "/media":
                return ["camera_settings.csv"]
            elif path_str == "/mnt":
                return []
            else:
                raise FileNotFoundError(f"No such directory: {path_str}")

        # Mock os.path.join to return our test file path
        original_join = os_module.path.join
        def mock_join(path, filename):
            """Mock path joining to return test CSV for /media/camera_settings.csv"""
            if path == "/media" and filename == "camera_settings.csv":
                return str(external_csv)
            return original_join(path, filename)

        # Patch os functions
        monkeypatch.setattr('os.listdir', mock_listdir)
        monkeypatch.setattr('os.path.join', mock_join)

        # Import the function (will use patched os functions)
        from webui.backend.scripts.capture_focus_bracket import load_camera_settings

        # Call load_camera_settings - should NOT crash with NameError
        # The bug would cause: NameError: name 'root' is not defined
        settings = load_camera_settings()

        # Verify settings were loaded successfully
        assert settings is not None, "Settings should be loaded from external media"
        assert 'ExposureTime' in settings, "ExposureTime should be in loaded settings"
        assert settings['ExposureTime'] == 10000, "Should load external settings value"
        assert 'AnalogueGain' in settings, "AnalogueGain should be in loaded settings"
        assert settings['AnalogueGain'] == 2.5, "AnalogueGain should match external CSV"

    def test_regression_color_gains_tuple_format(self, tmp_path, monkeypatch):
        """
        Regression test for color gains tuple format (Preventive test)

        BUG DESCRIPTION:
        This is a preventive regression test to ensure color gains remain
        as a tuple (red, blue) and are not accidentally changed to a list,
        dict, or other format.

        IMPACT IF BROKEN:
        - Picamera2 expects tuple format for ColourGains control
        - Incorrect format would cause TypeError during capture
        - Focus bracket consistency would be compromised

        TEST VERIFIES:
        Color gains are correctly formatted as (red, blue) tuple when
        lock_colour_gains is enabled.

        Related: Issue #13 4 - Preventive regression test
        """
        # Mock build_picamera_controls to inspect colour_gains format
        colour_gains_calls = []
        def mock_build_controls(controls_dict):
            if 'colour_gains' in controls_dict:
                colour_gains_calls.append(controls_dict['colour_gains'])
            return controls_dict

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'build_picamera_controls', mock_build_controls)

        # Setup minimal environment
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)
        monkeypatch.setattr(focus_module, 'PHOTOS_DIR', photos_dir)

        # Create mock camera
        class MockRequest:
            def save(self, stream, filepath):
                Path(filepath).touch()
            def release(self):
                pass

        class MockPicamera2:
            def __init__(self):
                self.controls_history = []
            def set_controls(self, controls):
                self.controls_history.append(controls)
            def start(self):
                pass
            def capture_request(self, flush=True):
                return MockRequest()

        mock_camera = MockPicamera2()

        # Mock GPIOHandler
        class MockGPIOHandler:
            def flash_on(self):
                pass
            def flash_off(self):
                pass

        mock_gpio_handler = MockGPIOHandler()

        # Mock sleep
        monkeypatch.setattr('time.sleep', lambda x: None)

        from webui.backend.scripts.capture_focus_bracket import takePhoto_FocusBracket

        # Call with locked color gains
        takePhoto_FocusBracket(
            picam2=mock_camera,
            camera_settings={},
            num_steps=1,
            focus_start=5.0,
            focus_end=5.0,
            focus_settle_delay=100,
            flash_delay_before=50,
            flash_delay_after=0,
            lock_colour_gains=1,  # Enable locked gains
            colour_gain_red=2.5,
            colour_gain_blue=1.8,
            onlyflash=False,
            computerName="testbox",
            gpio_handler=mock_gpio_handler
        )

        # Verify colour gains were set as tuple
        assert len(colour_gains_calls) > 0, "Should have set colour gains"

        for gains in colour_gains_calls:
            # CRITICAL: Must be tuple, not list or other type
            assert isinstance(gains, tuple), f"Colour gains must be tuple, got {type(gains)}"
            assert len(gains) == 2, f"Colour gains must be 2-element tuple, got length {len(gains)}"
            assert gains == (2.5, 1.8), f"Colour gains values incorrect: {gains}"

            # Verify types are correct
            assert isinstance(gains[0], (int, float)), "Red gain must be numeric"
            assert isinstance(gains[1], (int, float)), "Blue gain must be numeric"

    def test_regression_request_release_leak(self, tmp_path, monkeypatch):
        """
        Regression test for request.release() memory leak (Preventive test)

        BUG DESCRIPTION:
        This preventive test ensures that capture requests are always released,
        even when errors occur. Failure to release requests causes memory leaks
        in long-running capture sessions.

        IMPACT IF BROKEN:
        - Memory consumption grows with each capture
        - System may run out of memory during long timelapse sessions
        - Camera may become unresponsive
        - Requires system reboot to recover

        TEST VERIFIES:
        request.release() is called for every capture_request() call,
        ensuring proper resource cleanup.

        Related: Issue #13 4 - Memory leak prevention
        """
        # Setup environment
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

        import webui.backend.scripts.capture_focus_bracket as focus_module
        monkeypatch.setattr(focus_module, 'PHOTOS_DIR', photos_dir)

        # Track request lifecycle
        requests_created = []
        requests_released = []

        class TrackingMockRequest:
            def __init__(self, req_id):
                self.req_id = req_id
                requests_created.append(req_id)

            def save(self, stream, filepath):
                Path(filepath).touch()

            def release(self):
                requests_released.append(self.req_id)

        class MockPicamera2:
            def __init__(self):
                self.request_counter = 0

            def set_controls(self, controls):
                pass

            def start(self):
                pass

            def capture_request(self, flush=True):
                self.request_counter += 1
                return TrackingMockRequest(self.request_counter)

        mock_camera = MockPicamera2()

        # Mock GPIOHandler
        class MockGPIOHandler:
            def flash_on(self):
                pass
            def flash_off(self):
                pass

        mock_gpio_handler = MockGPIOHandler()

        # Mock sleep
        monkeypatch.setattr('time.sleep', lambda x: None)

        from webui.backend.scripts.capture_focus_bracket import takePhoto_FocusBracket

        # Capture 5-step bracket
        takePhoto_FocusBracket(
            picam2=mock_camera,
            camera_settings={},
            num_steps=5,
            focus_start=2.0,
            focus_end=8.0,
            focus_settle_delay=100,
            flash_delay_before=50,
            flash_delay_after=0,
            lock_colour_gains=0,
            colour_gain_red=2.0,
            colour_gain_blue=1.5,
            onlyflash=False,
            computerName="testbox",
            gpio_handler=mock_gpio_handler
        )

        # CRITICAL: Every created request must be released
        assert len(requests_created) == 5, "Should create 5 requests"
        assert len(requests_released) == 5, "Should release 5 requests"
        assert requests_created == requests_released, "All requests must be released in order"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
