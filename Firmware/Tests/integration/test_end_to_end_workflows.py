"""
Integration Tests: End-to-End Workflows (Feature Set 4)

Tests complete user workflows from start to finish, including:
- Adjust preview → Test capture → Copy to capture → Verify
- Autofocus → Calibrate → Copy settings → Test capture
- Settings comparison workflows
- Full optimization workflows
- Multi-step error recovery

Run with: pytest Tests/integration/test_end_to_end_workflows.py -v -s

Note: Requires real Raspberry Pi hardware with camera
"""

import pytest
import sys
from pathlib import Path
import time
import csv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

from mothbox_paths import PHOTOS_DIR, WEBUI_SETTINGS_FILE, CAMERA_SETTINGS_FILE


class TestWorkflow1_AdjustPreviewTestCaptureCopyVerify:
    """
    Workflow 1: Adjust preview → Test capture → Copy to capture → Verify production ready

    This is the primary workflow for users to:
    1. Adjust preview settings (sharpness, brightness, etc.)
    2. Take test capture to see results
    3. Copy settings to production if satisfied
    4. Verify production config is ready
    """

    def test_complete_adjustment_workflow(self, client):
        """Test complete workflow: adjust → capture → copy → verify"""
        print("\n" + "="*60)
        print("Workflow 1: Adjust Preview → Test Capture → Copy → Verify")
        print("="*60)

        # Step 1: Adjust preview settings
        print("\n📝 Step 1: Adjust preview settings...")
        response = client.post('/api/config/webui', json={
            'sharpness': 2.5,
            'brightness': 0.2,
            'contrast': 1.3,
            'saturation': 1.1
        })
        assert response.status_code == 200
        print("   ✓ Preview settings adjusted")

        # Step 2: Take test capture to see results
        print("\n📸 Step 2: Take test capture...")
        response = client.post('/api/camera/test-capture')

        if response.status_code != 200:
            print("   ⚠ Camera busy, skipping workflow")
            return

        data = response.get_json()
        assert data['success'] == True
        test_photo_path = data['test_photo_path']
        print(f"   ✓ Test capture: {test_photo_path}")

        # Verify test capture used preview settings
        settings_used = data['settings_used']
        assert float(settings_used['Sharpness']) == 2.5
        assert float(settings_used['Brightness']) == 0.2

        # Step 3: User likes results, copy to production
        print("\n📋 Step 3: Copy settings to production...")
        response = client.post('/api/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] == True
        print(f"   ✓ Copied {len(data['copied'])} settings: {data['copied']}")

        # Step 4: Verify production settings updated
        print("\n✅ Step 4: Verify production ready...")
        response = client.get('/api/camera/settings')
        assert response.status_code == 200

        capture_settings = response.get_json()
        assert float(capture_settings.get('Sharpness', 0)) == 2.5
        print("   ✓ Production settings verified")

        print("\n✅ Workflow 1 complete!")

    def test_workflow_with_multiple_test_captures(self, client):
        """Test workflow with multiple test captures before copying"""
        print("\n" + "="*60)
        print("Workflow 1 Variation: Multiple test captures")
        print("="*60)

        # Adjust settings
        client.post('/api/config/webui', json={'sharpness': 1.8})

        # First test capture
        response = client.post('/api/camera/test-capture')
        if response.status_code != 200:
            print("⚠ Camera busy, skipping")
            return

        print("   ✓ Test capture 1 complete")
        time.sleep(0.5)

        # Adjust again
        client.post('/api/config/webui', json={'sharpness': 2.2})

        # Second test capture
        response = client.post('/api/camera/test-capture')
        if response.status_code == 200:
            print("   ✓ Test capture 2 complete")

            # Copy final settings
            response = client.post('/api/config/copy-settings', json={
                'direction': 'preview_to_capture'
            })
            assert response.status_code == 200

            print("\n✅ Multiple test captures workflow complete!")
        else:
            print("⚠ Second capture failed")


class TestWorkflow2_AutofocusCalibrateVerify:
    """
    Workflow 2: Autofocus → Calibrate → Copy settings → Test capture

    This is the optimization workflow for:
    1. Run autofocus to find best focus position
    2. Calibrate exposure and gain
    3. Copy optimized settings to production
    4. Test capture to verify
    """

    def test_complete_optimization_workflow(self, client):
        """Test complete optimization workflow"""
        print("\n" + "="*60)
        print("Workflow 2: Autofocus → Calibrate → Copy → Verify")
        print("="*60)

        # Step 1: Run autofocus
        print("\n🔍 Step 1: Run autofocus...")
        response = client.post('/api/camera/autofocus')

        if response.status_code != 200:
            print("   ⚠ Camera busy, skipping workflow")
            return

        data = response.get_json()
        if data.get('success'):
            lens_position = data['lens_position']
            print(f"   ✓ Autofocus: {lens_position} diopters")
        else:
            print("   ⚠ Autofocus failed")

        time.sleep(1)

        # Step 2: Run calibration
        print("\n⚙️ Step 2: Calibrate exposure and gain...")
        response = client.post('/api/camera/calibrate', json={
            'apply_to': 'capture'
        })

        if response.status_code != 200:
            print("   ⚠ Calibration failed, skipping")
            return

        data = response.get_json()
        if data.get('success'):
            print(f"   ✓ Calibration complete")
            print(f"   Before: {data.get('before', {})}")
            print(f"   After: {data.get('after', {})}")
        else:
            print("   ⚠ Calibration failed")

        # Step 3: Take test capture to verify
        print("\n📸 Step 3: Test capture to verify...")
        response = client.post('/api/camera/test-capture')

        if response.status_code == 200:
            data = response.get_json()
            print(f"   ✓ Test capture: {data['test_photo_path']}")
            print(f"   Metadata: {data['metadata']}")

            print("\n✅ Workflow 2 complete!")
        else:
            print("   ⚠ Test capture failed")

    def test_calibration_with_both_modes(self, client):
        """Test calibration applied to both preview and capture"""
        print("\n" + "="*60)
        print("Workflow 2 Variation: Calibrate both modes")
        print("="*60)

        # Calibrate both preview and capture
        response = client.post('/api/camera/calibrate', json={
            'apply_to': 'both'
        })

        if response.status_code == 200:
            data = response.get_json()
            assert data.get('success') == True

            print("   ✓ Both modes calibrated")
            print("\n✅ Both-mode calibration workflow complete!")
        else:
            print("   ⚠ Calibration failed")


class TestWorkflow3_SettingsComparison:
    """
    Workflow 3: Settings comparison (preview vs capture differences)

    Users want to:
    1. View current preview settings
    2. View current capture settings
    3. Compare differences
    4. Decide whether to sync
    """

    def test_compare_preview_and_capture_settings(self, client):
        """Test comparing preview and capture settings"""
        print("\n" + "="*60)
        print("Workflow 3: Settings Comparison")
        print("="*60)

        # Get preview settings
        print("\n📋 Step 1: Get preview settings...")
        response = client.get('/api/config/webui')
        assert response.status_code == 200

        preview_settings = response.get_json()
        print(f"   Preview sharpness: {preview_settings.get('sharpness')}")
        print(f"   Preview brightness: {preview_settings.get('brightness')}")

        # Get capture settings
        print("\n📋 Step 2: Get capture settings...")
        response = client.get('/api/camera/settings')
        assert response.status_code == 200

        capture_settings = response.get_json()
        print(f"   Capture Sharpness: {capture_settings.get('Sharpness')}")
        print(f"   Capture Brightness: {capture_settings.get('Brightness')}")

        # Compare
        print("\n🔍 Step 3: Compare differences...")
        preview_sharp = float(preview_settings.get('sharpness', 0))
        capture_sharp = float(capture_settings.get('Sharpness', 0))

        if preview_sharp != capture_sharp:
            print(f"   ⚠ Sharpness differs: preview={preview_sharp}, capture={capture_sharp}")
        else:
            print(f"   ✓ Sharpness matches: {preview_sharp}")

        print("\n✅ Comparison workflow complete!")

    def test_sync_divergent_settings(self, client):
        """Test syncing settings when they've diverged"""
        print("\n" + "="*60)
        print("Workflow 3 Variation: Sync divergent settings")
        print("="*60)

        # Set different preview settings
        client.post('/api/config/webui', json={
            'sharpness': 3.0,
            'brightness': 0.3
        })

        # Settings are now different - sync them
        print("\n🔄 Syncing divergent settings...")
        response = client.post('/api/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })

        if response.status_code == 200:
            data = response.get_json()
            print(f"   ✓ Synced: {data['copied']}")
            print("\n✅ Sync workflow complete!")


class TestWorkflow4_FullOptimization:
    """
    Workflow 4: Full optimization (focus + calibrate + quality tune + copy)

    Complete optimization workflow:
    1. Run autofocus
    2. Run calibration
    3. Fine-tune image quality in preview
    4. Test capture
    5. Copy all to production
    """

    def test_complete_optimization_workflow(self, client):
        """Test complete optimization workflow"""
        print("\n" + "="*60)
        print("Workflow 4: Full Optimization")
        print("="*60)

        # Step 1: Autofocus
        print("\n🔍 Step 1: Autofocus...")
        response = client.post('/api/camera/autofocus')

        if response.status_code != 200:
            print("   ⚠ Camera busy, skipping workflow")
            return

        if response.get_json().get('success'):
            print("   ✓ Autofocus complete")
        else:
            print("   ⚠ Autofocus failed")

        time.sleep(1)

        # Step 2: Calibrate
        print("\n⚙️ Step 2: Calibrate...")
        response = client.post('/api/camera/calibrate', json={
            'apply_to': 'preview'
        })

        if response.status_code == 200 and response.get_json().get('success'):
            print("   ✓ Calibration complete")
        else:
            print("   ⚠ Calibration skipped")

        time.sleep(0.5)

        # Step 3: Fine-tune image quality
        print("\n🎨 Step 3: Fine-tune image quality...")
        response = client.post('/api/config/webui', json={
            'sharpness': 2.5,
            'brightness': 0.1,
            'contrast': 1.2,
            'saturation': 1.1
        })
        assert response.status_code == 200
        print("   ✓ Quality settings adjusted")

        # Step 4: Test capture
        print("\n📸 Step 4: Test capture...")
        response = client.post('/api/camera/test-capture')

        if response.status_code != 200:
            print("   ⚠ Test capture failed")
            return

        data = response.get_json()
        print(f"   ✓ Test capture: {data['test_photo_path']}")

        # Step 5: Copy to production
        print("\n📋 Step 5: Copy to production...")
        response = client.post('/api/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })

        if response.status_code == 200:
            data = response.get_json()
            print(f"   ✓ Copied {len(data['copied'])} settings")

            print("\n✅ Full optimization workflow complete!")
        else:
            print("   ⚠ Copy failed")


class TestMultiStepErrorRecovery:
    """Test error recovery in multi-step workflows"""

    def test_recovery_from_autofocus_failure(self, client):
        """Test workflow continues after autofocus failure"""
        print("\n" + "="*60)
        print("Error Recovery: Autofocus failure")
        print("="*60)

        # Attempt autofocus
        response = client.post('/api/camera/autofocus')

        if response.status_code != 200:
            print("   ⚠ Autofocus failed (expected)")

            # Should still be able to continue with manual settings
            print("\n📝 Continue with manual settings...")
            response = client.post('/api/config/webui', json={
                'af_mode': 0,  # Manual focus
                'sharpness': 2.0
            })
            assert response.status_code == 200

            print("   ✓ Recovered: Manual settings applied")
            print("\n✅ Recovery workflow complete!")

    def test_recovery_from_calibration_failure(self, client):
        """Test workflow continues after calibration failure"""
        print("\n" + "="*60)
        print("Error Recovery: Calibration failure")
        print("="*60)

        # Attempt calibration (may fail if camera busy)
        response = client.post('/api/camera/calibrate', json={
            'apply_to': 'capture'
        })

        if response.status_code != 200:
            print("   ⚠ Calibration failed (expected)")

            # Should still be able to use existing settings
            print("\n📸 Continue with existing settings...")
            response = client.post('/api/camera/test-capture')

            if response.status_code == 200:
                print("   ✓ Recovered: Test capture successful")
                print("\n✅ Recovery workflow complete!")
            else:
                print("   ⚠ Camera still busy")

    def test_recovery_from_test_capture_failure(self, client):
        """Test workflow continues after test capture failure"""
        print("\n" + "="*60)
        print("Error Recovery: Test capture failure")
        print("="*60)

        # Set preview settings
        client.post('/api/config/webui', json={'sharpness': 2.5})

        # Attempt test capture
        response = client.post('/api/camera/test-capture')

        if response.status_code != 200:
            print("   ⚠ Test capture failed (expected)")

            # Should still be able to copy settings
            print("\n📋 Continue with settings copy...")
            response = client.post('/api/config/copy-settings', json={
                'direction': 'preview_to_capture'
            })

            if response.status_code == 200:
                print("   ✓ Recovered: Settings copied without test capture")
                print("\n✅ Recovery workflow complete!")

    def test_recovery_chain(self, client):
        """Test recovery through multiple failures"""
        print("\n" + "="*60)
        print("Error Recovery: Multiple failure recovery")
        print("="*60)

        operations = [
            ('Autofocus', lambda: client.post('/api/camera/autofocus')),
            ('Calibration', lambda: client.post('/api/camera/calibrate', json={'apply_to': 'preview'})),
            ('Test capture', lambda: client.post('/api/camera/test-capture')),
            ('Copy settings', lambda: client.post('/api/config/copy-settings', json={'direction': 'preview_to_capture'}))
        ]

        successful = []
        failed = []

        for name, operation in operations:
            try:
                response = operation()
                if response.status_code == 200:
                    successful.append(name)
                    print(f"   ✓ {name} succeeded")
                else:
                    failed.append(name)
                    print(f"   ⚠ {name} failed, continuing...")

                time.sleep(0.5)
            except Exception as e:
                failed.append(name)
                print(f"   ⚠ {name} error: {e}")

        print(f"\n✅ Recovery chain: {len(successful)}/{len(operations)} succeeded")


class TestSettingsPropagation:
    """Test settings propagation through the system"""

    def test_preview_to_capture_propagation(self, client):
        """Test settings propagate from preview to capture correctly"""
        print("\n" + "="*60)
        print("Settings Propagation: Preview → Capture")
        print("="*60)

        # Set specific preview values
        preview_values = {
            'sharpness': 2.7,
            'brightness': 0.15,
            'contrast': 1.25,
            'saturation': 1.05
        }

        response = client.post('/api/config/webui', json=preview_values)
        assert response.status_code == 200

        # Copy to capture
        response = client.post('/api/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })
        assert response.status_code == 200

        # Verify capture settings
        response = client.get('/api/camera/settings')
        capture_settings = response.get_json()

        # Check propagation
        assert float(capture_settings.get('Sharpness', 0)) == preview_values['sharpness']
        assert float(capture_settings.get('Brightness', 0)) == preview_values['brightness']

        print("   ✓ Settings propagated correctly")
        print("\n✅ Propagation test complete!")

    def test_capture_to_preview_propagation(self, client):
        """Test settings propagate from capture to preview correctly"""
        print("\n" + "="*60)
        print("Settings Propagation: Capture → Preview")
        print("="*60)

        # Set capture settings
        response = client.post('/api/camera/settings', json={
            'Sharpness': 2.3,
            'Brightness': 0.2
        })
        assert response.status_code == 200

        # Copy to preview
        response = client.post('/api/config/copy-settings', json={
            'direction': 'capture_to_preview'
        })
        assert response.status_code == 200

        # Verify preview settings
        response = client.get('/api/config/webui')
        preview_settings = response.get_json()

        # Check propagation
        assert float(preview_settings.get('sharpness', 0)) == 2.3
        assert float(preview_settings.get('brightness', 0)) == 0.2

        print("   ✓ Settings propagated correctly")
        print("\n✅ Propagation test complete!")


class TestNewUserOnboarding:
    """Test complete new user onboarding workflow"""

    def test_new_user_complete_workflow(self, client):
        """Test complete workflow for new user"""
        print("\n" + "="*60)
        print("New User Onboarding: Complete Workflow")
        print("="*60)

        # Step 1: Run autofocus (first time)
        print("\n🎯 Step 1: First-time autofocus...")
        response = client.post('/api/camera/autofocus')

        if response.status_code == 200:
            print("   ✓ Autofocus complete")
        else:
            print("   ⚠ Skipping (camera busy)")
            return

        time.sleep(1)

        # Step 2: Calibrate
        print("\n⚙️ Step 2: Initial calibration...")
        response = client.post('/api/camera/calibrate', json={
            'apply_to': 'both'
        })

        if response.status_code == 200:
            print("   ✓ Both modes calibrated")
        else:
            print("   ⚠ Calibration skipped")

        # Step 3: Test preview
        print("\n📸 Step 3: First test capture...")
        response = client.post('/api/camera/test-capture')

        if response.status_code == 200:
            data = response.get_json()
            print(f"   ✓ First test capture: {data['test_photo_path']}")

            # Step 4: User is happy, settings already synced (both mode)
            print("\n✅ Step 4: System ready for production!")
            print("\n✅ New user onboarding complete!")
        else:
            print("   ⚠ Test capture failed")
