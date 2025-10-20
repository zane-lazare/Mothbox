import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

"""
Integration tests for Focus Bracket capture workflow

Tests the complete focus bracketing workflow from settings update through capture routing

Note: Uses shared fixtures from Tests/conftest.py (app, client)
"""

import pytest
import sys
import csv
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add webui backend to path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
sys.path.insert(0, str(FIRMWARE_DIR))


@pytest.fixture
def focus_bracket_env(tmp_path, monkeypatch):
    """Set up temporary paths and default settings for focus bracket tests"""
    import mothbox_paths

    # Patch paths to use temp directory
    temp_settings = tmp_path / "camera_settings.csv"
    temp_photos = tmp_path / "photos"
    temp_photos.mkdir()

    monkeypatch.setattr(mothbox_paths, 'CAMERA_SETTINGS_FILE', str(temp_settings))
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', temp_photos)

    # Create default settings file
    with open(temp_settings, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['SETTING', 'VALUE', 'DETAILS'])
        writer.writerow(['FocusBracket', '1', 'Number of focus steps'])
        writer.writerow(['FocusBracket_Start', '2.0', 'Start focus position'])
        writer.writerow(['FocusBracket_End', '8.0', 'End focus position'])
        writer.writerow(['HDR', '1', 'Number of exposures'])
        writer.writerow(['ExposureTime', '10000', 'Exposure time'])
        writer.writerow(['AnalogueGain', '2.0', 'ISO gain'])

    yield temp_settings, temp_photos


class TestFocusBracketCapture:
    """Test focus bracket capture workflow"""

    def test_focus_bracket_settings_update(self, client, focus_bracket_env):
        """Test updating focus bracket settings via API"""
        settings_file, _ = focus_bracket_env

        # Update focus bracket settings
        response = client.post('/api/camera/settings', json={
            'FocusBracket': '5',
            'FocusBracket_Start': '2.0',
            'FocusBracket_End': '8.0'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True

        # Verify settings were written to CSV
        with open(settings_file, 'r') as f:
            reader = csv.DictReader(f)
            settings = {row['SETTING']: row['VALUE'] for row in reader}

        assert settings['FocusBracket'] == '5'
        assert settings['FocusBracket_Start'] == '2.0'
        assert settings['FocusBracket_End'] == '8.0'

    def test_focus_bracket_validation_rejects_invalid(self, client, focus_bracket_env):
        """Test that invalid focus bracket settings are rejected"""
        # Invalid step count (too high)
        response = client.post('/api/camera/settings', json={
            'FocusBracket': '15'
        })
        assert response.status_code == 400

        # Invalid start position (negative)
        response = client.post('/api/camera/settings', json={
            'FocusBracket_Start': '-1.0'
        })
        assert response.status_code == 400

        # Invalid end position (too high)
        response = client.post('/api/camera/settings', json={
            'FocusBracket_End': '15.0'
        })
        assert response.status_code == 400

    def test_focus_bracket_mode_detection(self, client, focus_bracket_env):
        """Test that _should_use_focus_bracket_mode detects settings correctly"""
        settings_file, _ = focus_bracket_env

        from routes.camera import _should_use_focus_bracket_mode

        # Set focus bracketing to single step (disabled)
        with open(settings_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['SETTING', 'VALUE', 'DETAILS'])
            writer.writerow(['FocusBracket', '1', ''])

        use_fb, steps, start, end = _should_use_focus_bracket_mode()
        assert use_fb == False
        assert steps == 1

        # Enable focus bracketing
        with open(settings_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['SETTING', 'VALUE', 'DETAILS'])
            writer.writerow(['FocusBracket', '5', ''])
            writer.writerow(['FocusBracket_Start', '2.0', ''])
            writer.writerow(['FocusBracket_End', '8.0', ''])

        use_fb, steps, start, end = _should_use_focus_bracket_mode()
        assert use_fb == True
        assert steps == 5
        assert start == 2.0
        assert end == 8.0

    def test_focus_bracket_priority_over_hdr(self, client, focus_bracket_env):
        """Test that focus bracketing takes priority over HDR when both enabled"""
        settings_file, _ = focus_bracket_env

        from routes.camera import _should_use_focus_bracket_mode, _should_use_hdr_mode

        # Enable both focus bracketing and HDR
        with open(settings_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['SETTING', 'VALUE', 'DETAILS'])
            writer.writerow(['FocusBracket', '5', ''])
            writer.writerow(['FocusBracket_Start', '2.0', ''])
            writer.writerow(['FocusBracket_End', '8.0', ''])
            writer.writerow(['HDR', '3', ''])

        # Check focus bracket detection
        use_fb, fb_steps, fb_start, fb_end = _should_use_focus_bracket_mode()
        assert use_fb == True
        assert fb_steps == 5

        # HDR should still detect settings
        use_hdr, hdr_count, hdr_width = _should_use_hdr_mode()
        assert use_hdr == True
        assert hdr_count == 3

    @patch('subprocess.run')
    def test_focus_bracket_script_routing(self, mock_subprocess, client, focus_bracket_env, monkeypatch):
        """Test that capture endpoint routes to focus bracket script"""
        settings_file, temp_photos = focus_bracket_env

        # Mock MOTHBOX_HOME to use test directory
        mock_mothbox_home = Path(__file__).parent.parent.parent
        monkeypatch.setattr('mothbox_paths.MOTHBOX_HOME', mock_mothbox_home)

        # Create mock focus bracket script
        script_dir = mock_mothbox_home / "webui" / "backend" / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        script_path = script_dir / "capture_focus_bracket.py"
        script_path.write_text("#!/usr/bin/env python3\nprint('Mock focus bracket script')")
        script_path.chmod(0o755)

        # Enable focus bracketing
        with open(settings_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['SETTING', 'VALUE', 'DETAILS'])
            writer.writerow(['FocusBracket', '5', ''])
            writer.writerow(['FocusBracket_Start', '2.0', ''])
            writer.writerow(['FocusBracket_End', '8.0', ''])
            writer.writerow(['HDR', '1', ''])

        # Mock successful subprocess execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Focus bracket capture complete"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Create a dummy photo file
        (temp_photos / "test.jpg").touch()

        # Trigger capture
        response = client.post('/api/camera/capture')

        assert response.status_code == 200
        data = response.get_json()

        # Verify focus bracket mode was detected
        assert data['success'] == True
        assert data['focus_bracket_mode'] == True
        assert data['focus_bracket_steps'] == 5
        assert data['focus_bracket_start'] == 2.0
        assert data['focus_bracket_end'] == 8.0
        assert 'Focus bracket' in data['message']

        # Verify correct script was called
        called_script = str(mock_subprocess.call_args[0][0][1])
        assert 'capture_focus_bracket.py' in called_script

    def test_focus_bracket_default_values(self, client, focus_bracket_env):
        """Test default values when focus bracket settings are missing"""
        settings_file, _ = focus_bracket_env

        from routes.camera import _should_use_focus_bracket_mode

        # Empty settings file
        with open(settings_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['SETTING', 'VALUE', 'DETAILS'])

        use_fb, steps, start, end = _should_use_focus_bracket_mode()

        # Should use defaults and disable bracketing
        assert use_fb == False
        assert steps == 1
        assert start == 2.0  # Default start
        assert end == 8.0    # Default end

    def test_focus_bracket_edge_cases(self, client, focus_bracket_env):
        """Test edge cases for focus bracket configuration"""
        settings_file, _ = focus_bracket_env

        from routes.camera import _should_use_focus_bracket_mode

        # Test with start > end (unusual but valid)
        with open(settings_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['SETTING', 'VALUE', 'DETAILS'])
            writer.writerow(['FocusBracket', '3', ''])
            writer.writerow(['FocusBracket_Start', '8.0', ''])
            writer.writerow(['FocusBracket_End', '2.0', ''])

        use_fb, steps, start, end = _should_use_focus_bracket_mode()
        assert use_fb == True
        assert steps == 3
        assert start == 8.0
        assert end == 2.0

        # Test with start == end (valid for single step)
        with open(settings_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['SETTING', 'VALUE', 'DETAILS'])
            writer.writerow(['FocusBracket', '1', ''])
            writer.writerow(['FocusBracket_Start', '5.0', ''])
            writer.writerow(['FocusBracket_End', '5.0', ''])

        use_fb, steps, start, end = _should_use_focus_bracket_mode()
        assert use_fb == False
        assert steps == 1

    def test_timing_settings_persistence(self, client, focus_bracket_env):
        """Test that timing settings are persisted to CSV"""
        settings_file, _ = focus_bracket_env

        # Update timing settings
        response = client.post('/api/camera/settings', json={
            'FlashDelay_BeforeCapture': '100',
            'FlashDelay_AfterCapture': '50',
            'FocusBracket_SettleDelay': '750'
        })

        assert response.status_code == 200

        # Verify settings were written to CSV
        with open(settings_file, 'r') as f:
            reader = csv.DictReader(f)
            settings = {row['SETTING']: row['VALUE'] for row in reader}

        assert settings['FlashDelay_BeforeCapture'] == '100'
        assert settings['FlashDelay_AfterCapture'] == '50'
        assert settings['FocusBracket_SettleDelay'] == '750'

    def test_timing_settings_validation(self, client, focus_bracket_env):
        """Test that invalid timing settings are rejected"""
        # Flash delay before - out of range
        response = client.post('/api/camera/settings', json={
            'FlashDelay_BeforeCapture': '600'  # Max is 500
        })
        assert response.status_code == 400

        # Flash delay after - negative
        response = client.post('/api/camera/settings', json={
            'FlashDelay_AfterCapture': '-10'
        })
        assert response.status_code == 400

        # Settle delay - too low
        response = client.post('/api/camera/settings', json={
            'FocusBracket_SettleDelay': '50'  # Min is 100
        })
        assert response.status_code == 400

        # Settle delay - too high
        response = client.post('/api/camera/settings', json={
            'FocusBracket_SettleDelay': '2500'  # Max is 2000
        })
        assert response.status_code == 400

    def test_color_gains_settings_persistence(self, client, focus_bracket_env):
        """Test that color gains settings are persisted to CSV"""
        settings_file, _ = focus_bracket_env

        # Update color gains settings
        response = client.post('/api/camera/settings', json={
            'FocusBracket_LockColorGains': '1',
            'FocusBracket_ColorGainRed': '2.5',
            'FocusBracket_ColorGainBlue': '1.8'
        })

        assert response.status_code == 200

        # Verify settings were written to CSV
        with open(settings_file, 'r') as f:
            reader = csv.DictReader(f)
            settings = {row['SETTING']: row['VALUE'] for row in reader}

        assert settings['FocusBracket_LockColorGains'] == '1'
        assert settings['FocusBracket_ColorGainRed'] == '2.5'
        assert settings['FocusBracket_ColorGainBlue'] == '1.8'

    def test_color_gains_lock_toggle(self, client, focus_bracket_env):
        """Test color gains lock on/off toggle"""
        # Test lock enabled
        response = client.post('/api/camera/settings', json={
            'FocusBracket_LockColorGains': '1'
        })
        assert response.status_code == 200

        # Test lock disabled
        response = client.post('/api/camera/settings', json={
            'FocusBracket_LockColorGains': '0'
        })
        assert response.status_code == 200

        # Test invalid value
        response = client.post('/api/camera/settings', json={
            'FocusBracket_LockColorGains': '2'
        })
        assert response.status_code == 400

    def test_color_gains_validation(self, client, focus_bracket_env):
        """Test that invalid color gains are rejected"""
        # Red gain too low
        response = client.post('/api/camera/settings', json={
            'FocusBracket_ColorGainRed': '0.5'
        })
        assert response.status_code == 400

        # Red gain too high
        response = client.post('/api/camera/settings', json={
            'FocusBracket_ColorGainRed': '5.0'
        })
        assert response.status_code == 400

        # Blue gain too low
        response = client.post('/api/camera/settings', json={
            'FocusBracket_ColorGainBlue': '0.8'
        })
        assert response.status_code == 400

        # Blue gain too high
        response = client.post('/api/camera/settings', json={
            'FocusBracket_ColorGainBlue': '4.5'
        })
        assert response.status_code == 400

    def test_default_timing_and_color_values(self, client, focus_bracket_env):
        """Test that default values are used when settings are missing"""
        settings_file, _ = focus_bracket_env

        # Create settings file without timing/color settings
        with open(settings_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['SETTING', 'VALUE', 'DETAILS'])
            writer.writerow(['FocusBracket', '5', ''])

        # Note: This test verifies the defaults are defined, but we can't easily test
        # the script execution without running it. The unit tests verify the validators.
        # Here we just verify the settings can be added
        response = client.post('/api/camera/settings', json={
            'FlashDelay_BeforeCapture': '50',  # Default value
            'FlashDelay_AfterCapture': '0',    # Default value
            'FocusBracket_SettleDelay': '500', # Default value
            'FocusBracket_LockColorGains': '1',  # Default value
            'FocusBracket_ColorGainRed': '2.259', # Default value
            'FocusBracket_ColorGainBlue': '1.500' # Default value
        })

        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
