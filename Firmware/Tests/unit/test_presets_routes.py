"""
Unit tests for preset management routes (Issue #78 Phase 2C)

Tests all preset endpoints with comprehensive mocking for CI/CD compatibility.
Focus areas: preset CRUD operations, validation, workflow compatibility, file I/O.

Test structure:
- TestListPresetsEndpoint: GET /api/presets tests
- TestGetPresetEndpoint: GET /api/presets/<name> tests
- TestCreatePresetEndpoint: POST /api/presets tests
- TestApplyPresetEndpoint: POST /api/presets/<name>/apply tests
- TestDeletePresetEndpoint: DELETE /api/presets/<name> tests
- TestPresetValidation: Input validation and security tests
"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Import after path setup
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestListPresetsEndpoint:
    """Tests for GET /api/presets endpoint"""

    def test_list_presets_returns_all_presets(self, client):
        """GET /presets returns all available presets"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.list_presets.return_value = [
                {
                    'name': 'daylight',
                    'display_name': '☀️ Daylight',
                    'description': 'Daylight preset',
                    'category': 'built-in',
                    'workflow': 'both'
                },
                {
                    'name': 'my_preset',
                    'display_name': 'My Preset',
                    'description': 'User preset',
                    'category': 'user',
                    'workflow': 'photo'
                }
            ]
            mock_pm.get_preset_count.return_value = {'built-in': 5, 'user': 1, 'total': 6}

            response = client.get('/api/presets')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['presets']) == 2
        assert data['counts']['total'] == 6
        assert data['presets'][0]['name'] == 'daylight'
        assert data['presets'][1]['name'] == 'my_preset'

    def test_list_presets_filters_by_workflow(self, client):
        """GET /presets?workflow=photo filters presets"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.list_presets.return_value = [
                {'name': 'preset1', 'workflow': 'photo'},
                {'name': 'preset2', 'workflow': 'liveview'},
                {'name': 'preset3', 'workflow': 'both'},
                {'name': 'preset4', 'workflow': 'photo'}
            ]
            mock_pm.get_preset_count.return_value = {'built-in': 4, 'user': 0, 'total': 4}

            response = client.get('/api/presets?workflow=photo')

        assert response.status_code == 200
        data = response.get_json()
        # Should include photo and both
        assert len(data['presets']) == 3
        workflows = [p['workflow'] for p in data['presets']]
        assert 'photo' in workflows
        assert 'both' in workflows
        assert 'liveview' not in workflows

    def test_list_presets_handles_error(self, client):
        """GET /presets returns 500 on error"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.list_presets.side_effect = RuntimeError("Preset directory not found")

            response = client.get('/api/presets')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data


class TestGetPresetEndpoint:
    """Tests for GET /api/presets/<name> endpoint"""

    def test_get_preset_returns_preset_data(self, client):
        """GET /presets/<name> returns specific preset"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.get_preset.return_value = {
                'name': 'daylight',
                'display_name': '☀️ Daylight',
                'description': 'Daylight photography',
                'workflow': 'both',
                'settings': {
                    'camera': {'Sharpness': '2.5'},
                    'liveview': {'stream_width': '1024'}
                }
            }

            response = client.get('/api/presets/daylight')

        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'daylight'
        assert 'settings' in data
        assert data['settings']['camera']['Sharpness'] == '2.5'

    def test_get_preset_returns_404_when_not_found(self, client):
        """GET /presets/<name> returns 404 for missing preset"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.get_preset.return_value = None

            response = client.get('/api/presets/nonexistent')

        assert response.status_code == 404
        data = response.get_json()
        assert 'not found' in data['error']

    def test_get_preset_handles_error(self, client):
        """GET /presets/<name> returns 500 on error"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.get_preset.side_effect = PermissionError("Cannot read preset file")

            response = client.get('/api/presets/daylight')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data


class TestCreatePresetEndpoint:
    """Tests for POST /api/presets endpoint"""

    def test_create_preset_with_provided_settings(self, client):
        """POST /presets creates preset with provided settings"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.save_preset.return_value = (True, "Preset saved successfully")

            response = client.post('/api/presets', json={
                'name': 'my_preset',
                'description': 'My custom preset',
                'workflow': 'photo',
                'from_current': False,
                'settings': {
                    'camera': {'Sharpness': '3.0'},
                    'liveview': {'stream_width': '1280'}
                }
            })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['name'] == 'my_preset'

        # Verify save_preset was called correctly
        mock_pm.save_preset.assert_called_once()
        call_args = mock_pm.save_preset.call_args
        assert call_args[0][0] == 'my_preset'  # name
        assert 'camera' in call_args[0][1]  # settings
        assert call_args[0][2] == 'My custom preset'  # description
        assert call_args[1]['workflow'] == 'photo'

    def test_create_preset_from_current_settings(self, client, tmp_path, monkeypatch):
        """POST /presets creates preset from current camera/liveview settings"""
        from Tests.conftest import patch_path_constant_everywhere

        # Setup camera settings file
        camera_file = tmp_path / "camera_settings.csv"
        camera_file.write_text("SETTING,VALUE,DETAILS\nSharpness,2.5,Default\nBrightness,0.0,Default\n")
        patch_path_constant_everywhere(monkeypatch, 'CAMERA_SETTINGS_FILE', camera_file)

        # Setup liveview settings file
        liveview_file = tmp_path / "liveview_settings.txt"
        liveview_file.write_text("stream_width=1024\nstream_height=768\n")
        patch_path_constant_everywhere(monkeypatch, 'LIVEVIEW_SETTINGS_FILE', liveview_file)

        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.save_preset.return_value = (True, "Preset saved")

            response = client.post('/api/presets', json={
                'name': 'current_snapshot',
                'description': 'Snapshot of current settings',
                'from_current': True
            })

        assert response.status_code == 200

        # Verify save_preset was called with current settings
        call_args = mock_pm.save_preset.call_args
        settings = call_args[0][1]
        assert 'camera' in settings
        assert 'liveview' in settings
        assert settings['camera']['Sharpness'] == '2.5'
        assert settings['liveview']['stream_width'] == '1024'

    def test_create_preset_validates_name_required(self, client):
        """POST /presets requires preset name"""
        response = client.post('/api/presets', json={
            'description': 'No name provided',
            'settings': {}
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'name is required' in data['error']

    def test_create_preset_validates_settings_required(self, client):
        """POST /presets requires settings when from_current=false"""
        response = client.post('/api/presets', json={
                'name': 'preset1',
            'from_current': False
            # No settings provided
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'Settings are required' in data['error']

    def test_create_preset_validates_no_data(self, client):
        """POST /presets returns 400 when no data provided"""
        response = client.post('/api/presets', json={})

        assert response.status_code == 400
        data = response.get_json()
        assert 'name is required' in data['error']

    def test_create_preset_handles_save_failure(self, client):
        """POST /presets returns 400 when save fails"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.save_preset.return_value = (False, "Preset name contains invalid characters")

            response = client.post('/api/presets', json={
                'name': 'bad/name',
                'settings': {'camera': {}}
            })

        assert response.status_code == 400
        data = response.get_json()
        assert 'invalid characters' in data['error']

    def test_create_preset_handles_error(self, client):
        """POST /presets returns 500 on unexpected error"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.save_preset.side_effect = IOError("Disk full")

            response = client.post('/api/presets', json={
                'name': 'preset1',
                'settings': {'camera': {}}
            })

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data


class TestApplyPresetEndpoint:
    """Tests for POST /api/presets/<name>/apply endpoint"""

    def test_apply_preset_to_capture(self, client, tmp_path, monkeypatch):
        """POST /presets/<name>/apply applies preset to camera settings"""
        from Tests.conftest import patch_path_constant_everywhere

        # Setup camera settings file
        camera_file = tmp_path / "camera_settings.csv"
        camera_file.write_text("SETTING,VALUE,DETAILS\nSharpness,1.0,Default\n")
        patch_path_constant_everywhere(monkeypatch, 'CAMERA_SETTINGS_FILE', camera_file)

        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.get_preset.return_value = {
                'name': 'daylight',
                'workflow': 'both',
                'settings': {
                    'camera': {'Sharpness': '2.5', 'Brightness': '0.2'}
                }
            }

            response = client.post('/api/presets/daylight/apply', json={
                'apply_to': 'capture'
            })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['applied_to'] == 'capture'

        # Verify settings were applied
        content = camera_file.read_text()
        assert 'Sharpness,2.5' in content

    def test_apply_preset_validates_not_found(self, client):
        """POST /presets/<name>/apply returns 404 for missing preset"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.get_preset.return_value = None

            response = client.post('/api/presets/nonexistent/apply', json={
                'apply_to': 'capture'
            })

        assert response.status_code == 404
        data = response.get_json()
        assert 'not found' in data['error']

    def test_apply_preset_validates_apply_to_parameter(self, client):
        """POST /presets/<name>/apply validates apply_to parameter"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.get_preset.return_value = {'name': 'preset1', 'settings': {}}

            response = client.post('/api/presets/preset1/apply', json={
                'apply_to': 'invalid'
            })

        assert response.status_code == 400
        data = response.get_json()
        assert 'apply_to must be' in data['error']

    def test_apply_preset_validates_has_settings(self, client):
        """POST /presets/<name>/apply validates preset has settings"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.get_preset.return_value = {
                'name': 'empty_preset',
                'settings': {}
            }

            response = client.post('/api/presets/empty_preset/apply', json={
                'apply_to': 'capture'
            })

        assert response.status_code == 400
        data = response.get_json()
        assert 'no settings' in data['error']


class TestDeletePresetEndpoint:
    """Tests for DELETE /api/presets/<name> endpoint"""

    def test_delete_preset_success(self, client):
        """DELETE /presets/<name> deletes user preset"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.delete_preset.return_value = (True, "Preset deleted successfully")

            response = client.delete('/api/presets/my_preset')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        mock_pm.delete_preset.assert_called_once_with('my_preset')

    def test_delete_preset_not_found(self, client):
        """DELETE /presets/<name> returns 404 for missing preset"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.delete_preset.return_value = (False, "Preset not found")

            response = client.delete('/api/presets/nonexistent')

        assert response.status_code == 404
        data = response.get_json()
        assert 'not found' in data['error']

    def test_delete_preset_cannot_delete_builtin(self, client):
        """DELETE /presets/<name> returns 400 for built-in presets"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.delete_preset.return_value = (False, "Cannot delete built-in preset")

            response = client.delete('/api/presets/daylight')

        assert response.status_code == 400
        data = response.get_json()
        assert 'built-in' in data['error']

    def test_delete_preset_handles_error(self, client):
        """DELETE /presets/<name> returns 500 on error"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.delete_preset.side_effect = PermissionError("Cannot delete file")

            response = client.delete('/api/presets/my_preset')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data


class TestPresetValidation:
    """Validation and security tests"""

    def test_create_preset_strips_whitespace(self, client):
        """POST /presets strips whitespace from name and description"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.save_preset.return_value = (True, "Saved")

            response = client.post('/api/presets', json={
                'name': '  my_preset  ',
                'description': '  Description with spaces  ',
                'settings': {'camera': {}}
            })

        assert response.status_code == 200

        # Verify stripped values were passed
        call_args = mock_pm.save_preset.call_args
        assert call_args[0][0] == 'my_preset'  # name stripped
        assert call_args[0][2] == 'Description with spaces'  # description stripped

    def test_create_preset_defaults_workflow_to_both(self, client):
        """POST /presets defaults workflow to 'both'"""
        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.save_preset.return_value = (True, "Saved")

            response = client.post('/api/presets', json={
                'name': 'preset1',
                'settings': {'camera': {}}
                # No workflow specified
            })

        assert response.status_code == 200

        # Verify workflow defaulted to 'both'
        call_args = mock_pm.save_preset.call_args
        assert call_args[1]['workflow'] == 'both'

    def test_apply_preset_defaults_apply_to_capture(self, client, tmp_path, monkeypatch):
        """POST /presets/<name>/apply defaults to capture if not specified"""
        from Tests.conftest import patch_path_constant_everywhere

        camera_file = tmp_path / "camera_settings.csv"
        camera_file.write_text("SETTING,VALUE,DETAILS\n")
        patch_path_constant_everywhere(monkeypatch, 'CAMERA_SETTINGS_FILE', camera_file)

        with patch('routes.presets.preset_manager') as mock_pm:
            mock_pm.get_preset.return_value = {
                'name': 'preset1',
                'workflow': 'both',
                'settings': {'camera': {'Sharpness': '2.0'}}
            }

            # No apply_to specified
            response = client.post('/api/presets/preset1/apply', json={})

        assert response.status_code == 200
        data = response.get_json()
        assert data['applied_to'] == 'capture'  # Default
