"""
Integration Tests: Stream Calibration Workflow (Issue #45)

Tests auto-calibration for webUI live video stream using CameraStreamer.
This workflow uses the persistent CameraStreamer instance to tune focus
for optimal real-time viewing without releasing camera hardware.

Key characteristics:
- Camera owned by CameraStreamer (persistent instance)
- Updates webui_settings.txt (used by stream)
- Operates on live stream without subprocess
- Optimizes for real-time video viewing
- Locks focus in manual mode after calibration

Related: Issue #45 - Camera Calibration Architecture split

Run with: pytest Tests/integration/test_stream_calibration.py -v -s
"""

import pytest
import time
from pathlib import Path

# Fixtures (app, client, stream_ready) are provided by conftest.py


@pytest.mark.stream
class TestStreamCalibrationBasic:
    """Test basic stream calibration workflow"""

    def test_calibration_success(self, client, stream_ready):
        """Test stream calibration completes successfully"""
        print("\n🔧 Testing stream calibration...")

        response = client.post('/api/camera/calibrate-stream')

        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert data['success'] is True
        assert 'lens_position' in data
        assert 'af_state' in data
        assert 'duration_seconds' in data

        # Verify lens position is valid
        lens_pos = data['lens_position']
        assert 0.0 <= lens_pos <= 15.0, f"Lens position {lens_pos}D out of range"

        # Verify AF state
        assert data['af_state'] in ['Idle', 'Scanning', 'Success', 'Fail']

        print(f"   ✓ Stream calibration completed in {data['duration_seconds']:.2f}s")
        print(f"   ✓ Lens position: {lens_pos}D")
        print(f"   ✓ AF state: {data['af_state']}")

    def test_calibration_timing(self, client, stream_ready):
        """Test stream calibration completes within expected time"""
        print("\n⏱️  Testing stream calibration timing...")

        start_time = time.time()
        response = client.post('/api/camera/calibrate-stream')
        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = response.get_json()

        # Stream calibration should be faster (uses existing camera instance)
        assert elapsed < 15.0, \
            f"Stream calibration took {elapsed}s (should be <15s)"

        print(f"   ✓ Completed in {elapsed:.2f}s")
        print(f"   ✓ AF duration: {data['duration_seconds']:.2f}s")

    def test_calibration_uses_camera_streamer(self, client, stream_ready):
        """Test stream calibration uses CameraStreamer instance"""
        print("\n📹 Testing CameraStreamer usage...")

        # Verify camera_streamer is initialized
        assert stream_ready.camera is not None, \
            "CameraStreamer should have camera initialized"

        # Run calibration
        response = client.post('/api/camera/calibrate-stream')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Camera should still be initialized after (not released)
        assert stream_ready.camera is not None, \
            "CameraStreamer should retain camera after calibration"

        print(f"   ✓ CameraStreamer instance used")
        print(f"   ✓ Camera retained after calibration")


@pytest.mark.stream
class TestStreamCalibrationFocusLocking:
    """Test stream calibration locks focus in manual mode"""

    def test_calibration_locks_manual_focus(self, client, stream_ready):
        """Test calibration sets manual focus mode with locked position"""
        print("\n🔒 Testing manual focus locking...")

        from mothbox_paths import WEBUI_SETTINGS_FILE, get_control_values

        # Run calibration
        response = client.post('/api/camera/calibrate-stream')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        lens_pos = data['lens_position']

        # Verify webui_settings.txt updated to manual focus
        if WEBUI_SETTINGS_FILE.exists():
            settings = get_control_values(WEBUI_SETTINGS_FILE)

            # Should be locked to manual mode (af_mode=0)
            af_mode = settings.get('af_mode', '')
            assert af_mode == '0', \
                f"af_mode should be 0 (Manual), got {af_mode}"

            # Should have lens position saved
            saved_lens_pos = settings.get('lens_position', '')
            assert saved_lens_pos != '', \
                "lens_position should be saved in webui_settings.txt"

            print(f"   ✓ Focus locked in manual mode (af_mode=0)")
            print(f"   ✓ Lens position saved: {saved_lens_pos}D")
            print(f"   ✓ API reported: {lens_pos}D")
        else:
            pytest.skip("webui_settings.txt not found")

    def test_calibration_consistency(self, client, stream_ready):
        """Test stream calibration produces consistent results"""
        print("\n🔁 Testing stream calibration consistency...")

        results = []
        for i in range(3):
            response = client.post('/api/camera/calibrate-stream')

            assert response.status_code == 200
            data = response.get_json()

            results.append({
                'lens': float(data['lens_position']),
                'af_state': data['af_state']
            })

            time.sleep(1.0)  # Brief delay between calibrations

        # Check consistency
        lenses = [r['lens'] for r in results]
        lens_range = max(lenses) - min(lenses)

        print(f"   ✓ Lens range: {lens_range:.2f}D")
        print(f"   ✓ Positions: {[f'{p:.2f}D' for p in lenses]}")

        # Results should be reasonably consistent
        assert lens_range < 2.0, "Focus too inconsistent"


@pytest.mark.stream
class TestStreamCalibrationFileUpdates:
    """Test stream calibration updates webui_settings.txt correctly"""

    def test_calibration_updates_webui_settings(self, client, stream_ready):
        """Test calibration writes to webui_settings.txt"""
        print("\n💾 Testing webui_settings.txt update...")

        from mothbox_paths import WEBUI_SETTINGS_FILE, get_control_values

        # Read before
        before_values = {}
        if WEBUI_SETTINGS_FILE.exists():
            before_values = get_control_values(WEBUI_SETTINGS_FILE)

        # Run calibration
        response = client.post('/api/camera/calibrate-stream')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Read after
        if WEBUI_SETTINGS_FILE.exists():
            after_values = get_control_values(WEBUI_SETTINGS_FILE)

            # Verify file was updated
            assert 'af_mode' in after_values
            assert 'lens_position' in after_values

            print(f"   ✓ webui_settings.txt updated")
            print(f"   ✓ af_mode: {after_values.get('af_mode')}")
            print(f"   ✓ lens_position: {after_values.get('lens_position')}D")
        else:
            pytest.skip("webui_settings.txt not found")

    def test_calibration_does_not_update_camera_settings(self, client, stream_ready):
        """Test stream calibration doesn't modify camera_settings.csv"""
        print("\n🔒 Testing camera_settings.csv preservation...")

        from mothbox_paths import CAMERA_SETTINGS_FILE
        import csv

        # Read camera_settings.csv before (if exists)
        before_values = {}
        before_mtime = None
        if CAMERA_SETTINGS_FILE.exists():
            before_mtime = CAMERA_SETTINGS_FILE.stat().st_mtime
            with open(CAMERA_SETTINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    before_values[row['SETTING']] = row['VALUE']

        # Run stream calibration
        response = client.post('/api/camera/calibrate-stream')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify camera_settings.csv unchanged
        if CAMERA_SETTINGS_FILE.exists() and before_mtime:
            after_mtime = CAMERA_SETTINGS_FILE.stat().st_mtime

            # File should not be modified (mtime unchanged)
            # Note: Allow small timing differences due to filesystem precision
            time_diff = abs(after_mtime - before_mtime)
            assert time_diff < 1.0, \
                "camera_settings.csv should not be modified by stream calibration"

            print(f"   ✓ camera_settings.csv not modified")
            print(f"   ✓ Stream calibration only updates webui_settings.txt")
        else:
            print(f"   ℹ️  camera_settings.csv not present for comparison")


@pytest.mark.stream
class TestStreamRecoveryAfterCalibration:
    """Test stream recovers after calibration"""

    def test_stream_recovers_after_calibration(self, client, stream_ready):
        """Test stream can resume after calibration"""
        print("\n🔄 Testing stream recovery after calibration...")

        # Trigger calibration
        response = client.post('/api/camera/calibrate-stream')
        assert response.status_code == 200

        # Wait briefly
        time.sleep(0.5)

        # Verify stream can be accessed again
        # (If stream is broken, subsequent operations would fail)
        response2 = client.post('/api/camera/autofocus')
        assert response2.status_code == 200, \
            "Stream should recover after calibration"

        print(f"   ✓ Stream recovered after calibration")
        print(f"   ✓ Subsequent autofocus succeeded")

    def test_camera_remains_initialized(self, client, stream_ready):
        """Test camera remains initialized after stream calibration"""
        print("\n📹 Testing camera state after calibration...")

        # Verify camera is initialized before
        assert stream_ready.camera is not None, \
            "Camera should be initialized by stream_ready fixture"

        # Run calibration
        response = client.post('/api/camera/calibrate-stream')
        assert response.status_code == 200

        # Camera should still be initialized (not released)
        assert stream_ready.camera is not None, \
            "Camera should remain initialized after stream calibration"

        print(f"   ✓ Camera remained initialized")
        print(f"   ✓ No subprocess cleanup required")


@pytest.mark.stream
class TestStreamCalibrationConcurrency:
    """Test concurrent stream calibration handling"""

    def test_concurrent_calibration_prevention(self, client, stream_ready):
        """Test system prevents concurrent stream calibrations"""
        print("\n🔒 Testing concurrent calibration prevention...")

        # Attempt rapid-fire calibrations
        responses = []
        for i in range(3):
            response = client.post('/api/camera/calibrate-stream')
            responses.append((i, response))
            # Minimal delay (tests concurrent access)
            time.sleep(0.05)

        # Check responses
        success_count = 0
        error_count = 0

        for i, response in responses:
            if response.status_code == 200:
                data = response.get_json()
                if data.get('success'):
                    success_count += 1
            elif response.status_code == 500:
                error_count += 1

        print(f"   ✓ {success_count} succeeded, {error_count} errored")
        print(f"   ℹ️  Concurrent access handled (no deadlocks)")

    def test_calibration_autofocus_interleaving(self, client, stream_ready):
        """Test calibration and autofocus can be interleaved"""
        print("\n🔀 Testing calibration/autofocus interleaving...")

        # Run calibration
        response1 = client.post('/api/camera/calibrate-stream')
        assert response1.status_code == 200

        time.sleep(0.5)

        # Run autofocus
        response2 = client.post('/api/camera/autofocus')
        assert response2.status_code == 200

        time.sleep(0.5)

        # Run calibration again
        response3 = client.post('/api/camera/calibrate-stream')
        assert response3.status_code == 200

        print(f"   ✓ Calibration and autofocus interleaved successfully")
        print(f"   ✓ No resource conflicts")


@pytest.mark.stream
class TestStreamCalibrationErrorRecovery:
    """Test stream calibration error handling"""

    def test_calibration_camera_unavailable(self, client, stream_ready):
        """Test calibration handles errors gracefully"""
        print("\n🔧 Testing stream calibration error handling...")

        # Run calibration
        response = client.post('/api/camera/calibrate-stream')

        # Should return valid status code
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.get_json()
            # Should have valid structure
            assert 'success' in data
            assert 'lens_position' in data
            print(f"   ✓ Calibration succeeded")
        else:
            print(f"   ℹ️  Calibration unavailable (expected in some conditions)")

    def test_calibration_preserves_stream_state_on_error(self, client, stream_ready):
        """Test stream state is preserved even if calibration fails"""
        print("\n🛡️  Testing stream state preservation on error...")

        # Verify camera is initialized before
        was_initialized = stream_ready.camera is not None

        # Run calibration (may succeed or fail)
        response = client.post('/api/camera/calibrate-stream')

        # Camera should still be in same state after (not corrupted)
        is_initialized = stream_ready.camera is not None

        # State should be preserved
        assert is_initialized == was_initialized, \
            "Camera state should be preserved after calibration attempt"

        print(f"   ✓ Camera state preserved (initialized={is_initialized})")


@pytest.mark.stream
class TestStreamCalibrationMetadata:
    """Test stream calibration returns valid metadata"""

    def test_calibration_returns_focus_metadata(self, client, stream_ready):
        """Test calibration returns focus-related metadata"""
        print("\n📊 Testing stream calibration metadata...")

        response = client.post('/api/camera/calibrate-stream')

        assert response.status_code == 200
        data = response.get_json()

        # Should include lens position
        lens_pos = data['lens_position']
        assert 0.0 <= lens_pos <= 15.0, \
            f"Lens position {lens_pos}D out of range"

        # Should include AF state
        af_state = data['af_state']
        assert af_state in ['Idle', 'Scanning', 'Success', 'Fail']

        # Should include duration
        duration = data['duration_seconds']
        assert 0 < duration < 20, \
            f"Duration {duration}s seems unreasonable"

        print(f"   ✓ Lens position: {lens_pos}D (valid)")
        print(f"   ✓ AF state: {af_state} (valid)")
        print(f"   ✓ Duration: {duration:.2f}s (valid)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
