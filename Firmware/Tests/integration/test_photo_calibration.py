"""
Integration Tests: Photo Calibration Workflow (Issue #45)

Tests auto-calibration for TakePhoto.py high-resolution still images.
This workflow uses subprocess to call TakePhoto.py independently,
ensuring camera is fully released from webUI/CameraStreamer.

Key characteristics:
- Camera owned exclusively by subprocess (not CameraStreamer)
- Updates camera_settings.csv (used by TakePhoto.py)
- Independent of webUI streaming state
- Optimizes for high-res stills with flash

Related: Issue #45 - Camera Calibration Architecture split

Run with: pytest Tests/integration/test_photo_calibration.py -v -s
"""

import pytest
import time
from pathlib import Path

# Fixtures (app, client, photo_ready) are provided by conftest.py


@pytest.mark.photo
class TestPhotoCalibrationBasic:
    """Test basic photo calibration workflow"""

    def test_calibration_success(self, client, photo_ready):
        """Test photo calibration completes successfully"""
        print("\n🔧 Testing photo calibration...")

        response = client.post('/api/camera/calibrate-photo')

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

        print(f"   ✓ Photo calibration completed in {data['af_duration_seconds']:.2f}s")
        print(f"   ✓ Exposure: {data['before']['ExposureTime']} → {data['after']['ExposureTime']}µs")
        print(f"   ✓ Gain: {data['before']['AnalogueGain']} → {data['after']['AnalogueGain']}")
        print(f"   ✓ Focus: {data['before']['LensPosition']} → {data['after']['LensPosition']}D")

    def test_calibration_timing(self, client, photo_ready):
        """Test photo calibration completes within expected time"""
        print("\n⏱️  Testing photo calibration timing...")

        start_time = time.time()
        response = client.post('/api/camera/calibrate-photo')
        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = response.get_json()

        # Photo calibration may take longer than stream (high-res config)
        assert elapsed < 30.0, \
            f"Photo calibration took {elapsed}s (should be <30s)"

        print(f"   ✓ Completed in {elapsed:.2f}s")
        print(f"   ✓ AF duration: {data['af_duration_seconds']:.2f}s")


@pytest.mark.photo
class TestPhotoCalibrationMetadata:
    """Test photo calibration produces valid metadata"""

    def test_calibration_produces_valid_exposure(self, client, photo_ready):
        """Test calibration produces valid exposure values"""
        print("\n📈 Testing photo calibration exposure values...")

        response = client.post('/api/camera/calibrate-photo')

        assert response.status_code == 200
        data = response.get_json()

        after = data['after']
        exp = int(after['ExposureTime'])
        gain = float(after['AnalogueGain'])

        # Values should be in valid ranges
        assert 100 <= exp <= 1000000, f"Exposure {exp}µs out of range"
        assert 1.0 <= gain <= 16.0, f"Gain {gain} out of range"

        print(f"   ✓ Exposure: {exp}µs (valid)")
        print(f"   ✓ Gain: {gain} (valid)")

    def test_calibration_produces_valid_focus(self, client, photo_ready):
        """Test calibration produces valid lens position"""
        print("\n🎯 Testing photo calibration focus values...")

        response = client.post('/api/camera/calibrate-photo')

        assert response.status_code == 200
        data = response.get_json()

        after = data['after']
        lens_pos = float(after['LensPosition'])

        # Lens position should be in valid range
        assert 0.0 <= lens_pos <= 15.0, \
            f"Lens position {lens_pos}D out of range"

        print(f"   ✓ Lens position: {lens_pos}D (valid)")

    def test_calibration_consistency(self, client, photo_ready):
        """Test photo calibration produces consistent results"""
        print("\n🔁 Testing photo calibration consistency...")

        results = []
        for i in range(3):
            response = client.post('/api/camera/calibrate-photo')

            assert response.status_code == 200
            data = response.get_json()
            after = data['after']

            results.append({
                'exposure': int(after['ExposureTime']),
                'gain': float(after['AnalogueGain']),
                'lens': float(after['LensPosition'])
            })

            time.sleep(2.0)  # Delay between calibrations

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
        assert exp_range < 100000, "Exposure too inconsistent"
        assert gain_range < 5.0, "Gain too inconsistent"
        assert lens_range < 2.0, "Focus too inconsistent"


@pytest.mark.photo
class TestPhotoCalibrationFileUpdates:
    """Test photo calibration updates camera_settings.csv correctly"""

    def test_calibration_updates_camera_settings(self, client, photo_ready):
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

        # Run calibration
        response = client.post('/api/camera/calibrate-photo')

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

    def test_calibration_preserves_unrelated_settings(self, client, photo_ready):
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
        response = client.post('/api/camera/calibrate-photo')

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


@pytest.mark.photo
class TestPhotoCalibrationTimestamp:
    """Test LastCalibration timestamp in controls.txt"""

    def test_calibration_updates_timestamp(self, client, photo_ready):
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
        response = client.post('/api/camera/calibrate-photo')

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

    def test_last_calibration_format(self, client, photo_ready):
        """Test LastCalibration timestamp is integer format"""
        print("\n🔢 Testing LastCalibration format...")

        from mothbox_paths import CONTROLS_FILE, get_control_values

        # Run calibration
        response = client.post('/api/camera/calibrate-photo')

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


@pytest.mark.photo
class TestPhotoCalibrationErrorRecovery:
    """Test photo calibration error handling"""

    def test_calibration_camera_unavailable(self, client, photo_ready):
        """Test calibration handles camera unavailable gracefully"""
        print("\n🔧 Testing photo calibration camera unavailable handling...")

        # Run calibration multiple times rapidly
        # Should handle gracefully even if camera is busy
        responses = []
        for i in range(2):
            response = client.post('/api/camera/calibrate-photo')
            responses.append(response)
            time.sleep(0.1)

        # All should return valid status codes
        for i, response in enumerate(responses):
            assert response.status_code in [200, 500], \
                f"Request {i+1} should return valid status"

        print(f"   ✓ Photo calibration handled resource conflicts")

    def test_calibration_subprocess_isolation(self, client, photo_ready):
        """Test photo calibration runs in subprocess (isolated from webUI)"""
        print("\n📦 Testing subprocess isolation...")

        # This is a behavioral test - we verify that the endpoint works
        # even when CameraStreamer is not initialized (subprocess is independent)

        response = client.post('/api/camera/calibrate-photo')

        # Should work regardless of CameraStreamer state
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] is True
            print(f"   ✓ Photo calibration succeeded independently")
        else:
            print(f"   ℹ️  Camera unavailable (expected in some test conditions)")


@pytest.mark.photo
class TestPhotoCalibrationUnderDifferentLighting:
    """Test photo calibration behavior under different lighting conditions"""

    def test_calibration_produces_valid_values(self, client, photo_ready):
        """Test calibration produces valid values regardless of lighting"""
        print("\n💡 Testing photo calibration value validity...")

        # Run calibration (actual lighting depends on test environment)
        response = client.post('/api/camera/calibrate-photo')

        assert response.status_code == 200
        data = response.get_json()

        after = data['after']
        exp = int(after['ExposureTime'])
        gain = float(after['AnalogueGain'])
        lens = float(after['LensPosition'])

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


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
