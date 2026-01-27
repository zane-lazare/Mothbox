# Camera Settings Loading Cleanup

**Issues:** #383, #384
**Date:** 2026-01-27
**Status:** Planning

## Problems

### #384: False "Ignoring" Warnings

`load_camera_settings()` prints misleading warnings:
```
Warning: Unknown setting: HDR. Ignoring.
Warning: Unknown setting: AutoCalibration. Ignoring.
```

But these settings ARE used - they're popped from the dict later (lines 793-844).

**Root cause:** The function only recognizes Picamera2 camera controls in its if/elif chain. Application-level settings fall through to the `else` clause which prints "Ignoring" - but line 270 still adds them to the dict.

### #383: Duplicate Loading

Settings loaded twice:
- Line 784: Before autocalibration check
- Line 824: After potential calibration

Both calls print all debug messages and warnings, cluttering logs.

## Solution

### Fix #384: Recognize Application Settings

Add application-level settings to the known settings list:

```python
# Application settings (not Picamera2 controls)
APPLICATION_SETTINGS = {
    "Name",
    "HDR",
    "HDR_width",
    "AutoCalibration",
    "AutoCalibrationPeriod",
    "ImageFileType",
    "VerticalFlip",
}

# In load_camera_settings():
elif setting in APPLICATION_SETTINGS:
    pass  # Keep as string, used by application logic
else:
    print(f"Warning: Unknown setting: {setting}. Ignoring.")
```

### Fix #383: Load Once, Reload Conditionally

Only reload if calibration actually ran:

```python
camera_settings = load_camera_settings()
# ... autocalibration check ...

if recalibrated:
    # Calibration may have updated settings file
    camera_settings = load_camera_settings()
```

## Files Changed

- `5.x/TakePhoto.py` - Main fixes
- `4.x/TakePhoto.py` - Same fixes (identical code)

## Testing

1. Run TakePhoto.py, verify no false warnings
2. Verify logs show settings loaded once (unless calibration runs)
3. Verify all settings still work correctly
