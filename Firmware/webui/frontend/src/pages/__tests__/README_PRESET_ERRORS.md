# Preset Error Notification Integration Tests (PR #72)

## Overview

These integration tests verify that preset initialization failures show proper toast error notifications to users in Camera.jsx and Settings.jsx.

## Test Files

- `Camera.preset-errors.test.jsx` - Tests Camera page preset error notifications
- `Settings.preset-errors.test.jsx` - Tests Settings page preset error notifications with fallback logic

## Requirements

### Hardware & Environment
- **Raspberry Pi** with camera hardware
- **Backend running** at `http://localhost:5000`
- **Node.js** and npm installed
- Frontend dependencies installed (`npm install`)

### Backend Setup
1. Start the Mothbox backend:
   ```bash
   cd /home/zane/projects/Mothbox/Firmware
   python3 webui/backend/app.py
   ```

2. Ensure test presets exist in database
3. Configure invalid preset references in preferences to trigger errors

## Running Tests

### Via run_tests.sh (Recommended)
```bash
cd /home/zane/projects/Mothbox/Firmware
./Tests/run_tests.sh preset-errors
```

### Direct vitest
```bash
cd /home/zane/projects/Mothbox/Firmware/webui/frontend
npm test -- --run preset-errors
```

### With coverage
```bash
cd /home/zane/projects/Mothbox/Firmware/webui/frontend
npm run test:coverage -- preset-errors
```

## What The Tests Verify

### Camera.jsx Tests
1. ✅ Toast error appears when photo preset fails to load
2. ✅ Error messages use preset display names (not internal names)
3. ✅ API error messages are extracted and shown to user
4. ✅ Optional chaining prevents crashes when presetsData is null
5. ✅ Liveview preset errors are properly handled

### Settings.jsx Tests
1. ✅ Toast error when photo preset fails AND fallback also fails
2. ✅ Display names are used in all error messages
3. ✅ Toast shown when no fallback preset is available
4. ✅ Liveview preset errors with fallback logic work correctly

## Test Approach

These are **integration tests** that:
- Use real backend API endpoints (not mocked)
- Only mock `toast` to capture error notification calls
- Verify actual user-facing error messages
- Test in realistic failure scenarios

## Triggering Test Scenarios

To test specific error paths, you can:

### 1. Invalid Preset in Preferences
Edit preferences to reference non-existent preset:
```bash
# Via API or database
curl -X POST http://localhost:5000/api/preferences \
  -H "Content-Type: application/json" \
  -d '{"default_capture_preset": "nonexistent_preset"}'
```

### 2. Remove Fallback Preset
Delete or rename the "balanced" preset to test "no fallback" scenario

### 3. Invalid Workflow
Create preset with mismatched workflow to trigger validation errors

## Expected Behavior

When tests run successfully, you should see:
- All tests pass (green checkmarks)
- Toast error messages captured and verified
- No crashes or unhandled exceptions
- Proper error formatting with display names

## Troubleshooting

### Backend Not Running
```
Error: Failed to fetch
```
**Solution**: Start backend with `python3 webui/backend/app.py`

### No Preset Errors Triggered
Tests pass but no toast errors captured.
**Solution**: Configure invalid presets in preferences to trigger test scenarios

### Import Errors
```
Cannot find module '../Camera'
```
**Solution**: Run `npm install` to ensure all dependencies are installed

## Integration with CI/CD

These tests are designed for Pi hardware testing:
- Run after deploying to Pi
- Verify error handling works in production environment
- Part of manual verification before release

## Related Files

- **Implementation**: `src/pages/Camera.jsx` (lines 206-209, 962-970)
- **Implementation**: `src/pages/Settings.jsx` (lines 314-328, 360-374)
- **PR**: #72
- **Issue**: #63

## Maintenance

When updating preset error handling:
1. Update implementation in Camera.jsx or Settings.jsx
2. Run tests to verify error messages still appear
3. Update tests if error message format changes
4. Document any new test scenarios needed
