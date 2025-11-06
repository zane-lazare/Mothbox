"""
Unit tests for configuration validation

RUN ON RASPBERRY PI ONLY - tests Flask routes
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestConfigDefaults:
    """Test configuration default values"""

    def test_jpeg_quality_default_is_85(self, client, temp_webui_settings):
        """Verify default JPEG quality is 85 when no config file exists"""
        from mothbox_paths import WEBUI_SETTINGS_FILE

        response = client.get('/api/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        # If config file exists, it will override defaults (which is correct behavior)
        # So we check: either matches default, or file exists with custom value
        if WEBUI_SETTINGS_FILE.exists():
            print(f"\n✓ Config file exists with jpeg_quality: {data['jpeg_quality']}")
            print(f"   (Existing settings take precedence over defaults)")
            assert 50 <= data['jpeg_quality'] <= 100, \
                f"Quality should be in valid range, got {data['jpeg_quality']}"
        else:
            assert data['jpeg_quality'] == 85, \
                f"Expected default jpeg_quality=85, got {data['jpeg_quality']}"
            print(f"\n✓ Default JPEG quality: {data['jpeg_quality']}")

    def test_all_default_values(self, client, temp_webui_settings):
        """Verify WebUI settings are loaded correctly"""
        from mothbox_paths import WEBUI_SETTINGS_FILE

        response = client.get('/api/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        # Expected defaults (used when no config file exists)
        expected_defaults = {
            'stream_width': 1024,
            'stream_height': 768,
            'frame_rate': 10,
            'jpeg_quality': 85
        }

        print(f"\n📋 WebUI Settings:")
        if WEBUI_SETTINGS_FILE.exists():
            print(f"   Source: {WEBUI_SETTINGS_FILE} (existing config)")
            # Just verify values are in valid ranges
            assert 320 <= data.get('stream_width', 0) <= 1920, "Width out of range"
            assert 240 <= data.get('stream_height', 0) <= 1080, "Height out of range"
            assert 1 <= data.get('frame_rate', 0) <= 30, "FPS out of range"
            assert 50 <= data.get('jpeg_quality', 0) <= 100, "Quality out of range"
            for key in expected_defaults:
                print(f"   {key}: {data.get(key)} ✓")
        else:
            print(f"   Source: Defaults (no config file)")
            for key, expected_value in expected_defaults.items():
                actual_value = data.get(key)
                print(f"   {key}: {actual_value} {'✓' if actual_value == expected_value else '✗'}")
                assert actual_value == expected_value, \
                    f"{key}: expected {expected_value}, got {actual_value}"


class TestQualityValidation:
    """Test JPEG quality validation"""

    def test_quality_range_validation(self, client, temp_webui_settings):
        """Test quality must be 50-100"""
        # Invalid: too low
        response = client.post('/api/config/webui', json={'jpeg_quality': 49})
        assert response.status_code == 400, "Should reject quality < 50"
        print(f"\n✓ Rejected quality=49 (too low)")

        # Invalid: too high
        response = client.post('/api/config/webui', json={'jpeg_quality': 101})
        assert response.status_code == 400, "Should reject quality > 100"
        print(f"✓ Rejected quality=101 (too high)")

        # Valid: boundary values
        for quality in [50, 100]:
            response = client.post('/api/config/webui', json={'jpeg_quality': quality})
            assert response.status_code == 200, \
                f"Should accept quality={quality}"
            print(f"✓ Accepted quality={quality}")

    def test_quality_recommended_range(self, client, temp_webui_settings):
        """Test recommended quality values (70-95)"""
        recommended_values = [70, 80, 85, 90, 95]

        print(f"\n📊 Testing recommended quality values:")
        for quality in recommended_values:
            response = client.post('/api/config/webui', json={'jpeg_quality': quality})
            assert response.status_code == 200, \
                f"Should accept quality={quality}"
            print(f"   Q={quality}: ✓")


class TestResolutionValidation:
    """Test resolution validation"""

    def test_resolution_range_validation(self, client, temp_webui_settings):
        """Test resolution must be within valid ranges"""
        # Invalid: width too low
        response = client.post('/api/config/webui', json={
            'stream_width': 319,
            'stream_height': 768
        })
        assert response.status_code == 400, "Should reject width < 320"

        # Invalid: height too high
        response = client.post('/api/config/webui', json={
            'stream_width': 1024,
            'stream_height': 1081
        })
        assert response.status_code == 400, "Should reject height > 1080"

        # Valid: common resolutions
        valid_resolutions = [
            (640, 480),
            (1024, 768),
            (1920, 1080)
        ]

        print(f"\n📐 Testing valid resolutions:")
        for width, height in valid_resolutions:
            response = client.post('/api/config/webui', json={
                'stream_width': width,
                'stream_height': height
            })
            assert response.status_code == 200, \
                f"Should accept {width}x{height}"
            print(f"   {width}x{height}: ✓")


class TestFrameRateValidation:
    """Test frame rate validation"""

    def test_frame_rate_range_validation(self, client, temp_webui_settings):
        """Test frame rate must be 1-30 FPS"""
        # Invalid: too low
        response = client.post('/api/config/webui', json={'frame_rate': 0})
        assert response.status_code == 400, "Should reject FPS < 1"

        # Invalid: too high
        response = client.post('/api/config/webui', json={'frame_rate': 31})
        assert response.status_code == 400, "Should reject FPS > 30"

        # Valid: common frame rates
        valid_fps = [1, 5, 10, 15, 24, 30]

        print(f"\n🎬 Testing valid frame rates:")
        for fps in valid_fps:
            response = client.post('/api/config/webui', json={'frame_rate': fps})
            assert response.status_code == 200, \
                f"Should accept {fps} FPS"
            print(f"   {fps} FPS: ✓")


class TestSettingsPersistence:
    """Test settings are saved and loaded correctly"""

    def test_settings_update_and_retrieve(self, client, temp_webui_settings):
        """Test settings can be updated and retrieved"""
        test_settings = {
            'stream_width': 1280,
            'stream_height': 720,
            'frame_rate': 15,
            'jpeg_quality': 90
        }

        # Update settings
        response = client.post('/api/config/webui', json=test_settings)
        assert response.status_code == 200

        # Retrieve settings
        response = client.get('/api/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        # Verify all settings match
        print(f"\n💾 Settings persistence test:")
        for key, expected_value in test_settings.items():
            actual_value = data.get(key)
            print(f"   {key}: {actual_value} {'✓' if actual_value == expected_value else '✗'}")
            assert actual_value == expected_value, \
                f"{key}: expected {expected_value}, got {actual_value}"


class TestStreamModeValidation:
    """Test stream mode validation (Phase 1.3)"""

    def test_stream_mode_default(self, client, temp_webui_settings):
        """Verify stream_mode defaults to simplejpeg"""
        response = client.get('/api/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        # Should have stream_mode in defaults
        assert 'stream_mode' in data, "stream_mode should be in default settings"
        assert data['stream_mode'] == 'simplejpeg', \
            f"Expected stream_mode='simplejpeg', got '{data['stream_mode']}'"
        print(f"\n✓ Default stream_mode: {data['stream_mode']}")

    def test_stream_mode_validation(self, client, temp_webui_settings):
        """Test stream_mode must be valid option"""
        # Invalid mode
        response = client.post('/api/config/webui', json={'stream_mode': 'invalid_mode'})
        assert response.status_code == 400, "Should reject invalid stream_mode"
        print(f"\n✓ Rejected invalid stream_mode")

        # Invalid mode with typo
        response = client.post('/api/config/webui', json={'stream_mode': 'simple_jpeg'})
        assert response.status_code == 400, "Should reject typo in stream_mode"
        print(f"✓ Rejected typo in stream_mode")

        # Valid modes
        valid_modes = ['simplejpeg', 'mjpeg_hardware']
        print(f"\n📹 Testing valid stream modes:")
        for mode in valid_modes:
            response = client.post('/api/config/webui', json={
                'stream_mode': mode,
                'jpeg_quality': 85  # Include other required fields
            })
            assert response.status_code == 200, \
                f"Should accept stream_mode='{mode}'"
            print(f"   {mode}: ✓")

    def test_stream_mode_persistence(self, client, temp_webui_settings):
        """Test stream_mode is saved and loaded correctly"""
        from mothbox_paths import WEBUI_SETTINGS_FILE

        # Get current mode first
        response = client.get('/api/config/webui')
        assert response.status_code == 200, "GET config failed"
        original_mode = response.get_json().get('stream_mode', 'simplejpeg')

        # Set to a different mode
        new_mode = 'mjpeg_hardware' if original_mode == 'simplejpeg' else 'simplejpeg'
        response = client.post('/api/config/webui', json={
            'stream_mode': new_mode,
            'jpeg_quality': 85
        })
        assert response.status_code == 200, f"POST config failed: {response.get_json()}"

        # Verify it was written to file - file MUST exist after POST
        assert WEBUI_SETTINGS_FILE.exists(), \
            f"Config file must exist after saving settings: {WEBUI_SETTINGS_FILE}"

        with open(WEBUI_SETTINGS_FILE, 'r') as f:
            content = f.read()
            assert f'stream_mode={new_mode}' in content, \
                f"stream_mode should be in config file. Got:\n{content}"
        print(f"\n💾 Stream mode written to file: {new_mode} ✓")

        # Verify it reads back correctly
        response = client.get('/api/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        assert data['stream_mode'] == new_mode, \
            f"Expected {new_mode}, got {data['stream_mode']}"
        print(f"💾 Stream mode persists: {data['stream_mode']} ✓")

        # Set back to original
        response = client.post('/api/config/webui', json={
            'stream_mode': original_mode,
            'jpeg_quality': 85
        })
        assert response.status_code == 200

        # Verify change
        response = client.get('/api/config/webui')
        data = response.get_json()
        assert data['stream_mode'] == original_mode
        print(f"💾 Stream mode updated: {data['stream_mode']} ✓")

    def test_stream_mode_optional_in_update(self, client, temp_webui_settings):
        """Test stream_mode is optional when updating other settings"""
        # Update only quality, not stream_mode
        response = client.post('/api/config/webui', json={'jpeg_quality': 90})
        assert response.status_code == 200, \
            "Should allow updating without stream_mode"
        print(f"\n✓ Can update settings without specifying stream_mode")
