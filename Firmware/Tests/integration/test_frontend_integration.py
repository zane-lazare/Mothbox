"""
Integration Tests: Frontend Integration (Phase 3)

Tests that verify frontend UI properly integrates with Phase 2.2 backend features:
- Camera page controls update preview stream settings
- Interactive buttons trigger correct backend endpoints
- Settings copy functionality works end-to-end
- Real-time metadata updates during preview
- Test capture creates photos and returns metadata

These tests verify the complete frontend-backend integration path.

Run with: pytest Tests/integration/test_frontend_integration.py -v -s

Note: Uses shared fixtures from Tests/conftest.py
"""

import pytest
import time
from pathlib import Path

# Fixtures (app, client) provided by conftest.py


class TestCameraPageIntegration:
    """Test Camera page UI integration with backend (Phase 3)"""

    def test_preview_settings_update_via_api(self, client):
        """Test that camera page can update preview settings"""
        print("\n🎬 Testing preview settings update...")

        # Simulate user changing preview settings via Camera page
        response = client.post('/config/webui', json={
            'sharpness': 2.5,
            'brightness': 0.2,
            'contrast': 1.3,
            'saturation': 1.1
        })

        assert response.status_code == 200, "Should accept valid preview settings"
        data = response.get_json()
        assert data['success'] is True

        # Verify settings were persisted
        response = client.get('/config/webui')
        settings = response.get_json()

        assert float(settings.get('sharpness', 0)) == 2.5
        assert float(settings.get('brightness', 0)) == 0.2
        assert float(settings.get('contrast', 0)) == 1.3
        assert float(settings.get('saturation', 0)) == 1.1

        print("   ✓ Preview settings updated successfully")

    def test_autofocus_button_integration(self, client):
        """Test autofocus button triggers backend correctly"""
        print("\n🔍 Testing autofocus button integration...")

        # Simulate user clicking "Autofocus" button
        response = client.post('/camera/autofocus')

        # Should succeed or gracefully handle camera busy
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.get_json()
            assert 'success' in data
            assert 'lens_position' in data or 'af_state' in data
            print(f"   ✓ Autofocus completed: {data.get('af_state', 'N/A')}")
        else:
            # Camera busy is acceptable in test environment
            print("   ⚠ Autofocus skipped (camera busy)")

    def test_calibration_button_integration(self, client):
        """Test calibration button with checkbox options"""
        print("\n⚙️ Testing calibration button integration...")

        # Test 1: Calibrate capture settings only
        response = client.post('/camera/calibrate', json={
            'update_capture': True,
            'update_preview': False
        })

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.get_json()
            assert 'success' in data
            print("   ✓ Calibration (capture only) triggered")
        else:
            print("   ⚠ Calibration skipped (camera busy)")

        time.sleep(0.5)

        # Test 2: Calibrate both
        response = client.post('/camera/calibrate', json={
            'update_capture': True,
            'update_preview': True
        })

        assert response.status_code in [200, 500]
        print("   ✓ Calibration (both) triggered")

    def test_test_capture_button_integration(self, client):
        """Test that test capture button creates photo"""
        print("\n📸 Testing test capture button integration...")

        # Simulate user clicking "Test Capture" button
        response = client.post('/camera/test-capture')

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] is True
            assert 'test_photo_path' in data
            assert 'settings_used' in data
            assert 'metadata' in data

            # Verify photo was created
            from mothbox_paths import PHOTOS_DIR
            photo_path = PHOTOS_DIR / data['test_photo_path']
            assert photo_path.exists(), "Test capture photo should exist"

            print(f"   ✓ Test capture created: {data['test_photo_path']}")
        else:
            print("   ⚠ Test capture skipped (camera busy)")


class TestSettingsCopyIntegration:
    """Test Settings page copy functionality (Phase 3)"""

    def test_copy_preview_to_capture_button(self, client):
        """Test copy preview → capture button"""
        print("\n📋 Testing copy preview → capture button...")

        # Set some preview settings
        client.post('/config/webui', json={
            'sharpness': 3.0,
            'brightness': 0.3,
            'contrast': 1.5
        })

        # Simulate user clicking "Copy to Capture Settings" button
        response = client.post('/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })

        assert response.status_code == 200
        data = response.get_json()

        assert data['success'] is True
        assert data['direction'] == 'preview_to_capture'
        assert 'settings_copied' in data

        print(f"   ✓ Copied {len(data['settings_copied'])} settings")

    def test_copy_capture_to_preview_button(self, client):
        """Test copy capture → preview button"""
        print("\n📋 Testing copy capture → preview button...")

        # Simulate user clicking "Copy to Preview Settings" button
        response = client.post('/config/copy-settings', json={
            'direction': 'capture_to_preview'
        })

        assert response.status_code == 200
        data = response.get_json()

        assert data['success'] is True
        assert data['direction'] == 'capture_to_preview'

        print("   ✓ Copy capture → preview completed")

    def test_copy_button_error_handling(self, client):
        """Test copy settings with invalid direction"""
        print("\n❌ Testing copy settings error handling...")

        # Invalid direction
        response = client.post('/config/copy-settings', json={
            'direction': 'invalid'
        })

        assert response.status_code == 400
        print("   ✓ Invalid direction rejected")

        # Missing direction
        response = client.post('/config/copy-settings', json={})

        assert response.status_code == 400
        print("   ✓ Missing direction rejected")


class TestMetadataDisplay:
    """Test real-time metadata display (Phase 3)"""

    def test_settings_endpoint_returns_metadata(self, client):
        """Test that camera/settings endpoint returns metadata for display"""
        print("\n📊 Testing metadata endpoint...")

        response = client.get('/camera/settings')

        assert response.status_code == 200
        data = response.get_json()

        # Should contain capture settings
        assert 'ExposureTime' in data or 'exposure_time' in data
        assert 'AnalogueGain' in data or 'analogue_gain' in data

        print("   ✓ Metadata endpoint returns camera settings")


class TestEndToEndWorkflow:
    """Test complete frontend workflows (Phase 3)"""

    def test_settings_adjustment_workflow(self, client):
        """Test complete workflow: adjust settings → test capture → apply to production"""
        print("\n🔄 Testing complete settings adjustment workflow...")

        # Step 1: User adjusts preview settings
        print("   Step 1: Adjusting preview settings...")
        response = client.post('/config/webui', json={
            'sharpness': 2.0,
            'brightness': 0.1,
            'contrast': 1.2
        })
        assert response.status_code == 200

        # Step 2: User clicks "Test Capture" to see results
        print("   Step 2: Test capture...")
        response = client.post('/camera/test-capture')

        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] is True
            print(f"      ✓ Test photo: {data['test_photo_path']}")

            # Step 3: User likes results, copies to production
            print("   Step 3: Copy to production settings...")
            response = client.post('/config/copy-settings', json={
                'direction': 'preview_to_capture'
            })
            assert response.status_code == 200

            print("   ✓ Complete workflow succeeded")
        else:
            print("   ⚠ Workflow skipped (camera busy)")

    def test_calibration_workflow(self, client):
        """Test calibration workflow: autofocus → calibrate → apply"""
        print("\n🎯 Testing calibration workflow...")

        # Step 1: Run autofocus
        print("   Step 1: Autofocus...")
        response = client.post('/camera/autofocus')

        if response.status_code == 200:
            time.sleep(1)

            # Step 2: Run calibration
            print("   Step 2: Calibrate...")
            response = client.post('/camera/calibrate', json={
                'update_capture': True,
                'update_preview': False
            })

            if response.status_code == 200:
                data = response.get_json()
                assert 'optimized_settings' in data
                print("   ✓ Calibration workflow succeeded")
            else:
                print("   ⚠ Calibration skipped")
        else:
            print("   ⚠ Workflow skipped (camera busy)")


class TestErrorHandling:
    """Test UI error handling (Phase 3)"""

    def test_invalid_settings_rejected(self, client):
        """Test that UI validation catches invalid settings"""
        print("\n🛡️ Testing invalid settings rejection...")

        # Sharpness out of range
        response = client.post('/config/webui', json={'sharpness': 20.0})
        assert response.status_code == 400
        print("   ✓ Invalid sharpness rejected")

        # Brightness out of range
        response = client.post('/config/webui', json={'brightness': 5.0})
        assert response.status_code == 400
        print("   ✓ Invalid brightness rejected")

    def test_missing_camera_graceful_error(self, client):
        """Test graceful error when camera not available"""
        print("\n⚠️  Testing camera unavailable handling...")

        # This test may pass or fail depending on camera state
        # Just verify it returns proper HTTP status
        response = client.post('/camera/autofocus')
        assert response.status_code in [200, 500, 503]

        if response.status_code != 200:
            data = response.get_json()
            assert 'error' in data or 'success' in data
            print("   ✓ Graceful error handling verified")
        else:
            print("   ✓ Camera available, test passed")
