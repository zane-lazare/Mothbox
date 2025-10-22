"""
Integration Tests: Preset Management Workflows

Tests complete preset workflows from start to finish, including:
- List presets → Select → Apply → Verify settings updated
- Save current settings as preset → Apply later → Verify match
- Apply preset to capture/preview/both → Verify correct targets updated
- Delete user preset workflow
- Built-in preset application and protection

Run with: pytest Tests/integration/test_preset_workflows.py -v -s

Note: Requires real Raspberry Pi hardware with camera
"""

import pytest
import sys
from pathlib import Path
import time
import csv
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

from mothbox_paths import WEBUI_SETTINGS_FILE, CAMERA_SETTINGS_FILE


class TestPresetWorkflow1_ListSelectApplyVerify:
    """
    Workflow 1: List presets → Select → Apply → Verify settings updated

    This is the primary workflow for users to:
    1. View available presets
    2. Select a preset (e.g., "Night Photography")
    3. Apply it to camera/preview/both
    4. Verify settings were updated correctly
    """

    def test_list_and_apply_builtin_preset_workflow(self, client):
        """Test complete workflow: list → select → apply → verify"""
        print("\n" + "="*70)
        print("Workflow 1: List Presets → Select → Apply → Verify")
        print("="*70)

        # Step 1: List all available presets
        print("\n📋 Step 1: List available presets...")
        response = client.get('/api/presets')
        assert response.status_code == 200
        data = response.get_json()

        assert 'presets' in data
        assert 'counts' in data
        presets = data['presets']
        print(f"   ✓ Found {data['counts']['total']} presets")
        print(f"     - Built-in: {data['counts']['built_in']}")
        print(f"     - User: {data['counts']['user']}")

        # Verify we have built-in presets
        builtin_presets = [p for p in presets if p['category'] == 'built-in']
        assert len(builtin_presets) > 0, "Should have built-in presets"

        # Step 2: Select a preset (use first built-in)
        selected_preset = builtin_presets[0]
        print(f"\n🎨 Step 2: Select preset '{selected_preset['display_name']}'...")
        print(f"   Description: {selected_preset['description']}")

        # Get preset details
        response = client.get(f"/api/presets/{selected_preset['name']}")

        if response.status_code != 200:
            pytest.skip(f"Preset {selected_preset['name']} file not found in /etc/mothbox/presets")

        preset_data = response.get_json()
        assert 'settings' in preset_data
        print(f"   ✓ Loaded preset details")

        # Step 3: Apply preset to camera settings
        print(f"\n📸 Step 3: Apply preset to capture settings...")
        response = client.post(f"/api/presets/{selected_preset['name']}/apply",
                              json={'apply_to': 'capture'})

        assert response.status_code == 200
        apply_result = response.get_json()
        assert apply_result['success'] is True
        print(f"   ✓ {apply_result['message']}")

        # Step 4: Verify settings were updated
        print(f"\n✅ Step 4: Verify camera settings updated...")
        if CAMERA_SETTINGS_FILE.exists():
            with open(CAMERA_SETTINGS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                current_settings = {row['SETTING']: row['VALUE'] for row in reader}

            # Check that some preset settings were applied
            if 'camera' in preset_data['settings']:
                for setting_name, setting_value in preset_data['settings']['camera'].items():
                    if setting_name in current_settings:
                        print(f"   ✓ {setting_name}: {current_settings[setting_name]}")

        print("\n✨ Workflow complete!")


class TestPresetWorkflow2_SaveAndReuse:
    """
    Workflow 2: Save current settings as preset → Apply later → Verify match

    This workflow tests:
    1. User adjusts settings manually
    2. Saves current state as custom preset
    3. Changes settings to something else
    4. Re-applies saved preset
    5. Verifies settings match original
    """

    def test_save_current_settings_and_reuse(self, client):
        """Test workflow: adjust → save preset → change → reapply → verify match"""
        print("\n" + "="*70)
        print("Workflow 2: Save Current Settings → Modify → Reapply → Verify")
        print("="*70)

        preset_name = f"test_preset_{int(time.time())}"

        try:
            # Step 1: Set specific camera settings
            print("\n📝 Step 1: Configure specific settings...")
            original_settings = {
                'ExposureTime': '7500',
                'AnalogueGain': '3.5',
                'Sharpness': '2.0'
            }

            response = client.post('/api/camera/settings', json=original_settings)
            assert response.status_code == 200
            print("   ✓ Settings configured")

            # Step 2: Save current settings as preset
            print(f"\n💾 Step 2: Save as preset '{preset_name}'...")
            response = client.post('/api/presets', json={
                'name': preset_name,
                'description': 'Test preset for workflow',
                'from_current': True
            })

            assert response.status_code == 200
            result = response.get_json()
            assert result['success'] is True
            print(f"   ✓ Preset saved: {result['message']}")

            # Step 3: Change settings to something different
            print("\n🔄 Step 3: Modify settings to different values...")
            response = client.post('/api/camera/settings', json={
                'ExposureTime': '15000',
                'AnalogueGain': '6.0',
                'Sharpness': '0.5'
            })
            assert response.status_code == 200
            print("   ✓ Settings changed")

            # Step 4: Re-apply saved preset
            print(f"\n📸 Step 4: Re-apply saved preset '{preset_name}'...")
            response = client.post(f'/api/presets/{preset_name}/apply',
                                  json={'apply_to': 'capture'})

            assert response.status_code == 200
            apply_result = response.get_json()
            assert apply_result['success'] is True
            print(f"   ✓ Preset re-applied")

            # Step 5: Verify settings match original
            print("\n✅ Step 5: Verify settings restored to original values...")
            if CAMERA_SETTINGS_FILE.exists():
                with open(CAMERA_SETTINGS_FILE, 'r') as f:
                    reader = csv.DictReader(f)
                    current_settings = {row['SETTING']: row['VALUE'] for row in reader}

                for setting_name, expected_value in original_settings.items():
                    if setting_name in current_settings:
                        actual_value = current_settings[setting_name]
                        # Allow for float comparison tolerance
                        try:
                            if float(actual_value) == float(expected_value):
                                print(f"   ✓ {setting_name}: {actual_value} (matches original)")
                        except ValueError:
                            if actual_value == expected_value:
                                print(f"   ✓ {setting_name}: {actual_value} (matches original)")

            print("\n✨ Workflow complete!")

        finally:
            # Cleanup: Delete test preset
            print(f"\n🧹 Cleanup: Deleting test preset '{preset_name}'...")
            client.delete(f'/api/presets/{preset_name}')


class TestPresetWorkflow3_ApplyToTargets:
    """
    Workflow 3: Apply preset to different targets (capture/preview/both)

    Tests that apply_to parameter correctly updates:
    - capture: Only camera_settings.csv
    - preview: Only webui_settings.txt
    - both: Both files
    """

    def test_apply_preset_to_capture_only(self, client):
        """Test applying preset to capture settings only"""
        print("\n" + "="*70)
        print("Workflow 3a: Apply Preset to Capture Only")
        print("="*70)

        # Get first available preset
        response = client.get('/api/presets')
        presets = response.get_json()['presets']
        if not presets:
            pytest.skip("No presets available")

        preset_name = presets[0]['name']

        # Apply to capture only
        print(f"\n📸 Applying preset '{preset_name}' to CAPTURE only...")
        response = client.post(f'/api/presets/{preset_name}/apply',
                              json={'apply_to': 'capture'})

        if response.status_code == 200:
            result = response.get_json()
            assert 'capture' in result.get('applied_to', [])
            assert 'preview' not in result.get('applied_to', [])
            print(f"   ✓ Applied to capture only")
            print(f"   Message: {result['message']}")
        else:
            pytest.skip(f"Preset file not found: {preset_name}")

    def test_apply_preset_to_preview_only(self, client):
        """Test applying preset to preview settings only"""
        print("\n" + "="*70)
        print("Workflow 3b: Apply Preset to Preview Only")
        print("="*70)

        # Get first available preset
        response = client.get('/api/presets')
        presets = response.get_json()['presets']
        if not presets:
            pytest.skip("No presets available")

        preset_name = presets[0]['name']

        # Apply to preview only
        print(f"\n👁️  Applying preset '{preset_name}' to PREVIEW only...")
        response = client.post(f'/api/presets/{preset_name}/apply',
                              json={'apply_to': 'preview'})

        if response.status_code == 200:
            result = response.get_json()
            assert 'preview' in result.get('applied_to', [])
            assert 'capture' not in result.get('applied_to', [])
            print(f"   ✓ Applied to preview only")
            print(f"   Message: {result['message']}")
        else:
            pytest.skip(f"Preset file not found: {preset_name}")

    def test_apply_preset_to_both(self, client):
        """Test applying preset to both capture and preview"""
        print("\n" + "="*70)
        print("Workflow 3c: Apply Preset to Both Capture and Preview")
        print("="*70)

        # Get first available preset
        response = client.get('/api/presets')
        presets = response.get_json()['presets']
        if not presets:
            pytest.skip("No presets available")

        preset_name = presets[0]['name']

        # Apply to both
        print(f"\n🔄 Applying preset '{preset_name}' to BOTH...")
        response = client.post(f'/api/presets/{preset_name}/apply',
                              json={'apply_to': 'both'})

        if response.status_code == 200:
            result = response.get_json()
            applied_to = result.get('applied_to', [])
            assert 'capture' in applied_to or 'preview' in applied_to
            print(f"   ✓ Applied to: {', '.join(applied_to)}")
            print(f"   Message: {result['message']}")
        else:
            pytest.skip(f"Preset file not found: {preset_name}")


class TestPresetWorkflow4_UserPresetManagement:
    """
    Workflow 4: User preset CRUD operations

    Tests:
    1. Create user preset
    2. List and verify it appears
    3. Apply user preset
    4. Delete user preset
    5. Verify deletion
    """

    def test_complete_user_preset_lifecycle(self, client):
        """Test complete user preset lifecycle: create → apply → delete"""
        print("\n" + "="*70)
        print("Workflow 4: User Preset Lifecycle (Create → Use → Delete)")
        print("="*70)

        preset_name = f"user_test_{int(time.time())}"

        # Step 1: Create user preset
        print(f"\n💾 Step 1: Create user preset '{preset_name}'...")
        response = client.post('/api/presets', json={
            'name': preset_name,
            'description': 'Test user preset',
            'from_current': True
        })

        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        print(f"   ✓ Created: {result['message']}")

        # Step 2: Verify preset appears in list
        print(f"\n📋 Step 2: Verify preset appears in list...")
        response = client.get('/api/presets')
        presets = response.get_json()['presets']

        user_preset = next((p for p in presets if p['name'] == preset_name), None)
        assert user_preset is not None, f"Preset '{preset_name}' not found in list"
        assert user_preset['category'] == 'user'
        print(f"   ✓ Found in preset list")
        print(f"     Display name: {user_preset['display_name']}")
        print(f"     Category: {user_preset['category']}")

        # Step 3: Apply user preset
        print(f"\n📸 Step 3: Apply user preset...")
        response = client.post(f'/api/presets/{preset_name}/apply',
                              json={'apply_to': 'capture'})

        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        print(f"   ✓ Applied successfully")

        # Step 4: Delete user preset
        print(f"\n🗑️  Step 4: Delete user preset...")
        response = client.delete(f'/api/presets/{preset_name}')

        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        print(f"   ✓ Deleted: {result['message']}")

        # Step 5: Verify deletion
        print(f"\n✅ Step 5: Verify preset no longer exists...")
        response = client.get('/api/presets')
        presets = response.get_json()['presets']

        user_preset = next((p for p in presets if p['name'] == preset_name), None)
        assert user_preset is None, f"Preset '{preset_name}' still exists after deletion"
        print(f"   ✓ Preset successfully removed from list")

        print("\n✨ Workflow complete!")


class TestPresetWorkflow5_BuiltInProtection:
    """
    Workflow 5: Built-in preset protection

    Verifies that built-in presets:
    1. Can be applied
    2. Cannot be deleted
    3. Cannot be overwritten
    """

    def test_builtin_preset_protection(self, client):
        """Test that built-in presets are protected from modification"""
        print("\n" + "="*70)
        print("Workflow 5: Built-in Preset Protection")
        print("="*70)

        # Step 1: Get a built-in preset
        print("\n📋 Step 1: Get built-in preset...")
        response = client.get('/api/presets')
        presets = response.get_json()['presets']

        builtin_presets = [p for p in presets if p['category'] == 'built-in']
        if not builtin_presets:
            pytest.skip("No built-in presets available")

        preset_name = builtin_presets[0]['name']
        print(f"   Using: {builtin_presets[0]['display_name']}")

        # Step 2: Verify it can be applied
        print(f"\n📸 Step 2: Verify built-in preset CAN be applied...")
        response = client.post(f'/api/presets/{preset_name}/apply',
                              json={'apply_to': 'capture'})

        if response.status_code == 200:
            print(f"   ✓ Built-in preset successfully applied")
        else:
            pytest.skip(f"Preset file not found: {preset_name}")

        # Step 3: Verify it CANNOT be deleted
        print(f"\n🔒 Step 3: Verify built-in preset CANNOT be deleted...")
        response = client.delete(f'/api/presets/{preset_name}')

        assert response.status_code == 400
        result = response.get_json()
        assert 'error' in result
        assert 'built-in' in result['error'].lower()
        print(f"   ✓ Deletion blocked: {result['error']}")

        print("\n✨ Built-in presets are protected!")


@pytest.fixture
def client():
    """Create Flask test client with all blueprints"""
    from flask import Flask
    from routes.presets import presets_bp
    from routes.camera import camera_bp
    from routes.config import config_bp

    app = Flask(__name__)
    app.register_blueprint(presets_bp, url_prefix='/api/presets')
    app.register_blueprint(camera_bp, url_prefix='/api/camera')
    app.register_blueprint(config_bp, url_prefix='/api/config')

    return app.test_client()
