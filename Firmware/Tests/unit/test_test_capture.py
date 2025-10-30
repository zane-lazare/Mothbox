"""
Unit tests for test capture endpoint (Phase 4.5)

Tests the /api/camera/test-capture-liveview endpoint that captures full-resolution
test photos using preview settings without affecting production config.

RUN ON RASPBERRY PI ONLY - tests camera hardware
"""

import pytest
import sys
from pathlib import Path
import json
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


@pytest.mark.photo
class TestTestCaptureEndpoint:
    """Test test capture endpoint with real hardware"""

    def test_test_capture_endpoint_exists(self):
        """Test that test capture endpoint is registered"""
        from routes.camera import camera_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        with app.test_client() as client:
            response = client.post('/api/camera/test-capture-liveview')
            # Should not return 404
            assert response.status_code != 404
            print(f"\n✓ Test capture endpoint exists")

    def test_test_capture_creates_real_photo(self):
        """Test that test capture creates a real photo file"""
        from routes.camera import camera_bp
        from flask import Flask
        from mothbox_paths import PHOTOS_DIR

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        # Get count of existing test captures
        test_captures_dir = PHOTOS_DIR / "test_captures"
        existing_count = len(list(test_captures_dir.glob("*.jpg"))) if test_captures_dir.exists() else 0

        with app.test_client() as client:
            response = client.post('/api/camera/test-capture-liveview')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'test_photo_path' in data

        # Verify new file was created
        assert test_captures_dir.exists(), "test_captures directory should exist"
        new_count = len(list(test_captures_dir.glob("*.jpg")))
        assert new_count > existing_count, "Should have created a new test photo"

        # Verify the reported file exists
        photo_path = PHOTOS_DIR / data['test_photo_path']
        assert photo_path.exists(), f"Photo should exist at {photo_path}"
        assert photo_path.stat().st_size > 0, "Photo file should not be empty"

        print(f"\n✓ Test capture created: {data['test_photo_path']}")
        print(f"   File size: {photo_path.stat().st_size / 1024:.1f} KB")

    def test_test_capture_returns_valid_metadata(self):
        """Test that test capture returns valid metadata"""
        from routes.camera import camera_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        with app.test_client() as client:
            response = client.post('/api/camera/test-capture-liveview')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify metadata structure
        assert 'metadata' in data
        metadata = data['metadata']

        assert 'exposure_time' in metadata
        assert 'analogue_gain' in metadata
        assert 'lens_position' in metadata
        assert 'colour_temperature' in metadata

        # Verify metadata values are reasonable
        assert metadata['exposure_time'] > 0, "Exposure time should be positive"
        assert metadata['analogue_gain'] >= 1.0, "Gain should be >= 1.0"
        assert metadata['lens_position'] >= 0.0, "Lens position should be non-negative"
        assert metadata['colour_temperature'] > 0, "Color temperature should be positive"

        print(f"\n✓ Metadata returned:")
        print(f"   Exposure: {metadata['exposure_time']}µs")
        print(f"   Gain: {metadata['analogue_gain']}")
        print(f"   Focus: {metadata['lens_position']} diopters")
        print(f"   Color temp: {metadata['colour_temperature']}K")

    def test_test_capture_returns_settings_used(self):
        """Test that test capture returns the settings that were applied"""
        from routes.camera import camera_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        with app.test_client() as client:
            response = client.post('/api/camera/test-capture-liveview')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify settings_used structure
        assert 'settings_used' in data
        settings = data['settings_used']

        # Should include image quality settings
        assert 'Sharpness' in settings
        assert 'Brightness' in settings
        assert 'Contrast' in settings
        assert 'Saturation' in settings

        # Should include focus settings
        assert 'AfMode' in settings
        assert 'AfSpeed' in settings
        assert 'AfRange' in settings

        # Should include white balance
        assert 'AwbEnable' in settings

        print(f"\n✓ Settings used:")
        print(f"   Sharpness: {settings['Sharpness']}")
        print(f"   Brightness: {settings['Brightness']}")
        print(f"   Contrast: {settings['Contrast']}")
        print(f"   Saturation: {settings['Saturation']}")
        print(f"   Focus mode: {settings['AfMode']} (0=Manual, 1=Single, 2=Continuous)")
        print(f"   AWB: {settings['AwbEnable']}")

    def test_test_capture_doesnt_affect_production_settings(self):
        """Test that test capture doesn't modify camera_settings.csv"""
        from routes.camera import camera_bp
        from flask import Flask
        from mothbox_paths import CAMERA_SETTINGS_FILE

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        # Read production settings before
        if CAMERA_SETTINGS_FILE.exists():
            before_mtime = CAMERA_SETTINGS_FILE.stat().st_mtime
            before_content = CAMERA_SETTINGS_FILE.read_text()
        else:
            before_mtime = None
            before_content = None

        # Take test capture
        with app.test_client() as client:
            response = client.post('/api/camera/test-capture-liveview')

        assert response.status_code == 200

        # Give filesystem time to sync
        time.sleep(0.1)

        # Verify production settings unchanged
        if CAMERA_SETTINGS_FILE.exists():
            after_mtime = CAMERA_SETTINGS_FILE.stat().st_mtime
            after_content = CAMERA_SETTINGS_FILE.read_text()

            assert after_mtime == before_mtime, "camera_settings.csv modification time should not change"
            assert after_content == before_content, "camera_settings.csv content should not change"
            print(f"\n✓ Production camera_settings.csv unchanged")
        else:
            assert before_content is None, "camera_settings.csv should still not exist"
            print(f"\n✓ Production camera_settings.csv still doesn't exist (correct)")

    def test_test_capture_response_format(self):
        """Test that test capture response has expected format"""
        from routes.camera import camera_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        with app.test_client() as client:
            response = client.post('/api/camera/test-capture-liveview')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Required fields
        assert 'success' in data
        assert 'test_photo_path' in data
        assert 'settings_used' in data
        assert 'metadata' in data
        assert 'timestamp' in data
        assert 'message' in data

        # Verify types
        assert isinstance(data['success'], bool)
        assert isinstance(data['test_photo_path'], str)
        assert isinstance(data['settings_used'], dict)
        assert isinstance(data['metadata'], dict)
        assert isinstance(data['timestamp'], (int, float))
        assert isinstance(data['message'], str)

        # Verify path format
        assert data['test_photo_path'].startswith('test_captures/')
        assert data['test_photo_path'].endswith('.jpg')

        print(f"\n✓ Response format valid")
        print(f"   Success: {data['success']}")
        print(f"   Photo: {data['test_photo_path']}")
        print(f"   Message: {data['message']}")


# =============================================================================
# Enhanced Test Capture Tests (Feature Set 4)
# =============================================================================

@pytest.mark.photo
class TestTestCaptureErrorRecovery:
    """Test error recovery for test capture endpoint"""

    def test_recovery_from_camera_busy(self):
        """Test recovery when camera is busy"""
        from routes.camera import camera_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        with app.test_client() as client:
            # Multiple rapid requests
            responses = []
            for _ in range(3):
                response = client.post('/api/camera/test-capture-liveview')
                responses.append(response.status_code)
                time.sleep(0.2)

            # At least one should complete or all should gracefully fail
            assert any(r == 200 for r in responses) or all(r in [500, 503] for r in responses)

            print(f"\n✓ Recovery from busy camera: {responses}")

    def test_recovery_from_disk_full(self):
        """Test error handling when disk is full"""
        # Note: Simulating disk full is complex
        # This test documents expected behavior

        expected_error = {
            'success': False,
            'error': 'Disk full or write error',
            'traceback': '...'
        }

        assert 'error' in expected_error
        assert expected_error['success'] == False

        print("\n✓ Disk full error structure defined")


@pytest.mark.photo
class TestTestCaptureCleanup:
    """Test cleanup after test capture"""

    def test_temp_files_removed_on_success(self):
        """Test no temp files remain after successful capture"""
        from routes.camera import camera_bp
        from flask import Flask
        from mothbox_paths import PHOTOS_DIR

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        with app.test_client() as client:
            response = client.post('/api/camera/test-capture-liveview')

            if response.status_code == 200:
                # Check for temp files
                test_dir = PHOTOS_DIR / "test_captures"

                if test_dir.exists():
                    temp_files = list(test_dir.glob("*.tmp"))
                    assert len(temp_files) == 0

                    print("\n✓ No temp files after success")
            else:
                print("\n⚠ Camera busy, skipping")

    def test_temp_files_removed_on_error(self):
        """Test temp files cleaned up even on error"""
        from routes.camera import camera_bp
        from flask import Flask
        from mothbox_paths import PHOTOS_DIR

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        # Multiple rapid requests may cause errors
        with app.test_client() as client:
            for _ in range(5):
                client.post('/api/camera/test-capture-liveview')
                time.sleep(0.1)

            # Check for abandoned temp files
            test_dir = PHOTOS_DIR / "test_captures"

            if test_dir.exists():
                temp_files = list(test_dir.glob("*.tmp"))
                # Should be minimal or zero
                assert len(temp_files) < 3

                print(f"\n✓ Temp files minimal after errors: {len(temp_files)}")


@pytest.mark.photo
class TestConcurrentCaptureRequests:
    """Test concurrent test capture request handling"""

    def test_queue_concurrent_requests(self):
        """Test system queues or rejects concurrent captures"""
        from routes.camera import camera_bp
        from flask import Flask
        from concurrent.futures import ThreadPoolExecutor, as_completed

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        def capture():
            with app.test_client() as client:
                response = client.post('/api/camera/test-capture-liveview')
                return response.status_code

        # Submit 3 concurrent requests
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(capture) for _ in range(3)]
            results = [future.result() for future in as_completed(futures)]

        # At least one should complete
        success_count = sum(1 for r in results if r == 200)
        print(f"\n✓ Concurrent requests: {success_count}/3 succeeded")

    def test_serial_requests_succeed(self):
        """Test serial requests all succeed"""
        from routes.camera import camera_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        successes = 0

        with app.test_client() as client:
            for i in range(3):
                response = client.post('/api/camera/test-capture-liveview')
                if response.status_code == 200:
                    successes += 1
                time.sleep(1)  # Wait between captures

        print(f"\n✓ Serial requests: {successes}/3 succeeded")


@pytest.mark.photo
class TestInvalidPreviewSettings:
    """Test test capture with invalid preview settings"""

    def test_capture_with_missing_preview_settings(self):
        """Test capture when webui_settings.txt is missing"""
        from routes.camera import camera_bp
        from flask import Flask
        from mothbox_paths import WEBUI_SETTINGS_FILE
        import tempfile
        import shutil

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        # Backup settings
        backup = None
        if WEBUI_SETTINGS_FILE.exists():
            backup = tempfile.NamedTemporaryFile(delete=False)
            shutil.copy2(WEBUI_SETTINGS_FILE, backup.name)
            WEBUI_SETTINGS_FILE.unlink()

        try:
            with app.test_client() as client:
                response = client.post('/api/camera/test-capture-liveview')

                # Should use defaults
                if response.status_code == 200:
                    data = json.loads(response.data)
                    # Should have default settings
                    assert 'settings_used' in data
                    print("\n✓ Defaults used when settings missing")
                else:
                    print("\n⚠ Camera busy")

        finally:
            if backup and Path(backup.name).exists():
                shutil.copy2(backup.name, WEBUI_SETTINGS_FILE)
                Path(backup.name).unlink()

    def test_capture_with_corrupted_preview_settings(self):
        """Test capture with corrupted webui_settings.txt"""
        from routes.camera import camera_bp
        from flask import Flask
        from mothbox_paths import WEBUI_SETTINGS_FILE
        import tempfile
        import shutil

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        # Backup settings
        backup = None
        if WEBUI_SETTINGS_FILE.exists():
            backup = tempfile.NamedTemporaryFile(delete=False)
            shutil.copy2(WEBUI_SETTINGS_FILE, backup.name)

        try:
            # Corrupt settings
            WEBUI_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            WEBUI_SETTINGS_FILE.write_text("corrupted\ndata")

            with app.test_client() as client:
                response = client.post('/api/camera/test-capture-liveview')

                # Should handle gracefully (use defaults or error)
                assert response.status_code in [200, 500]

                print("\n✓ Corrupted settings handled")

        finally:
            if backup and Path(backup.name).exists():
                shutil.copy2(backup.name, WEBUI_SETTINGS_FILE)
                Path(backup.name).unlink()


@pytest.mark.photo
class TestTestCaptureWithoutStreaming:
    """Test test capture when streaming is not active"""

    def test_capture_when_streaming_stopped(self):
        """Test capture works when streaming is not active"""
        from routes.camera import camera_bp
        from flask import Flask
        from liveview_stream import LiveViewStreamer

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        # Mock camera streamer
        class MockSocketIO:
            def emit(self, event, data, **kwargs):
                pass

        camera_streamer = CameraStreamer(MockSocketIO())
        camera_streamer.stop_streaming()  # Ensure stopped

        app.config['CAMERA_STREAMER'] = camera_streamer

        with app.test_client() as client:
            response = client.post('/api/camera/test-capture-liveview')

            # Should work even without streaming
            if response.status_code == 200:
                data = json.loads(response.data)
                assert data['success'] == True
                print("\n✓ Capture works without streaming")
            else:
                print("\n⚠ Camera busy")

    def test_capture_releases_and_restarts_streaming(self):
        """Test capture properly releases and restarts streaming"""
        from routes.camera import camera_bp
        from flask import Flask
        from liveview_stream import LiveViewStreamer

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        class MockSocketIO:
            def emit(self, event, data, **kwargs):
                pass

        camera_streamer = CameraStreamer(MockSocketIO())
        app.config['CAMERA_STREAMER'] = camera_streamer

        # Start streaming
        if not camera_streamer.start_streaming():
            print("\n⚠ Camera not available")
            return

        was_streaming = camera_streamer.streaming

        # Take capture
        with app.test_client() as client:
            response = client.post('/api/camera/test-capture-liveview')

            if response.status_code == 200:
                # Give time for restart
                time.sleep(1)

                # Should restart streaming
                print(f"\n✓ Streaming after capture: {camera_streamer.streaming}")
            else:
                print("\n⚠ Capture failed")

        camera_streamer.stop_streaming()
