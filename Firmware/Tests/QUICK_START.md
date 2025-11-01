# Quick Start: Continue Phase 2 Testing (Issue #78)

**Branch**: `feature/issue-13-phase1-hardware-config-tests`
**Latest Commits**: `8a3c8a7` (Phase 2A & 2B), `eb96819` (Phase 2C structure)

## Status Summary

✅ **Completed**: 121 tests, 85%+ coverage on config/gpio/gps routes
🚧 **In Progress**: Presets tests (25 tests created, need mocking fix)
⏳ **Pending**: Camera infrastructure + camera routes (~90 hours remaining)

## Next Task: Fix Presets Tests

**File**: `Tests/unit/test_presets_routes.py`
**Problem**: `preset_manager` instantiated at module level (routes/presets.py:21)
**Goal**: 60-70% coverage on presets.py (332 lines)
**Current**: 12.50% coverage (1/25 tests passing)

### Solution Approaches

1. **Patch before import** using sys.modules manipulation
2. **Monkeypatch instance** to replace module-level object
3. **Refactor** (long-term): make preset_manager lazy/injectable

### Test Coverage

Run: `python3 -m pytest Tests/unit/test_presets_routes.py -v --cov=routes.presets --cov-report=term-missing`

## After Presets: Camera Infrastructure (Phase 2D)

Build 5 fixtures in `Tests/conftest.py`:
1. `mock_picamera2()` - Camera hardware mock
2. `mock_subprocess_run()` - TakePhoto.py subprocess factory
3. `mock_socketio_emit()` - WebSocket emission tracker
4. `temp_photos_dir()` - Isolated photo directory
5. `mock_camera_streamer()` - LiveViewStreamer mock

## Reference Examples

- **GPS tests**: `Tests/unit/test_gps_routes.py` (46 tests, 85.81%)
- **Config tests**: `Tests/unit/test_config_routes.py` (41 tests, 85.36%)
- **Fixtures**: `Tests/conftest.py` (lines 190-210 for blueprint setup)

## Testing Pattern

```python
# Standard test structure
def test_endpoint_name(self, client, temp_file_fixture):
    """Brief description"""
    # Setup: Create test data

    # Execute: Call endpoint via test client
    with patch('routes.module.dependency') as mock_dep:
        mock_dep.return_value = expected_value
        response = client.get('/api/endpoint')

    # Assert: Verify response and side effects
    assert response.status_code == 200
    data = response.get_json()
    assert data['key'] == expected_value
```

## Quick Commands

```bash
# Run presets tests
pytest Tests/unit/test_presets_routes.py -v

# Run all tests
pytest Tests/unit/ -v

# Coverage for specific module
pytest Tests/unit/test_presets_routes.py --cov=routes.presets --cov-report=term-missing
```
