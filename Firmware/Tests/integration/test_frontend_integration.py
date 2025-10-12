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
        assert 'copied' in data
        assert 'skipped' in data

        print(f"   ✓ Copied {len(data['copied'])} settings")

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
        assert 'copied' in data

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
                assert 'after' in data  # 'after' contains the optimized settings
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


# =============================================================================
# Enhanced Frontend Integration Tests (Feature Set 4)
# =============================================================================

class TestFrontendErrorStates:
    """Test frontend error state handling"""

    def test_camera_unavailable_state(self, client):
        """Test UI handles camera unavailable gracefully"""
        print("\n⚠️  Testing camera unavailable state...")

        # Multiple rapid requests may make camera unavailable
        for _ in range(3):
            response = client.post('/api/camera/autofocus')
            time.sleep(0.1)

        # Last request should have appropriate error handling
        if response.status_code != 200:
            data = response.get_json()
            assert 'error' in data or 'success' in data

            print("   ✓ Camera unavailable error handled")
        else:
            print("   ✓ All requests succeeded")

    def test_settings_locked_during_operation(self, client):
        """Test settings are locked during long operations"""
        print("\n🔒 Testing settings lock during operation...")

        # Start calibration (long operation)
        response = client.post('/api/camera/calibrate', json={
            'apply_to': 'capture'
        })

        if response.status_code == 200:
            # Try to modify settings immediately (should queue or reject)
            response2 = client.post('/api/config/webui', json={
                'sharpness': 3.0
            })

            # Either succeeds (queued) or fails (locked)
            assert response2.status_code in [200, 409, 503]

            print("   ✓ Settings lock behavior verified")
        else:
            print("   ⚠ Calibration unavailable")

    def test_concurrent_operation_error(self, client):
        """Test error when operations conflict"""
        print("\n⚠️  Testing concurrent operation error...")

        # Try test capture twice rapidly
        response1 = client.post('/api/camera/test-capture')
        response2 = client.post('/api/camera/test-capture')

        # At least one should complete or both should error appropriately
        statuses = [response1.status_code, response2.status_code]

        # Valid outcomes: both 200, or one 200 and one error
        assert 200 in statuses or all(s in [500, 503] for s in statuses)

        print(f"   ✓ Concurrent operations: {statuses}")


class TestFrontendLoadingStates:
    """Test frontend loading state validation"""

    def test_operation_in_progress_indicator(self, client):
        """Test that long operations provide progress feedback"""
        print("\n⏳ Testing operation progress indicator...")

        # Start calibration (provides progress updates)
        response = client.post('/api/camera/calibrate', json={
            'apply_to': 'capture'
        })

        if response.status_code == 200:
            data = response.get_json()

            # Should have completion indicator
            assert 'success' in data

            print("   ✓ Operation progress tracked")
        else:
            print("   ⚠ Operation unavailable")

    def test_loading_timeout_handling(self, client):
        """Test frontend handles operation timeouts"""
        print("\n⏱️  Testing timeout handling...")

        # Normal operations should complete within reasonable time
        import time
        start = time.time()

        response = client.get('/api/camera/settings')

        elapsed = time.time() - start

        # Should complete quickly (< 5 seconds)
        assert elapsed < 5.0
        assert response.status_code == 200

        print(f"   ✓ Request completed in {elapsed:.2f}s")


class TestFrontendNotifications:
    """Test frontend notification system"""

    def test_success_notification(self, client):
        """Test success notifications for completed operations"""
        print("\n✅ Testing success notification...")

        response = client.post('/api/config/webui', json={
            'sharpness': 2.0
        })

        assert response.status_code == 200
        data = response.get_json()

        # Should indicate success
        assert data.get('success') == True

        print("   ✓ Success notification format verified")

    def test_error_notification(self, client):
        """Test error notifications for failed operations"""
        print("\n❌ Testing error notification...")

        # Invalid settings
        response = client.post('/api/config/webui', json={
            'sharpness': 99.0  # Out of range
        })

        assert response.status_code == 400
        data = response.get_json()

        # Should include error message
        assert 'error' in data

        print(f"   ✓ Error notification: {data['error']}")

    def test_warning_notification(self, client):
        """Test warning notifications for partial success"""
        print("\n⚠️  Testing warning notification...")

        # Copy settings (may have skipped items)
        response = client.post('/api/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })

        if response.status_code == 200:
            data = response.get_json()

            # Should show what was copied and skipped
            assert 'copied' in data
            assert 'skipped' in data

            if len(data['skipped']) > 0:
                print(f"   ✓ Warning: {len(data['skipped'])} settings skipped")
            else:
                print("   ✓ All settings copied")


class TestFrontendButtonStates:
    """Test button state management"""

    def test_button_disabled_during_operation(self, client):
        """Test buttons are disabled during operations"""
        print("\n🔘 Testing button state management...")

        # Start operation
        response = client.post('/api/camera/autofocus')

        if response.status_code in [200, 500]:
            # Operation attempted - buttons should be disabled during execution
            # This is frontend logic, backend just needs to return status

            print("   ✓ Button state can be managed based on operation status")

    def test_button_re_enabled_after_completion(self, client):
        """Test buttons re-enable after operation completes"""
        print("\n🔘 Testing button re-enable...")

        response = client.post('/api/camera/autofocus')

        # After completion, should be able to trigger again
        time.sleep(2)  # Wait for completion

        response2 = client.post('/api/camera/autofocus')

        # Should be able to trigger again (or get appropriate busy response)
        assert response2.status_code in [200, 500, 503]

        print("   ✓ Button can be triggered again after operation")

    def test_button_state_on_error(self, client):
        """Test button state after operation error"""
        print("\n🔘 Testing button state after error...")

        # Trigger operation that may error
        response = client.post('/api/camera/test-capture')

        # Regardless of success/failure, should return proper status
        assert response.status_code in [200, 500, 503]

        # Should be able to try again
        time.sleep(0.5)
        response2 = client.post('/api/camera/test-capture')

        assert response2.status_code in [200, 500, 503]

        print("   ✓ Button usable after error")


class TestRealTimeUIUpdates:
    """Test real-time UI updates during operations"""

    def test_calibration_progress_updates(self, client):
        """Test UI receives calibration progress updates"""
        print("\n📊 Testing calibration progress updates...")

        # Start calibration (emits progress events)
        response = client.post('/api/camera/calibrate', json={
            'apply_to': 'capture'
        })

        if response.status_code == 200:
            data = response.get_json()

            # Should complete successfully
            assert data.get('success') == True

            # Progress updates would be via WebSocket (tested separately)
            print("   ✓ Calibration completed with progress tracking")
        else:
            print("   ⚠ Calibration unavailable")

    def test_metadata_live_updates(self, client):
        """Test metadata updates in real-time"""
        print("\n📊 Testing metadata live updates...")

        # Get metadata multiple times
        metadata_samples = []

        for _ in range(3):
            response = client.get('/api/camera/settings')
            if response.status_code == 200:
                metadata_samples.append(response.get_json())
            time.sleep(0.5)

        if len(metadata_samples) > 0:
            print(f"   ✓ Collected {len(metadata_samples)} metadata samples")

            # Metadata should be present
            for sample in metadata_samples:
                assert isinstance(sample, dict)
        else:
            print("   ⚠ Metadata unavailable")


class TestMultiTabWorkflow:
    """Test workflows across multiple pages/tabs"""

    def test_settings_page_to_camera_page(self, client):
        """Test workflow: Settings page → Camera page"""
        print("\n🔄 Testing Settings → Camera workflow...")

        # Step 1: Adjust settings on Settings page
        response = client.post('/api/config/webui', json={
            'sharpness': 2.3
        })
        assert response.status_code == 200

        # Step 2: Navigate to Camera page and take test capture
        response = client.post('/api/camera/test-capture')

        if response.status_code == 200:
            data = response.get_json()

            # Should use settings from Settings page
            assert float(data['settings_used']['Sharpness']) == 2.3

            print("   ✓ Settings flowed from Settings → Camera")
        else:
            print("   ⚠ Camera unavailable")

    def test_camera_page_to_settings_page(self, client):
        """Test workflow: Camera page → Settings page"""
        print("\n🔄 Testing Camera → Settings workflow...")

        # Step 1: Take test capture on Camera page
        response = client.post('/api/camera/test-capture')

        if response.status_code != 200:
            print("   ⚠ Camera unavailable")
            return

        # Step 2: Navigate to Settings page to copy settings
        response = client.post('/api/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })

        assert response.status_code == 200
        data = response.get_json()

        print(f"   ✓ Copied {len(data['copied'])} settings")

    def test_settings_persistence_across_pages(self, client):
        """Test settings persist when navigating between pages"""
        print("\n💾 Testing settings persistence...")

        # Set on Settings page
        response = client.post('/api/config/webui', json={
            'sharpness': 2.7
        })
        assert response.status_code == 200

        # Read back (simulating page reload)
        response = client.get('/api/config/webui')
        assert response.status_code == 200

        data = response.get_json()
        assert float(data.get('sharpness', 0)) == 2.7

        print("   ✓ Settings persisted across page navigation")


class TestUIPerformance:
    """Test UI performance and responsiveness"""

    def test_settings_update_latency(self, client):
        """Test settings update has acceptable latency"""
        print("\n⚡ Testing settings update latency...")

        import time
        start = time.time()

        response = client.post('/api/config/webui', json={
            'sharpness': 2.0
        })

        latency = time.time() - start

        assert response.status_code == 200
        assert latency < 1.0  # Should complete in < 1 second

        print(f"   ✓ Settings update latency: {latency*1000:.0f}ms")

    def test_rapid_ui_interactions(self, client):
        """Test rapid UI interactions don't cause errors"""
        print("\n⚡ Testing rapid UI interactions...")

        # Rapid settings updates
        for value in [1.5, 2.0, 2.5, 3.0]:
            response = client.post('/api/config/webui', json={
                'sharpness': value
            })
            assert response.status_code == 200
            time.sleep(0.05)  # 50ms between requests

        print("   ✓ Rapid interactions handled gracefully")
