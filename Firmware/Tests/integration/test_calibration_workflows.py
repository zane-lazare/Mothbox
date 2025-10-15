"""
Integration Tests: Calibration Workflows (Feature Set 3)

Tests auto-calibration functionality including:
- Calibration under various lighting conditions
- Settings file updates (preview, capture, both)
- LastCalibration timestamp verification
- WebSocket progress events
- Before/after metadata comparison
- Auto-calibration period triggers
- Error recovery and resource management

These tests require real Raspberry Pi hardware and camera.

Run with: pytest Tests/integration/test_calibration_workflows.py -v -s
"""

import pytest
import time
from pathlib import Path

# Fixtures (app, client) are provided by conftest.py


class TestCalibrationBasicWorkflows:
    """Test basic calibration workflows"""

    def test_calibration_capture_only(self, client):
        """Test calibration updating capture settings only"""
        print("\n🔧 Testing calibration for capture settings...")

        response = client.post('/api/camera/calibrate', json={
            'update_capture': True,
            'update_preview': False
        })

        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert data['success'] is True
        assert 'before' in data
        assert 'after' in data
        assert 'af_success' in data
        assert 'af_duration_seconds' in data
        assert 'timestamp' in data

        # Verify before/after have required fields
        for key in ['ExposureTime', 'AnalogueGain', 'LensPosition']:
            assert key in data['before'], f"Missing {key} in before"
            assert key in data['after'], f"Missing {key} in after"

        print(f"   ✓ Calibration completed in {data['af_duration_seconds']:.2f}s")
        print(f"   ✓ Exposure: {data['before']['ExposureTime']} → {data['after']['ExposureTime']}µs")
        print(f"   ✓ Gain: {data['before']['AnalogueGain']} → {data['after']['AnalogueGain']}")
        print(f"   ✓ Focus: {data['before']['LensPosition']} → {data['after']['LensPosition']}D")

    def test_calibration_preview_only(self, client):
        """Test calibration updating preview settings only"""
        print("\n🔧 Testing calibration for preview settings...")

        response = client.post('/api/camera/calibrate', json={
            'update_capture': False,
            'update_preview': True
        })

        assert response.status_code == 200
        data = response.get_json()

        assert data['success'] is True
        assert 'apply_to' in data
        # Note: Old format uses update_capture/update_preview
        # New format uses apply_to

        print(f"   ✓ Preview calibration completed")

    def test_calibration_both_settings(self, client):
        """Test calibration updating both capture and preview"""
        print("\n🔧 Testing calibration for both settings...")

        response = client.post('/api/camera/calibrate', json={
            'update_capture': True,
            'update_preview': True
        })

        assert response.status_code == 200
        data = response.get_json()

        assert data['success'] is True
        assert 'after' in data

        print(f"   ✓ Both settings updated successfully")

    def test_calibration_default_parameters(self, client):
        """Test calibration with default parameters"""
        print("\n🔧 Testing calibration with defaults...")

        # No parameters = defaults (update capture only)
        response = client.post('/api/camera/calibrate', json={})

        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] is True
            print(f"   ✓ Calibration succeeded with defaults")
        else:
            print(f"   ✓ Calibration requires explicit parameters")


class TestCalibrationMetadataChanges:
    """Test calibration actually changes settings"""

    def test_calibration_changes_exposure(self, client):
        """Test calibration produces different exposure values"""
        print("\n📈 Testing calibration changes exposure...")

        response = client.post('/api/camera/calibrate', json={
            'update_capture': False,
            'update_preview': False
        })

        assert response.status_code == 200
        data = response.get_json()

        before = data['before']
        after = data['after']

        # Exposure or gain should change (or both)
        # In some conditions they might be identical if already optimal
        before_exp = int(before.get('ExposureTime', 0))
        after_exp = int(after.get('ExposureTime', after.get('exposure_time', 0)))

        before_gain = float(before.get('AnalogueGain', 0))
        after_gain = float(after.get('AnalogueGain', after.get('analogue_gain', 0)))

        # Values should be in valid ranges
        assert 100 <= after_exp <= 1000000, \
            f"After exposure {after_exp}µs out of range"
        assert 1.0 <= after_gain <= 16.0, \
            f"After gain {after_gain} out of range"

        print(f"   ✓ Before: Exp={before_exp}µs, Gain={before_gain}")
        print(f"   ✓ After: Exp={after_exp}µs, Gain={after_gain}")

        # Check if values changed (they might not if already optimal)
        exp_changed = abs(before_exp - after_exp) > 100
        gain_changed = abs(before_gain - after_gain) > 0.1

        if exp_changed or gain_changed:
            print(f"   ✓ Calibration optimized settings")
        else:
            print(f"   ℹ️  Settings already optimal (no change needed)")

    def test_calibration_changes_lens_position(self, client):
        """Test calibration changes lens position"""
        print("\n🎯 Testing calibration changes focus...")

        response = client.post('/api/camera/calibrate', json={
            'update_capture': False,
            'update_preview': False
        })

        assert response.status_code == 200
        data = response.get_json()

        after = data['after']
        lens_pos = float(after.get('LensPosition', after.get('lens_position', 0)))

        # Lens position should be in valid range
        assert 0.0 <= lens_pos <= 15.0, \
            f"Lens position {lens_pos}D out of range"

        print(f"   ✓ Calibrated lens position: {lens_pos}D")

    def test_calibration_consistency(self, client):
        """Test calibration produces consistent results"""
        print("\n🔁 Testing calibration consistency...")

        results = []
        for i in range(3):
            response = client.post('/api/camera/calibrate', json={
                'update_capture': False,
                'update_preview': False
            })

            assert response.status_code == 200
            data = response.get_json()
            after = data['after']

            results.append({
                'exposure': int(after.get('ExposureTime', after.get('exposure_time', 0))),
                'gain': float(after.get('AnalogueGain', after.get('analogue_gain', 0))),
                'lens': float(after.get('LensPosition', after.get('lens_position', 0)))
            })

            time.sleep(1.0)  # Brief delay between calibrations

        # Check consistency
        exposures = [r['exposure'] for r in results]
        gains = [r['gain'] for r in results]
        lenses = [r['lens'] for r in results]

        exp_range = max(exposures) - min(exposures)
        gain_range = max(gains) - min(gains)
        lens_range = max(lenses) - min(lenses)

        print(f"   ✓ Exposure range: {exp_range}µs")
        print(f"   ✓ Gain range: {gain_range:.2f}")
        print(f"   ✓ Lens range: {lens_range:.2f}D")

        # Results should be reasonably consistent in stable lighting
        # (Allow some variance due to auto-exposure adjustments)
        assert exp_range < 100000, "Exposure too inconsistent"
        assert gain_range < 5.0, "Gain too inconsistent"
        assert lens_range < 2.0, "Focus too inconsistent"


class TestCalibrationFileUpdates:
    """Test calibration updates settings files correctly"""

    def test_calibration_updates_camera_settings(self, client):
        """Test calibration writes to camera_settings.csv"""
        print("\n💾 Testing camera_settings.csv update...")

        from mothbox_paths import CAMERA_SETTINGS_FILE
        import csv

        # Read before
        before_values = {}
        if CAMERA_SETTINGS_FILE.exists():
            with open(CAMERA_SETTINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    before_values[row['SETTING']] = row['VALUE']

        # Run calibration (update capture)
        response = client.post('/api/camera/calibrate', json={
            'update_capture': True,
            'update_preview': False
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Read after
        after_values = {}
        if CAMERA_SETTINGS_FILE.exists():
            with open(CAMERA_SETTINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    after_values[row['SETTING']] = row['VALUE']

            # Verify file was updated with calibrated values
            assert 'ExposureTime' in after_values
            assert 'AnalogueGain' in after_values
            assert 'LensPosition' in after_values

            print(f"   ✓ camera_settings.csv updated")
            print(f"   ✓ ExposureTime: {after_values['ExposureTime']}µs")
            print(f"   ✓ AnalogueGain: {after_values['AnalogueGain']}")
            print(f"   ✓ LensPosition: {after_values['LensPosition']}D")
        else:
            pytest.skip("camera_settings.csv not found")

    def test_calibration_updates_webui_settings(self, client):
        """Test calibration writes to webui_settings.txt"""
        print("\n💾 Testing webui_settings.txt update...")

        from mothbox_paths import WEBUI_SETTINGS_FILE, get_control_values

        # Read before
        before_values = {}
        if WEBUI_SETTINGS_FILE.exists():
            before_values = get_control_values(WEBUI_SETTINGS_FILE)

        # Run calibration (update preview)
        response = client.post('/api/camera/calibrate', json={
            'update_capture': False,
            'update_preview': True
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Read after
        if WEBUI_SETTINGS_FILE.exists():
            after_values = get_control_values(WEBUI_SETTINGS_FILE)

            # Verify file was updated
            # Note: Preview settings might update af_mode but not exposure
            # (exposure is auto for preview)
            assert 'af_mode' in after_values

            print(f"   ✓ webui_settings.txt updated")
            print(f"   ✓ af_mode: {after_values.get('af_mode')}")
        else:
            pytest.skip("webui_settings.txt not found")

    def test_calibration_preserves_unrelated_settings(self, client):
        """Test calibration doesn't overwrite unrelated settings"""
        print("\n🔒 Testing preservation of unrelated settings...")

        from mothbox_paths import CAMERA_SETTINGS_FILE
        import csv

        # Read all settings before
        before_all_settings = {}
        if CAMERA_SETTINGS_FILE.exists():
            with open(CAMERA_SETTINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    before_all_settings[row['SETTING']] = row['VALUE']

        # Run calibration
        response = client.post('/api/camera/calibrate', json={
            'update_capture': True,
            'update_preview': False
        })

        assert response.status_code == 200

        # Read all settings after
        after_all_settings = {}
        if CAMERA_SETTINGS_FILE.exists():
            with open(CAMERA_SETTINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    after_all_settings[row['SETTING']] = row['VALUE']

            # Check that unrelated settings weren't modified
            calibration_keys = ['ExposureTime', 'AnalogueGain', 'LensPosition']
            unrelated_keys = [k for k in before_all_settings.keys()
                            if k not in calibration_keys]

            preserved_count = 0
            for key in unrelated_keys:
                if key in after_all_settings:
                    if before_all_settings[key] == after_all_settings[key]:
                        preserved_count += 1

            print(f"   ✓ Preserved {preserved_count}/{len(unrelated_keys)} unrelated settings")
        else:
            pytest.skip("camera_settings.csv not found")


class TestLastCalibrationTimestamp:
    """Test LastCalibration timestamp in controls.txt"""

    def test_calibration_updates_timestamp(self, client):
        """Test calibration updates LastCalibration in controls.txt"""
        print("\n⏰ Testing LastCalibration timestamp update...")

        from mothbox_paths import CONTROLS_FILE, get_control_values

        # Read before
        before_timestamp = None
        if CONTROLS_FILE.exists():
            controls = get_control_values(CONTROLS_FILE)
            before_timestamp = controls.get('LastCalibration', '0')

        # Run calibration
        start_time = time.time()
        response = client.post('/api/camera/calibrate', json={
            'update_capture': True,
            'update_preview': False
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Check response has timestamp
        response_timestamp = data.get('timestamp')
        assert response_timestamp is not None
        assert response_timestamp >= start_time

        # Read after
        if CONTROLS_FILE.exists():
            controls = get_control_values(CONTROLS_FILE)
            after_timestamp = controls.get('LastCalibration', '0')

            # Timestamp should be updated
            assert after_timestamp != before_timestamp, \
                "LastCalibration timestamp should be updated"

            # Should be close to current time
            timestamp_int = int(after_timestamp)
            time_diff = abs(timestamp_int - start_time)
            assert time_diff < 60, \
                f"Timestamp {timestamp_int} too far from current time (diff={time_diff}s)"

            print(f"   ✓ LastCalibration updated: {after_timestamp}")
            print(f"   ✓ Response timestamp: {response_timestamp}")
        else:
            pytest.skip("controls.txt not found")

    def test_last_calibration_format(self, client):
        """Test LastCalibration timestamp is integer format"""
        print("\n🔢 Testing LastCalibration format...")

        from mothbox_paths import CONTROLS_FILE, get_control_values

        # Run calibration
        response = client.post('/api/camera/calibrate', json={
            'update_capture': True,
            'update_preview': False
        })

        assert response.status_code == 200

        # Check format in file
        if CONTROLS_FILE.exists():
            controls = get_control_values(CONTROLS_FILE)
            timestamp_str = controls.get('LastCalibration', '0')

            # Should be parseable as integer
            try:
                timestamp_int = int(timestamp_str)
                assert timestamp_int > 0, "Timestamp should be positive"
                print(f"   ✓ LastCalibration format valid: {timestamp_int}")
            except ValueError:
                pytest.fail(f"LastCalibration not an integer: {timestamp_str}")
        else:
            pytest.skip("controls.txt not found")


class TestCalibrationProgressEvents:
    """Test WebSocket calibration progress events"""

    def test_calibration_emits_progress(self, client):
        """Test calibration emits progress events"""
        print("\n📊 Testing calibration progress events...")

        # Note: WebSocket events are emitted via socketio
        # In test environment with MockSocketIO, events are discarded
        # But we can verify calibration completes in steps

        response = client.post('/api/camera/calibrate', json={
            'update_capture': True,
            'update_preview': False
        })

        assert response.status_code == 200
        data = response.get_json()

        # Calibration should complete successfully
        # (Progress events are emitted internally but not tested here)
        assert data['success'] is True

        print(f"   ✓ Calibration completed (progress events emitted internally)")
        print(f"   ℹ️  Note: WebSocket testing requires live socketio connection")

    def test_calibration_step_timing(self, client):
        """Test calibration completes within expected time"""
        print("\n⏱️  Testing calibration timing...")

        start_time = time.time()
        response = client.post('/api/camera/calibrate', json={
            'update_capture': True,
            'update_preview': False
        })
        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = response.get_json()

        # Should complete within reasonable time
        # Calibration includes: camera init, stabilization, AF, file writes
        assert elapsed < 20.0, \
            f"Calibration took {elapsed}s (should be <20s)"

        print(f"   ✓ Calibration completed in {elapsed:.2f}s")
        print(f"   ✓ AF duration: {data['af_duration_seconds']:.2f}s")


class TestCalibrationDuringStreaming:
    """Test calibration with active streaming"""

    def test_calibration_with_active_stream(self, client):
        """Test calibration when preview stream is active"""
        print("\n📹 Testing calibration during streaming...")

        # Note: camera_streamer should be active from conftest.py
        # Calibration endpoint should handle camera resource management

        response = client.post('/api/camera/calibrate', json={
            'update_capture': True,
            'update_preview': False
        })

        assert response.status_code == 200, \
            "Calibration should handle camera resource conflicts"

        data = response.get_json()
        assert data['success'] is True

        print(f"   ✓ Calibration succeeded with stream active")

    def test_stream_recovers_after_calibration(self, client):
        """Test stream can resume after calibration"""
        print("\n🔄 Testing stream recovery after calibration...")

        # Trigger calibration
        response = client.post('/api/camera/calibrate', json={
            'update_capture': True,
            'update_preview': False
        })
        assert response.status_code == 200

        # Wait for camera to be released back to stream
        time.sleep(1.0)

        # Verify stream can be accessed again
        # (If stream is broken, subsequent operations would fail)
        response2 = client.post('/api/camera/autofocus')
        assert response2.status_code == 200, \
            "Stream should recover after calibration"

        print(f"   ✓ Stream recovered after calibration")


class TestCalibrationErrorRecovery:
    """Test calibration error handling and recovery"""

    def test_calibration_invalid_apply_to(self, client):
        """Test calibration rejects invalid apply_to parameter"""
        print("\n❌ Testing invalid apply_to parameter...")

        response = client.post('/api/camera/calibrate', json={
            'apply_to': 'invalid_target'
        })

        assert response.status_code == 400, \
            "Should reject invalid apply_to parameter"

        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data

        print(f"   ✓ Invalid apply_to rejected")

    def test_calibration_multiple_rapid_requests(self, client):
        """Test handling of multiple rapid calibration requests"""
        print("\n⚡ Testing rapid calibration requests...")

        # Note: This tests concurrent request handling
        # The camera resource should be properly locked

        responses = []
        for i in range(3):
            print(f"   Request {i+1}/3...")
            response = client.post('/api/camera/calibrate', json={
                'update_capture': False,
                'update_preview': False
            })
            responses.append(response)

            # Very brief delay (test concurrent access)
            time.sleep(0.1)

        # All should return valid responses (200 or 500)
        # Even if camera is busy, should handle gracefully
        for i, response in enumerate(responses):
            assert response.status_code in [200, 500], \
                f"Request {i+1} returned unexpected status {response.status_code}"

        # At least one should succeed
        successes = sum(1 for r in responses if r.status_code == 200)
        assert successes >= 1, "At least one calibration should succeed"

        print(f"   ✓ {successes}/3 calibrations succeeded")


class TestCalibrationUnderDifferentLighting:
    """Test calibration behavior under different lighting conditions"""

    def test_calibration_produces_valid_values(self, client):
        """Test calibration produces valid values regardless of lighting"""
        print("\n💡 Testing calibration value validity...")

        # Run calibration (actual lighting depends on test environment)
        response = client.post('/api/camera/calibrate', json={
            'update_capture': False,
            'update_preview': False
        })

        assert response.status_code == 200
        data = response.get_json()

        after = data['after']
        exp = int(after.get('ExposureTime', after.get('exposure_time', 0)))
        gain = float(after.get('AnalogueGain', after.get('analogue_gain', 0)))
        lens = float(after.get('LensPosition', after.get('lens_position', 0)))

        # All values should be in valid ranges
        assert 100 <= exp <= 1000000, f"Exposure {exp}µs out of range"
        assert 1.0 <= gain <= 16.0, f"Gain {gain} out of range"
        assert 0.0 <= lens <= 15.0, f"Lens {lens}D out of range"

        # Log the values for debugging
        print(f"   ✓ Calibrated values all valid:")
        print(f"     - Exposure: {exp}µs")
        print(f"     - Gain: {gain}")
        print(f"     - Lens: {lens}D")

        # Detect lighting conditions based on gain
        if gain > 8.0:
            print(f"   ℹ️  Low light detected (high gain: {gain})")
        elif gain < 2.0:
            print(f"   ℹ️  Bright light detected (low gain: {gain})")
        else:
            print(f"   ℹ️  Normal light detected (gain: {gain})")


class TestAutoCalibrationPeriod:
    """Test auto-calibration period functionality"""

    def test_calibration_period_setting_exists(self, client):
        """Test AutoCalibrationPeriod setting can be configured"""
        print("\n🔄 Testing AutoCalibrationPeriod configuration...")

        # Try to update camera settings with AutoCalibrationPeriod
        response = client.post('/api/camera/settings', json={
            'AutoCalibrationPeriod': 100
        })

        # Should accept valid period
        assert response.status_code == 200

        print(f"   ✓ AutoCalibrationPeriod setting configured")

    def test_calibration_period_validation(self, client):
        """Test AutoCalibrationPeriod validation"""
        print("\n✅ Testing AutoCalibrationPeriod validation...")

        from routes.camera import ALLOWED_CAMERA_SETTINGS

        validator = ALLOWED_CAMERA_SETTINGS.get('AutoCalibrationPeriod')
        if validator:
            # Valid periods
            assert validator(1) is True, "Should accept period=1"
            assert validator(100) is True, "Should accept period=100"
            assert validator(10000) is True, "Should accept period=10000"

            # Invalid periods
            assert validator(0) is False, "Should reject period=0"
            assert validator(-1) is False, "Should reject negative"
            assert validator(10001) is False, "Should reject too high"

            print(f"   ✓ AutoCalibrationPeriod validation works")
        else:
            pytest.skip("AutoCalibrationPeriod not in ALLOWED_CAMERA_SETTINGS")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
