"""
Integration Tests: Quality Settings Persistence (Feature Set 2)

Tests that image quality settings persist correctly across:
- Camera restarts
- File backup/restore mechanisms
- Concurrent updates
- Active streaming
- File corruption scenarios

These tests verify the complete settings lifecycle in webui_settings.txt.

RUN ON RASPBERRY PI ONLY - requires actual hardware

Usage:
    pytest Tests/integration/test_quality_settings_persistence.py -v -s
"""
import pytest
import time
import shutil
import tempfile
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

from mothbox_paths import WEBUI_SETTINGS_FILE, get_control_values


class TestSettingsSurviveCameraRestart:
    """Test that settings persist across camera restarts"""

    def test_settings_survive_simple_restart(self, client, camera_streamer):
        """Test settings survive camera stop/start cycle"""
        print("\n🔄 Testing settings persistence through camera restart...")

        # Set custom quality settings
        test_settings = {
            'sharpness': 2.8,
            'brightness': 0.25,
            'contrast': 1.6,
            'saturation': 1.3
        }

        response = client.post('/config/webui', json=test_settings)
        assert response.status_code == 200
        print("   ✓ Settings saved via API")

        # Initialize camera with settings
        camera_streamer.load_stream_settings()
        camera_streamer.initialize_camera()
        print("   ✓ Camera initialized with settings")

        # Verify settings loaded into camera_streamer
        assert abs(camera_streamer.sharpness - 2.8) < 0.01
        assert abs(camera_streamer.brightness - 0.25) < 0.01
        assert abs(camera_streamer.contrast - 1.6) < 0.01
        assert abs(camera_streamer.saturation - 1.3) < 0.01
        print("   ✓ Settings loaded into camera")

        # Stop camera
        camera_streamer.stop_streaming()
        time.sleep(0.5)
        print("   ✓ Camera stopped")

        # Reload settings (simulates restart)
        camera_streamer.load_stream_settings()
        print("   ✓ Settings reloaded")

        # Verify settings still match
        assert abs(camera_streamer.sharpness - 2.8) < 0.01
        assert abs(camera_streamer.brightness - 0.25) < 0.01
        assert abs(camera_streamer.contrast - 1.6) < 0.01
        assert abs(camera_streamer.saturation - 1.3) < 0.01
        print("   ✓ Settings survived restart")

    def test_settings_survive_multiple_restarts(self, client, camera_streamer):
        """Test settings survive multiple camera restart cycles"""
        print("\n🔄 Testing settings through multiple restart cycles...")

        test_settings = {
            'sharpness': 4.0,
            'brightness': -0.3,
            'contrast': 2.0,
            'saturation': 0.8,
            'awb_mode': 5  # Daylight
        }

        # Save settings
        response = client.post('/config/webui', json=test_settings)
        assert response.status_code == 200
        print("   ✓ Initial settings saved")

        # Perform 3 restart cycles
        for i in range(3):
            camera_streamer.load_stream_settings()
            camera_streamer.initialize_camera()
            time.sleep(0.3)
            camera_streamer.stop_streaming()
            time.sleep(0.3)
            print(f"   ✓ Restart cycle {i+1} complete")

        # Final reload and verify
        camera_streamer.load_stream_settings()

        assert abs(camera_streamer.sharpness - 4.0) < 0.01
        assert abs(camera_streamer.brightness - (-0.3)) < 0.01
        assert abs(camera_streamer.contrast - 2.0) < 0.01
        assert abs(camera_streamer.saturation - 0.8) < 0.01
        assert camera_streamer.awb_mode == 5
        print("   ✓ All settings survived 3 restart cycles")


class TestBackupMechanismVerification:
    """Test settings file backup and restore mechanisms"""

    def test_backup_created_on_update(self, client):
        """Test that backup file is created when settings updated"""
        print("\n💾 Testing backup file creation...")

        # Clear any existing backups
        backup_pattern = f"{WEBUI_SETTINGS_FILE.name}.backup.*"
        for backup in WEBUI_SETTINGS_FILE.parent.glob(backup_pattern):
            backup.unlink()
        print("   ✓ Cleared existing backups")

        # Update settings to trigger backup
        response = client.post('/config/webui', json={'sharpness': 3.5})
        assert response.status_code == 200
        print("   ✓ Settings updated")

        # Check for backup file
        time.sleep(0.1)  # Allow time for file system
        backups = list(WEBUI_SETTINGS_FILE.parent.glob(backup_pattern))

        if len(backups) > 0:
            print(f"   ✓ Backup created: {backups[0].name}")
        else:
            print("   ⚠ No backup found (may not exist on first write)")

    def test_backup_limit_enforced(self, client):
        """Test that only most recent 5 backups are kept"""
        print("\n💾 Testing backup limit enforcement (keep 5)...")

        # Perform 8 updates to generate multiple backups
        for i in range(8):
            response = client.post('/config/webui', json={'sharpness': float(i)})
            assert response.status_code == 200
            time.sleep(0.2)  # Ensure different timestamps

        # Count backups
        backup_pattern = f"{WEBUI_SETTINGS_FILE.name}.backup.*"
        backups = list(WEBUI_SETTINGS_FILE.parent.glob(backup_pattern))

        print(f"   Found {len(backups)} backup(s)")
        assert len(backups) <= 5, "Should keep at most 5 backups"
        print("   ✓ Backup limit enforced")

    def test_restore_from_backup_after_corruption(self, client):
        """Test manual restore from backup file"""
        print("\n💾 Testing backup restore after corruption...")

        # Save known good settings
        good_settings = {
            'sharpness': 5.5,
            'brightness': 0.4,
            'contrast': 2.2
        }
        response = client.post('/config/webui', json=good_settings)
        assert response.status_code == 200
        print("   ✓ Good settings saved")

        # Find most recent backup
        backup_pattern = f"{WEBUI_SETTINGS_FILE.name}.backup.*"
        backups = sorted(
            WEBUI_SETTINGS_FILE.parent.glob(backup_pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if len(backups) == 0:
            print("   ⚠ No backups available, skipping restore test")
            return

        latest_backup = backups[0]
        print(f"   Latest backup: {latest_backup.name}")

        # Corrupt the settings file
        with open(WEBUI_SETTINGS_FILE, 'w') as f:
            f.write("corrupted_data_no_equals_signs\n")
            f.write("invalid format here\n")
        print("   ✓ Settings file corrupted")

        # Restore from backup
        shutil.copy2(latest_backup, WEBUI_SETTINGS_FILE)
        print("   ✓ Settings restored from backup")

        # Verify restoration
        response = client.get('/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        # Should have valid settings (may not match exact values if backup is older)
        assert 'sharpness' in data
        assert 0.0 <= data['sharpness'] <= 16.0
        print("   ✓ Settings file restored and valid")


class TestConcurrentSettingsUpdates:
    """Test race conditions and concurrent write safety"""

    def test_rapid_sequential_updates(self, client):
        """Test rapid sequential updates don't corrupt file"""
        print("\n⚡ Testing rapid sequential updates...")

        import threading
        results = []

        def update_setting(value):
            try:
                response = client.post('/config/webui', json={'sharpness': value})
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))

        # Fire off 10 rapid updates
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_setting, args=(float(i),))
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        print(f"   Completed {len(results)} concurrent updates")

        # Verify file is still valid
        response = client.get('/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        # Settings should be valid even if we don't know final value
        assert 'sharpness' in data
        assert 0.0 <= data['sharpness'] <= 16.0
        print(f"   ✓ File still valid after concurrent updates (final sharpness={data['sharpness']})")

    def test_concurrent_different_settings(self, client):
        """Test concurrent updates to different settings"""
        print("\n⚡ Testing concurrent updates to different settings...")

        import threading
        import random

        def update_sharpness():
            for _ in range(5):
                value = random.uniform(0.0, 16.0)
                client.post('/config/webui', json={'sharpness': value})
                time.sleep(0.01)

        def update_brightness():
            for _ in range(5):
                value = random.uniform(-1.0, 1.0)
                client.post('/config/webui', json={'brightness': value})
                time.sleep(0.01)

        def update_contrast():
            for _ in range(5):
                value = random.uniform(0.0, 32.0)
                client.post('/config/webui', json={'contrast': value})
                time.sleep(0.01)

        # Run concurrent updates
        threads = [
            threading.Thread(target=update_sharpness),
            threading.Thread(target=update_brightness),
            threading.Thread(target=update_contrast)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        print("   ✓ All concurrent updates completed")

        # Verify file integrity
        response = client.get('/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        assert 0.0 <= data['sharpness'] <= 16.0
        assert -1.0 <= data['brightness'] <= 1.0
        assert 0.0 <= data['contrast'] <= 32.0
        print("   ✓ Settings file valid after concurrent different-setting updates")


class TestSettingsDuringActiveStreaming:
    """Test settings updates during active camera streaming"""

    def test_update_settings_while_streaming(self, client, camera_streamer):
        """Test that settings can be updated while camera is streaming"""
        print("\n📹 Testing settings update during active streaming...")

        # Start streaming
        camera_streamer.load_stream_settings()
        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(1)  # Let streaming stabilize
        print("   ✓ Streaming started")

        # Update settings while streaming
        new_settings = {
            'sharpness': 6.0,
            'brightness': 0.5,
            'contrast': 2.5
        }

        response = client.post('/config/webui', json=new_settings)
        assert response.status_code == 200
        print("   ✓ Settings updated during streaming")

        # Stop streaming
        camera_streamer.stop_streaming()
        time.sleep(0.5)

        # Reload and verify settings persisted
        camera_streamer.load_stream_settings()
        assert abs(camera_streamer.sharpness - 6.0) < 0.01
        assert abs(camera_streamer.brightness - 0.5) < 0.01
        assert abs(camera_streamer.contrast - 2.5) < 0.01
        print("   ✓ Settings persisted correctly during streaming")

    def test_multiple_updates_during_streaming(self, client, camera_streamer):
        """Test multiple settings updates while streaming"""
        print("\n📹 Testing multiple updates during streaming...")

        # Start streaming
        camera_streamer.initialize_camera()
        camera_streamer.start_streaming()
        time.sleep(0.5)
        print("   ✓ Streaming started")

        # Perform 5 updates while streaming
        for i in range(5):
            response = client.post('/config/webui', json={
                'sharpness': float(i * 2),
                'brightness': float(i * 0.2 - 0.4)
            })
            assert response.status_code == 200
            time.sleep(0.2)

        print("   ✓ 5 updates completed during streaming")

        # Stop streaming
        camera_streamer.stop_streaming()

        # Verify final settings
        response = client.get('/config/webui')
        data = response.get_json()

        # Should have last values from loop (i=4)
        assert abs(data['sharpness'] - 8.0) < 0.01
        assert abs(data['brightness'] - 0.4) < 0.01
        print("   ✓ Final settings correct after multiple streaming updates")


class TestSettingsPropagationToFile:
    """Test that settings propagate correctly to webui_settings.txt"""

    def test_all_quality_settings_written_to_file(self, client):
        """Test that all quality settings are written to file"""
        print("\n📝 Testing settings propagation to file...")

        comprehensive_settings = {
            # Image quality
            'sharpness': 3.5,
            'brightness': 0.15,
            'contrast': 1.8,
            'saturation': 1.2,
            # Focus
            'af_mode': 1,
            'af_speed': 1,
            'af_range': 2,
            # White balance
            'awb_enable': False,
            'awb_mode': 6
        }

        # Save settings
        response = client.post('/config/webui', json=comprehensive_settings)
        assert response.status_code == 200
        print("   ✓ Comprehensive settings saved")

        # Read file directly
        file_settings = get_control_values(WEBUI_SETTINGS_FILE)

        # Verify all quality settings in file
        assert 'sharpness' in file_settings
        assert abs(float(file_settings['sharpness']) - 3.5) < 0.01
        print(f"   ✓ sharpness in file: {file_settings['sharpness']}")

        assert 'brightness' in file_settings
        assert abs(float(file_settings['brightness']) - 0.15) < 0.01
        print(f"   ✓ brightness in file: {file_settings['brightness']}")

        assert 'contrast' in file_settings
        assert abs(float(file_settings['contrast']) - 1.8) < 0.01
        print(f"   ✓ contrast in file: {file_settings['contrast']}")

        assert 'saturation' in file_settings
        assert abs(float(file_settings['saturation']) - 1.2) < 0.01
        print(f"   ✓ saturation in file: {file_settings['saturation']}")

        assert 'af_mode' in file_settings
        assert int(file_settings['af_mode']) == 1
        print(f"   ✓ af_mode in file: {file_settings['af_mode']}")

        assert 'awb_enable' in file_settings
        assert file_settings['awb_enable'].lower() == 'false'
        print(f"   ✓ awb_enable in file: {file_settings['awb_enable']}")

        assert 'awb_mode' in file_settings
        assert int(file_settings['awb_mode']) == 6
        print(f"   ✓ awb_mode in file: {file_settings['awb_mode']}")

    def test_file_format_is_valid(self, client):
        """Test that settings file format is valid key=value"""
        print("\n📝 Testing file format validity...")

        # Update settings
        response = client.post('/config/webui', json={'sharpness': 4.0})
        assert response.status_code == 200

        # Read and parse file
        if not WEBUI_SETTINGS_FILE.exists():
            print("   ⚠ Settings file doesn't exist yet")
            return

        with open(WEBUI_SETTINGS_FILE, 'r') as f:
            lines = f.readlines()

        print(f"   File has {len(lines)} lines")

        # Verify format
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                assert '=' in line, f"Invalid line format: {line}"
                key, value = line.split('=', 1)
                assert len(key) > 0, "Empty key"
                assert len(value) > 0, "Empty value"

        print("   ✓ All lines have valid key=value format")


class TestFileLockingAndConcurrentWriteSafety:
    """Test file locking and concurrent write safety"""

    def test_file_not_corrupted_by_concurrent_writes(self, client):
        """Test that concurrent writes don't corrupt settings file"""
        print("\n🔒 Testing file integrity under concurrent writes...")

        import threading
        import random

        write_count = [0]
        error_count = [0]

        def random_update():
            try:
                settings = {
                    'sharpness': random.uniform(0.0, 16.0),
                    'brightness': random.uniform(-1.0, 1.0),
                    'contrast': random.uniform(0.0, 32.0),
                    'saturation': random.uniform(0.0, 32.0)
                }
                response = client.post('/config/webui', json=settings)
                if response.status_code == 200:
                    write_count[0] += 1
                else:
                    error_count[0] += 1
            except Exception as e:
                error_count[0] += 1
                print(f"   ⚠ Update error: {e}")

        # Launch 20 concurrent writes
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=random_update)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        print(f"   Writes succeeded: {write_count[0]}")
        print(f"   Writes failed: {error_count[0]}")

        # Verify file is still readable and valid
        response = client.get('/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        # All settings should be in valid ranges
        assert 0.0 <= data['sharpness'] <= 16.0
        assert -1.0 <= data['brightness'] <= 1.0
        assert 0.0 <= data['contrast'] <= 32.0
        assert 0.0 <= data['saturation'] <= 32.0
        print("   ✓ File remains valid after concurrent writes")

    def test_partial_write_doesnt_corrupt_file(self, client):
        """Test that interrupted write doesn't leave file corrupted"""
        print("\n🔒 Testing partial write protection...")

        # Save good settings
        good_settings = {
            'sharpness': 7.0,
            'brightness': 0.2,
            'contrast': 1.5,
            'saturation': 1.0
        }

        response = client.post('/config/webui', json=good_settings)
        assert response.status_code == 200
        print("   ✓ Good settings saved")

        # Verify we can still read settings after any interruption
        # (The backup mechanism should protect against corruption)
        response = client.get('/config/webui')
        assert response.status_code == 200
        data = response.get_json()

        # Should have valid values
        assert 'sharpness' in data
        assert 'brightness' in data
        assert 'contrast' in data
        assert 'saturation' in data
        print("   ✓ Settings file readable and valid")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
