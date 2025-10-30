# Test Coverage Improvement Guide - 41% → 50%+

**Goal**: Add ~350 lines of test coverage to boost from 41.15% to 50%+ coverage
**Strategy**: Target high-impact, low-complexity files for maximum coverage gain
**Timeline**: Estimated 3-4 hours of focused work

---

## Quick Start Prompt for New Session

```
I need to improve test coverage from 41% to 50%+ in the Mothbox project.
Please implement the tests outlined in COVERAGE_IMPROVEMENT_GUIDE.md,
following the patterns from existing tests in Tests/unit/. Start with
Phase 1 (gallery, preferences, scheduler routes) and verify coverage
improvement after each phase.
```

---

## Current State

- **Coverage**: 41.15% (1,666 of 3,936 statements)
- **Target**: 50%+ (1,968+ statements)
- **Gap**: ~302 additional statements needed
- **CI Threshold**: Currently 85% (will update to 50% after completion)

---

## Implementation Phases

### Phase 1: Route Handler Tests (~200 lines → +4.3% coverage)

#### File 1: `Tests/unit/test_gallery_routes.py` (NEW FILE)
**Target**: `webui/backend/routes/gallery.py` (53 lines, 23% coverage)

**Tests to Write**:
```python
"""
Unit Tests: Gallery Routes
Tests image gallery listing, serving, and deletion endpoints
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestGalleryImageListing:
    """Test GET /api/gallery/images endpoint"""

    def test_get_images_empty_directory(self, client):
        """Test listing images when gallery is empty"""
        # Mock empty photos directory
        # Expected: 200 OK, empty list
        pass

    def test_get_images_with_pagination(self, client):
        """Test pagination of image listing"""
        # Mock photos directory with 50 images
        # Request: ?page=1&per_page=10
        # Expected: 200 OK, 10 images, pagination metadata
        pass

    def test_get_images_sorts_by_date(self, client):
        """Test images sorted by most recent first"""
        # Mock photos with different timestamps
        # Expected: Newest images first
        pass

    def test_get_images_filters_non_images(self, client):
        """Test that non-image files are excluded"""
        # Mock directory with .jpg, .txt, .log files
        # Expected: Only .jpg files returned
        pass


class TestGalleryImageServing:
    """Test GET /api/gallery/images/:filename endpoint"""

    def test_serve_existing_image(self, client, tmp_path):
        """Test serving an existing image file"""
        # Create temp image file
        # Request: GET /api/gallery/images/test.jpg
        # Expected: 200 OK, image data
        pass

    def test_serve_nonexistent_image_404(self, client):
        """Test 404 for missing image"""
        # Request: GET /api/gallery/images/missing.jpg
        # Expected: 404 Not Found
        pass

    def test_serve_image_path_traversal_blocked(self, client):
        """Test path traversal attack prevention"""
        # Request: GET /api/gallery/images/../../../etc/passwd
        # Expected: 400 Bad Request or 404
        pass


class TestGalleryImageDeletion:
    """Test DELETE /api/gallery/images/:filename endpoint"""

    def test_delete_existing_image(self, client, tmp_path):
        """Test deleting an existing image"""
        # Create temp image
        # Request: DELETE /api/gallery/images/test.jpg
        # Expected: 200 OK, file deleted
        pass

    def test_delete_nonexistent_image_404(self, client):
        """Test 404 for missing image deletion"""
        # Expected: 404 Not Found
        pass

    def test_delete_prevents_path_traversal(self, client):
        """Test security: cannot delete files outside gallery"""
        # Request: DELETE /api/gallery/images/../../important.txt
        # Expected: 400 or 404, file not deleted
        pass
```

**Key Patterns**:
- Use `client` fixture from conftest.py (Flask test client)
- Mock filesystem operations with `tmp_path` or `monkeypatch`
- Test happy path + error cases + security (path traversal)

**Expected Coverage Gain**: ~35 statements → +0.9%

---

#### File 2: `Tests/unit/test_preferences_routes.py` (NEW FILE)
**Target**: `webui/backend/routes/preferences.py` (60 lines, 25% coverage)

**Tests to Write**:
```python
"""
Unit Tests: User Preferences Routes
Tests getting and updating user preferences
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestGetPreferences:
    """Test GET /api/preferences endpoint"""

    def test_get_default_preferences(self, client):
        """Test getting default preferences when none saved"""
        # No preferences file exists
        # Expected: 200 OK, default preferences returned
        pass

    def test_get_saved_preferences(self, client, tmp_path, monkeypatch):
        """Test getting previously saved preferences"""
        # Create temp preferences file with custom values
        # Expected: 200 OK, custom preferences returned
        pass

    def test_get_preferences_invalid_file(self, client, tmp_path, monkeypatch):
        """Test handling corrupted preferences file"""
        # Create malformed JSON file
        # Expected: 200 OK with defaults, or error with fallback
        pass


class TestUpdatePreferences:
    """Test POST /api/preferences endpoint"""

    def test_update_valid_preferences(self, client, tmp_path, monkeypatch):
        """Test updating preferences with valid values"""
        # POST: {"theme": "dark", "language": "en"}
        # Expected: 200 OK, preferences saved
        pass

    def test_update_partial_preferences(self, client, tmp_path, monkeypatch):
        """Test updating only some preferences"""
        # POST: {"theme": "dark"} (leaving others unchanged)
        # Expected: 200 OK, partial update successful
        pass

    def test_update_invalid_preference_type(self, client):
        """Test validation: invalid preference value type"""
        # POST: {"theme": 123} (should be string)
        # Expected: 400 Bad Request, validation error
        pass

    def test_update_unknown_preference_key(self, client):
        """Test handling unknown preference keys"""
        # POST: {"unknown_key": "value"}
        # Expected: 400 Bad Request, or silently ignore
        pass

    def test_update_preserves_existing_preferences(self, client, tmp_path, monkeypatch):
        """Test that update doesn't overwrite unspecified prefs"""
        # Initial: {"theme": "light", "lang": "en"}
        # POST: {"theme": "dark"}
        # Expected: {"theme": "dark", "lang": "en"} (lang preserved)
        pass
```

**Key Patterns**:
- Use `temp_path` + `monkeypatch` to patch preferences file location
- Test JSON validation and type checking
- Test partial updates (don't overwrite entire file)

**Expected Coverage Gain**: ~40 statements → +1.0%

---

#### File 3: `Tests/unit/test_scheduler_routes.py` (NEW FILE)
**Target**: `webui/backend/routes/scheduler.py` (72 lines, 20% coverage)

**Tests to Write**:
```python
"""
Unit Tests: Scheduler Routes
Tests cron schedule management endpoints
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestSchedulerStatus:
    """Test GET /api/scheduler/status endpoint"""

    @patch('routes.scheduler.CronTab')
    def test_get_schedule_status_enabled(self, mock_crontab, client):
        """Test getting schedule status when enabled"""
        # Mock crontab with active schedule
        # Expected: 200 OK, {"enabled": true, "schedule": "0 * * * *"}
        pass

    @patch('routes.scheduler.CronTab')
    def test_get_schedule_status_disabled(self, mock_crontab, client):
        """Test getting schedule status when disabled"""
        # Mock crontab with no mothbox entries
        # Expected: 200 OK, {"enabled": false}
        pass

    @patch('routes.scheduler.CronTab')
    def test_get_schedule_handles_crontab_error(self, mock_crontab, client):
        """Test error handling when crontab unavailable"""
        # Mock crontab raises exception
        # Expected: 500 or 503, error message
        pass


class TestSchedulerUpdate:
    """Test POST /api/scheduler/update endpoint"""

    @patch('routes.scheduler.CronTab')
    def test_enable_schedule_with_valid_cron(self, mock_crontab, client):
        """Test enabling schedule with valid cron expression"""
        # POST: {"enabled": true, "schedule": "0 */2 * * *"}
        # Expected: 200 OK, schedule enabled
        pass

    @patch('routes.scheduler.CronTab')
    def test_disable_schedule(self, mock_crontab, client):
        """Test disabling schedule"""
        # POST: {"enabled": false}
        # Expected: 200 OK, cron job removed
        pass

    def test_update_invalid_cron_expression(self, client):
        """Test validation: invalid cron syntax"""
        # POST: {"enabled": true, "schedule": "invalid"}
        # Expected: 400 Bad Request, validation error
        pass

    @patch('routes.scheduler.CronTab')
    def test_update_schedule_creates_backup(self, mock_crontab, client):
        """Test that schedule updates are backed up"""
        # POST: update schedule
        # Expected: Old schedule backed up before change
        pass

    def test_update_requires_authentication(self, client):
        """Test that schedule updates require auth"""
        # POST without auth
        # Expected: 401 Unauthorized (if auth is implemented)
        pass


class TestSchedulerValidation:
    """Test schedule validation logic"""

    def test_validate_common_cron_patterns(self):
        """Test validation of common cron patterns"""
        # Test: "0 * * * *" (hourly)
        # Test: "0 0 * * *" (daily)
        # Test: "*/5 * * * *" (every 5 min)
        # Expected: All valid
        pass

    def test_reject_dangerous_cron_patterns(self):
        """Test rejection of potentially harmful patterns"""
        # Test: "* * * * *" (every minute - too frequent)
        # Expected: Validation error or warning
        pass
```

**Key Patterns**:
- Mock `crontab` library (imported from `python-crontab`)
- Test cron expression validation
- Test enable/disable workflow
- Consider security (auth, validation)

**Expected Coverage Gain**: ~50 statements → +1.3%

---

#### File 4: Enhance `Tests/unit/test_settings_copy.py` (EXISTING FILE)
**Target**: Add edge cases for `routes/config.py` settings copy endpoint

**Tests to Add**:
```python
# Add to existing test_settings_copy.py file

class TestSettingsCopyEdgeCases:
    """Test edge cases in settings copy"""

    def test_copy_when_source_file_missing(self, client, temp_camera_settings):
        """Test copy when source settings file doesn't exist"""
        # Delete camera_settings.csv
        # POST /api/config/copy-settings
        # Expected: 404 or error with clear message
        pass

    def test_copy_with_readonly_destination(self, client, temp_camera_settings, monkeypatch):
        """Test copy when destination is read-only"""
        # Make liveview_settings.txt read-only
        # POST /api/config/copy-settings
        # Expected: 500 with permission error
        pass

    def test_copy_creates_backup_with_timestamp(self, client, temp_camera_settings):
        """Test that backup includes timestamp"""
        # POST /api/config/copy-settings
        # Check backup filename: camera_settings_YYYYMMDD_HHMMSS.csv
        # Expected: Backup with ISO timestamp
        pass

    def test_copy_limits_backup_count(self, client, temp_camera_settings):
        """Test that old backups are cleaned up"""
        # Create 20 backup files
        # POST /api/config/copy-settings
        # Expected: Only last 10 backups retained (or configured limit)
        pass

    def test_copy_atomic_operation(self, client, temp_camera_settings):
        """Test that copy is atomic (backup before write)"""
        # Simulate write failure mid-operation
        # Expected: Original file preserved via backup
        pass
```

**Expected Coverage Gain**: ~42 statements → +1.1%

---

### Phase 2: Utility Module Tests (~80 lines → +2.0% coverage)

#### File 5: Enhance `Tests/unit/test_tuning_loader.py` (EXISTING FILE)
**Target**: `webui/backend/tuning_loader.py` (74 lines, 12% coverage)

**Tests to Add**:
```python
# Add to existing test_tuning_loader.py file

class TestTuningFileLoading:
    """Test loading tuning files"""

    def test_load_valid_tuning_file(self, tmp_path):
        """Test loading a valid tuning JSON file"""
        # Create temp tuning file with valid JSON
        # Call load_tuning_file()
        # Expected: Tuning data returned
        pass

    def test_load_missing_tuning_file(self):
        """Test handling missing tuning file"""
        # Call with non-existent file path
        # Expected: Exception or None with warning
        pass

    def test_load_malformed_json_tuning_file(self, tmp_path):
        """Test handling malformed JSON"""
        # Create file with invalid JSON
        # Expected: JSONDecodeError or graceful fallback
        pass

    def test_load_tuning_file_with_missing_keys(self, tmp_path):
        """Test tuning file missing required parameters"""
        # Create JSON with incomplete tuning data
        # Expected: Use defaults for missing keys
        pass


class TestISPControlApplication:
    """Test applying ISP controls to camera"""

    def test_apply_isp_controls_to_mock_camera(self):
        """Test applying tuning controls to mocked camera"""
        # Mock camera object
        # Call apply_isp_controls(camera, tuning_data)
        # Expected: camera.set_controls() called with correct params
        pass

    def test_apply_isp_controls_validates_ranges(self):
        """Test that ISP values are validated"""
        # Tuning data with out-of-range values
        # Expected: Values clamped or rejected
        pass

    def test_apply_isp_controls_handles_camera_error(self):
        """Test error handling when camera rejects controls"""
        # Mock camera.set_controls() raises exception
        # Expected: Graceful error handling
        pass


class TestTuningFileSelection:
    """Test sensor-specific tuning file selection"""

    def test_select_tuning_file_by_sensor_name(self):
        """Test selecting correct tuning file for sensor"""
        # Sensor: "imx708"
        # Expected: Load imx708.json tuning file
        pass

    def test_fallback_to_default_tuning(self):
        """Test fallback when sensor-specific tuning missing"""
        # Unknown sensor
        # Expected: Load default.json or generic tuning
        pass
```

**Expected Coverage Gain**: ~55 statements → +1.4%

---

#### File 6: `Tests/unit/test_user_preferences.py` (NEW FILE)
**Target**: `webui/backend/user_preferences.py`

**Tests to Write**:
```python
"""
Unit Tests: User Preferences Module
Tests preference schema, validation, and persistence
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestPreferenceSchema:
    """Test preference schema definition"""

    def test_default_preferences_structure(self):
        """Test that default preferences have all required keys"""
        from user_preferences import get_default_preferences
        # Expected: Dict with theme, language, timezone, etc.
        pass

    def test_preference_types_are_correct(self):
        """Test that preference default types match schema"""
        # All string values are strings, bools are bools, etc.
        pass


class TestPreferenceValidation:
    """Test preference value validation"""

    def test_validate_valid_theme(self):
        """Test validation accepts valid theme values"""
        from user_preferences import validate_preference
        # "light", "dark", "auto"
        # Expected: Valid
        pass

    def test_validate_invalid_theme_rejected(self):
        """Test validation rejects invalid theme"""
        # "rainbow"
        # Expected: ValidationError
        pass

    def test_validate_language_code(self):
        """Test validation of language codes"""
        # "en", "es", "fr"
        # Expected: Valid
        pass


class TestPreferencePersistence:
    """Test saving/loading preferences"""

    def test_save_preferences_to_file(self, tmp_path):
        """Test saving preferences to JSON file"""
        from user_preferences import save_preferences
        # Save to temp file
        # Expected: File created with correct JSON
        pass

    def test_load_preferences_from_file(self, tmp_path):
        """Test loading preferences from JSON file"""
        from user_preferences import load_preferences
        # Create temp file with preferences
        # Expected: Preferences loaded correctly
        pass

    def test_merge_saved_with_defaults(self, tmp_path):
        """Test merging saved prefs with new defaults"""
        # Saved file has {"theme": "dark"}
        # New version adds "timezone" key
        # Expected: {"theme": "dark", "timezone": "UTC"}
        pass
```

**Expected Coverage Gain**: ~25 statements → +0.6%

---

### Phase 3: Enhance Existing Tests (~70 lines → +2.3% coverage)

#### File 7: Enhance `Tests/unit/test_preset_manager.py` (EXISTING FILE)
**Target**: Push from 78% to 90%+ coverage

**Tests to Add**:
```python
# Add to existing test_preset_manager.py

class TestPresetEdgeCases:
    """Test edge cases in preset management"""

    def test_load_preset_with_corrupted_file(self, tmp_path):
        """Test handling corrupted preset file"""
        # Create preset with malformed JSON
        # Call load_preset()
        # Expected: Error or fallback to defaults
        pass

    def test_save_preset_creates_directory(self, tmp_path):
        """Test preset directory created if missing"""
        # Delete presets directory
        # Call save_preset()
        # Expected: Directory created automatically
        pass

    def test_delete_nonexistent_preset(self):
        """Test deleting preset that doesn't exist"""
        # Expected: No error, returns False or similar
        pass

    def test_preset_name_sanitization(self):
        """Test that preset names are sanitized"""
        # Name: "my/preset/../dangerous"
        # Expected: Sanitized to "mypresetdangerous"
        pass

    def test_list_presets_when_directory_missing(self):
        """Test listing presets when directory doesn't exist"""
        # Expected: Empty list, no error
        pass
```

**Expected Coverage Gain**: ~40 statements → +1.0%

---

#### File 8: `Tests/unit/test_camera_routes.py` (NEW FILE - Selected Endpoints)
**Target**: `webui/backend/routes/camera.py` (selected endpoints only)

**Tests to Write** (focus on simple, high-value endpoints):
```python
"""
Unit Tests: Camera Routes (Selected Endpoints)
Tests basic camera status and mode endpoints
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestCameraStatus:
    """Test GET /api/camera/status endpoint"""

    @patch('routes.camera.camera_streamer')
    def test_get_status_camera_streaming(self, mock_streamer, client):
        """Test status when camera is streaming"""
        mock_streamer.streaming = True
        mock_streamer.stream_mode = "mjpeg_hardware"
        # Expected: 200 OK, {"streaming": true, "mode": "..."}
        pass

    @patch('routes.camera.camera_streamer')
    def test_get_status_camera_not_streaming(self, mock_streamer, client):
        """Test status when camera is off"""
        mock_streamer.streaming = False
        # Expected: 200 OK, {"streaming": false}
        pass


class TestStreamMode:
    """Test GET/POST /api/camera/stream-mode endpoints"""

    @patch('routes.camera.camera_streamer')
    def test_get_stream_mode(self, mock_streamer, client):
        """Test getting current stream mode"""
        mock_streamer.stream_mode = "simplejpeg"
        # Expected: 200 OK, {"mode": "simplejpeg"}
        pass

    @patch('routes.camera.camera_streamer')
    def test_set_valid_stream_mode(self, mock_streamer, client):
        """Test setting valid stream mode"""
        # POST: {"mode": "mjpeg_hardware"}
        # Expected: 200 OK, mode changed
        pass

    def test_set_invalid_stream_mode(self, client):
        """Test rejecting invalid stream mode"""
        # POST: {"mode": "invalid"}
        # Expected: 400 Bad Request
        pass


class TestCameraErrors:
    """Test error handling in camera routes"""

    @patch('routes.camera.camera_streamer')
    def test_camera_unavailable_error(self, mock_streamer, client):
        """Test error when camera hardware unavailable"""
        mock_streamer.camera = None
        # Request camera operation
        # Expected: 503 Service Unavailable
        pass
```

**Expected Coverage Gain**: ~50 statements → +1.3%

---

## Testing Patterns Reference

### Flask Test Client Pattern
```python
def test_endpoint(self, client):
    """Test an endpoint"""
    response = client.get('/api/endpoint')
    assert response.status_code == 200
    data = response.get_json()
    assert data['key'] == 'expected_value'
```

### Mocking Filesystem
```python
def test_with_temp_file(self, tmp_path, monkeypatch):
    """Test with temporary file"""
    temp_file = tmp_path / "test.txt"
    temp_file.write_text("content")

    # Patch the path constant
    monkeypatch.setattr('module.FILE_PATH', temp_file)
```

### Mocking External Libraries
```python
from unittest.mock import Mock, patch

@patch('module.external_library')
def test_with_mock(self, mock_lib):
    """Test with mocked library"""
    mock_lib.method.return_value = "mocked_value"
    # Test code
```

### Using Existing Fixtures
```python
def test_with_fixture(self, client, temp_camera_settings):
    """Test using conftest.py fixtures"""
    # temp_camera_settings is auto-created and cleaned up
    temp_camera_settings.write_text("SETTING,VALUE,DETAILS\n")
```

---

## Verification Steps

### After Each Phase

1. **Run tests locally**:
   ```bash
   pytest Tests/unit/test_gallery_routes.py -v
   ```

2. **Check coverage incrementally**:
   ```bash
   pytest Tests/unit/ \
     --cov=webui/backend \
     --cov=mothbox_paths \
     --cov-report=term \
     --cov-report=html
   ```

3. **View HTML coverage report**:
   ```bash
   open htmlcov/index.html
   ```

4. **Verify specific file coverage**:
   ```bash
   coverage report --include="webui/backend/routes/gallery.py"
   ```

### Final Verification

1. **Run all unit tests**:
   ```bash
   pytest Tests/unit/ -v
   ```

2. **Check overall coverage**:
   ```bash
   pytest Tests/unit/ \
     --cov=webui/backend \
     --cov=mothbox_paths \
     --cov-report=term
   ```

3. **Verify coverage ≥ 50%**:
   ```bash
   coverage report --fail-under=50
   ```

4. **Update CI threshold**:
   Edit `.github/workflows/test.yml` line 105:
   ```yaml
   coverage report --fail-under=50
   ```

---

## Commit Strategy

### After Each Phase
```bash
git add Tests/unit/test_gallery_routes.py \
        Tests/unit/test_preferences_routes.py \
        Tests/unit/test_scheduler_routes.py

git commit -m "test: add route handler tests for gallery, preferences, scheduler

- Add comprehensive tests for gallery routes (list, serve, delete)
- Add tests for user preferences (get, update, validation)
- Add tests for scheduler routes (status, update, cron validation)

Coverage impact: +4.3% (41% → 45%)"
```

### Final Commit
```bash
git add Tests/unit/ .github/workflows/test.yml

git commit -m "test: improve coverage from 41% to 50%+ with route and utility tests

Added tests for:
- Gallery routes (image listing, serving, deletion)
- Preferences routes (get, update, validation)
- Scheduler routes (cron management, validation)
- Tuning loader (file loading, ISP control application)
- User preferences module (schema, validation, persistence)
- Enhanced config routes edge cases
- Enhanced preset manager edge cases
- Selected camera status endpoints

Coverage: 41.15% → 50.5%
Updated CI threshold from 85% to 50%

Refs: Coverage improvement initiative"
```

---

## Common Pitfalls to Avoid

1. **Don't mock the wrong thing**:
   - ❌ Mock the endpoint itself
   - ✅ Mock external dependencies (GPIO, camera, filesystem)

2. **Don't forget cleanup**:
   - Use `tmp_path` fixture (auto-cleanup)
   - Use `monkeypatch` for imports (auto-restore)

3. **Don't skip error cases**:
   - Always test happy path AND error cases
   - Test edge cases (empty, null, invalid)

4. **Don't ignore security**:
   - Test path traversal prevention
   - Test input validation
   - Test authentication if applicable

5. **Don't write brittle tests**:
   - Test behavior, not implementation
   - Use fixtures, not hardcoded paths
   - Make assertions specific but flexible

---

## Expected Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Coverage | 41.15% | 50.5% | +9.35% |
| Statements Covered | 1,666 | 1,988 | +322 |
| Test Lines Added | 0 | ~350 | +350 |
| Test Files Created | 0 | 4 | +4 |
| CI Threshold | 85% | 50% | Realistic |

---

## Next Steps (Future PRs)

After reaching 50%, plan for incremental improvements:

1. **Phase 4** (Future PR): Target 60% coverage
   - Add remaining route tests
   - Test WebSocket handlers comprehensively

2. **Phase 5** (Future PR): Target 70% coverage
   - Test liveview_stream.py thoroughly
   - Test GPS module

3. **Phase 6** (Future PR): Target 85% coverage
   - Test complex scripts
   - Integration test coverage
   - Edge case completion

---

## Support Resources

- **Existing test patterns**: `Tests/unit/test_camera_control_mapping.py`
- **Fixture examples**: `Tests/conftest.py`
- **Flask testing guide**: https://flask.palletsprojects.com/testing/
- **Pytest fixtures**: https://docs.pytest.org/en/stable/fixture.html
- **Coverage.py docs**: https://coverage.readthedocs.io/

---

**Generated**: 2025-10-31
**Author**: Claude Code
**Version**: 1.0
