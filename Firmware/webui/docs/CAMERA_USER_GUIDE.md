# Camera User Guide

This guide explains how to use the Mothbox camera system through the web interface.

## Overview

The Mothbox camera system provides two main features:
1. **Live View**: Real-time camera preview with adjustable settings
2. **Photo Capture**: High-resolution photo capture for monitoring

## Camera Page Interface

Access the camera page at: `http://[mothbox-ip]:5000/camera`

### Layout

The camera page displays:
- **Left Side**: Camera controls (exposure, focus, image quality)
- **Center**: Live camera preview (real-time video stream)
- **Right Side**: Capture buttons and status information

---

## Live View Preview

The live view shows a real-time preview of what the camera sees at approximately 10 frames per second.

**Features**:
- Real-time preview (~1024x768 resolution)
- Adjustable camera controls
- Visual feedback for focus, exposure, etc.
- WebSocket-based streaming (low latency)

**Connection Status**:
- **Green indicator**: Camera connected and streaming
- **Red indicator**: Camera disconnected or unavailable

---

## Camera Controls

### Exposure Controls

**Exposure Time**: Controls how long the camera sensor is exposed to light
- Range: 100µs to 1,000,000µs (1 second)
- Higher values = brighter images but more motion blur
- Lower values = darker images but sharper motion
- **Use Case**: Adjust for lighting conditions (increase at night, decrease in bright light)

**Gain (ISO)**: Controls sensor sensitivity to light
- Range: 1.0x to 16.0x
- Higher values = brighter images but more noise
- Lower values = cleaner images but may be darker
- **Use Case**: Increase gain in low light when exposure time is already high

**Auto Exposure (AE)**: Automatically adjusts exposure and gain
- Enable for automatic brightness control
- Disable for manual control
- **Use Case**: Enable for variable lighting, disable for consistent manual settings

### Focus Controls

**Autofocus (AF) Mode**:
- **Manual (0)**: Fixed focus position (set lens position manually)
- **Auto (1)**: Single autofocus trigger (focus once when clicked)
- **Continuous (2)**: Continuously adjusts focus (best for moving subjects)

**Lens Position** (Manual mode only):
- Range: 0.0 (infinity) to 10.0 (close)
- Measured in diopters
- **Use Case**: Set fixed focus distance for consistent captures

**AF Range**:
- **Normal**: General purpose focusing
- **Macro**: Optimized for close-up subjects
- **Full**: Scans full focus range (slower but more accurate)

**AF Speed**:
- **Normal**: Standard focusing speed
- **Fast**: Faster focusing (may be less accurate)

### White Balance

**Auto White Balance (AWB)**: Automatically adjusts color temperature
- Enable for automatic color correction
- Disable for manual control via color gains

**Color Gains** (Manual mode only):
- **Red Gain**: 0.0 to 8.0
- **Blue Gain**: 0.0 to 8.0
- **Use Case**: Manually correct color cast (warmer/cooler tones)

### Image Quality

**Sharpness**: Controls edge enhancement
- Range: 0.0 (soft) to 2.0 (very sharp)
- Default: 1.0
- **Use Case**: Increase for sharper insect details, decrease for softer look

**Brightness**: Adjusts overall image brightness
- Range: -1.0 (darker) to 1.0 (brighter)
- Default: 0.0
- **Use Case**: Fine-tune brightness without changing exposure

**Contrast**: Controls difference between light and dark areas
- Range: 0.0 (low contrast) to 2.0 (high contrast)
- Default: 1.0
- **Use Case**: Increase for more dramatic images, decrease for softer look

**Saturation**: Controls color intensity
- Range: 0.0 (grayscale) to 2.0 (very saturated)
- Default: 1.0
- **Use Case**: Adjust for accurate color reproduction or artistic effect

---

## Capture Buttons

### Test Photo (4K)

**Location**: Test Capture overlay (bottom center)

**Purpose**: Capture a 4K test photo using **current live view settings**

**When to Use**:
- Testing focus adjustments before production capture
- Verifying exposure settings at full resolution
- Checking image quality with current controls

**Process**:
1. Adjust camera controls in live view
2. Click "Test Photo" button
3. Wait for capture to complete (~3-5 seconds)
4. Photo saved to `test_captures/` directory
5. View success message with metadata (exposure, gain, focus)

**Filename Format**: `test_YYYY_MM_DD__HH_MM_SS_[serial].jpg`

**Resolution**: 3840x2160 (4K)

**Settings Used**: Current live view controls (NOT saved settings file)

---

### Instant Capture

**Location**: Test Capture overlay (below Test Photo button)

**Purpose**: Quick snapshot with full EXIF metadata using **current live view settings**

**When to Use**:
- Quick documentation snapshot
- Capturing current camera view for troubleshooting
- Testing GPS EXIF tagging
- Creating reference images

**Process**:
1. Adjust camera view and settings in live view
2. Click "Instant Capture" button
3. Wait for capture to complete (~3-5 seconds)
4. Photo saved to `test_captures/` directory with full metadata
5. View success message with filename

**Filename Format**: `instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg`

**Resolution**: 3840x2160 (4K)

**Settings Used**: Current live view controls (NOT saved settings file)

**EXIF Metadata**: Full camera metadata embedded (exposure, gain, focus, etc.)

**GPS Tagging**: GPS coordinates embedded in EXIF if GPS fix available

---

### Capture Photo (Production)

**Location**: Capture Control overlay (bottom right)

**Purpose**: Production-quality capture using **saved settings from file**

**When to Use**:
- Scheduled monitoring captures
- Production moth monitoring photos
- Creating image datasets for research

**Process**:
1. Click "Capture Photo" button
2. Wait for capture to complete (~5 seconds single, ~30 seconds for bracketed)
3. Photo(s) saved to main photos directory
4. View success message with filename

**Filename Format**: `YYYY_MM_DD__HH_MM_SS_[serial].jpg`

**Resolution**: Up to 9152x6944 (64MP) depending on camera model

**Settings Used**: Saved settings from `camera_settings.csv` file (NOT live view)

**Features**:
- HDR mode (if enabled in settings)
- Focus bracketing (if enabled - captures 5 images at different focus distances)
- GPS EXIF tagging (if GPS available)
- Full resolution capture

---

## Common Workflows

### Workflow 1: Adjusting Focus

**Goal**: Get sharp focus on subject using live view feedback

**Steps**:
1. Open Camera page
2. Enable live view (should auto-connect)
3. Set AF Mode to "Manual" (0)
4. Adjust "Lens Position" slider while watching preview
   - Move slider right for closer focus
   - Move slider left for distant focus
5. When focus looks good, click "Test Photo"
6. Review captured 4K image to verify sharpness
7. Adjust and re-test if needed
8. Once satisfied, click "Capture Photo" for production capture

**Tip**: Use "Sharpness" control to enhance edge detail in preview

---

### Workflow 2: Night Photography Setup

**Goal**: Optimize settings for low-light moth photography

**Steps**:
1. Open Camera page at dusk/night
2. Enable live view
3. Disable Auto Exposure (uncheck AE Enable)
4. Increase Exposure Time to 500,000µs (0.5 seconds)
5. Increase Gain to 8.0x
6. Watch preview - should be brighter
7. Adjust exposure/gain until preview looks good
8. Click "Test Photo" to verify at full resolution
9. Fine-tune settings based on test photo
10. Click "Capture Photo" for production capture

**Warning**: High exposure times may show motion blur if insects are moving

---

### Workflow 3: Quick Documentation

**Goal**: Capture current camera view for documentation/troubleshooting

**Steps**:
1. Open Camera page
2. Frame subject in live view
3. Adjust brightness/exposure if needed
4. Click "Instant Capture"
5. Photo saved to test_captures/ with full metadata
6. Download photo from Gallery page if needed

**Use Cases**:
- Documenting camera placement
- Troubleshooting image quality issues
- Sharing current view with collaborators
- Creating reference images for setup

---

### Workflow 4: Comparing Settings

**Goal**: Compare different camera settings to find optimal configuration

**Steps**:
1. Set Settings A in live view (e.g., Sharpness=1.0, Contrast=1.0)
2. Click "Test Photo"
3. Note filename (e.g., test_2025_01_15__14_30_45_ABC123.jpg)
4. Change to Settings B (e.g., Sharpness=2.0, Contrast=1.5)
5. Click "Test Photo"
6. Note filename (e.g., test_2025_01_15__14_31_12_DEF456.jpg)
7. Go to Gallery page
8. Compare the two test images side-by-side
9. Choose best settings and apply to saved settings

---

## Focus Strategy

The Focus Strategy card on the Settings page provides a unified interface for configuring how the camera focuses. It combines AutoCalibration and Focus Mode into a single dropdown.

### Focus Modes

| Mode | Best For | How It Works |
|------|----------|--------------|
| **Auto-Calibrate** | Unattended operation | Periodically runs autofocus and saves the result. Uses calibrated position for captures. |
| **Manual Focus** | Fixed camera-to-subject distance | You set an exact focus distance in diopters (0=far, 10=near). |
| **Autofocus (Single)** | Varying distances | Runs autofocus once before each capture. |
| **Autofocus (Continuous)** | Moving subjects | Continuously adjusts focus. Uses more power. |

### When to Use Which Mode

- **Most moth traps**: Use **Auto-Calibrate** with a 600-second interval. The camera will periodically re-optimize focus for changing conditions.
- **Fixed setup on a flat surface**: Use **Manual Focus** at the known distance to your target.
- **Variable distances**: Use **Autofocus (Single)** for a focus check before each capture.
- **Live monitoring**: Use **Autofocus (Continuous)** when viewing the live preview and wanting real-time focus tracking.

### Troubleshooting

- **Blurry photos in Auto-Calibrate**: Try a shorter calibration interval (e.g., 60 seconds). The flash must work for calibration to succeed.
- **Focus hunting in Continuous mode**: Switch to Single or reduce Focus Speed to Normal (Accurate).
- **Macro subjects out of focus**: Set Focus Range to "Macro (10cm - 50cm)" in AF modes, or use Manual Focus at 7-10 diopters.

---

## Settings: Test vs Production

### Test Photo / Instant Capture

**Settings Source**: Current live view controls (real-time adjustments)

**Use For**:
- Testing and experimenting with settings
- Quick snapshots
- Verifying settings before production
- Documentation

**Saved To**: `test_captures/` subdirectory

**Resolution**: 3840x2160 (4K)

### Capture Photo (Production)

**Settings Source**: Saved settings from `camera_settings.csv` file

**Use For**:
- Production monitoring
- Scheduled captures
- Research datasets
- Consistent automated captures

**Saved To**: Main photos directory

**Resolution**: Full camera resolution (up to 64MP)

**Important**: Test captures do NOT affect saved settings file. To update production settings, use the Settings page.

---

## Troubleshooting

### Live View Not Connecting

**Symptoms**: Red connection indicator, no video preview

**Solutions**:
1. Refresh the page (F5)
2. Check that no other process is using the camera
3. Restart the Mothbox web service: `sudo systemctl restart mothbox-webui`
4. Check camera cable connections
5. View logs: `sudo journalctl -u mothbox-webui -f`

### Test Photo Capture Fails

**Symptoms**: Error message when clicking "Test Photo"

**Solutions**:
1. Ensure live view is connected (green indicator)
2. Check that test_captures/ directory exists and is writable
3. Check available disk space: `df -h`
4. Try "Instant Capture" instead - if it works, issue is specific to test capture
5. Check logs for detailed error

### Images Too Dark/Bright

**Symptoms**: Photos are under/over-exposed

**Solutions for Dark Images**:
1. Increase Exposure Time slider
2. Increase Gain slider
3. Enable Auto Exposure (AE Enable checkbox)
4. Check that attract lights are on (for night photography)

**Solutions for Bright Images**:
1. Decrease Exposure Time slider
2. Decrease Gain slider
3. Enable Auto Exposure (AE Enable checkbox)
4. Adjust Brightness slider down

### Focus Is Blurry

**Symptoms**: Images lack sharpness, subject is out of focus

**Solutions**:
1. Set AF Mode to Manual
2. Adjust Lens Position slider while watching preview
3. Increase Sharpness slider for edge enhancement (won't fix out-of-focus, but helps)
4. Use "Test Photo" to verify focus at full resolution
5. Ensure subject is within camera's focus range
6. Try AF Mode "Auto" and trigger autofocus
7. Clean camera lens if dirty

### GPS Not Embedding in Photos

**Symptoms**: EXIF shows no GPS data

**Solutions**:
1. Check GPS status on Dashboard page
2. Verify GPS has valid fix (at least 4 satellites)
3. Wait 30-60 seconds after powering on for GPS to acquire fix
4. Check GPS antenna placement (needs clear view of sky)
5. View GPS config on Settings page

---

## Tips and Best Practices

### General Photography

1. **Use Test Photo liberally** - It's free and helps verify settings
2. **Enable Auto Exposure initially** - Let camera find good starting point
3. **Fine-tune manually** - Disable AE and adjust exposure/gain for consistency
4. **Check focus regularly** - Focus can drift, especially with temperature changes
5. **Save presets** - Use preset system to save good settings configurations

### Night Photography

1. **Increase exposure time** - Start at 200,000µs (0.2s) and adjust
2. **Increase gain** - Start at 4.0x and increase if still too dark
3. **Disable auto exposure** - Prevents settings from changing between captures
4. **Use manual focus** - Set focus once and keep it consistent
5. **Test before dark** - Set up and test settings during dusk for easier adjustment

### Insect Monitoring

1. **Use sufficient sharpness** - Set to 1.5-2.0 for detail capture
2. **Adjust contrast** - Increase to 1.2-1.5 for better subject separation
3. **Set focus for expected distance** - Focus on where insects will be
4. **Use consistent settings** - Avoid changing settings mid-monitoring session
5. **Enable GPS tagging** - Important for location-based analysis

### Troubleshooting

1. **Use Instant Capture for debugging** - Quick way to capture current state
2. **Compare test photos** - Capture before/after to verify changes
3. **Check metadata** - Review EXIF to see actual settings used
4. **Monitor logs** - Use Dashboard logs for error messages
5. **Document settings** - Keep notes on successful configurations

---

## Keyboard Shortcuts

*(Future feature - coming soon)*

---

## See Also

- **Camera API Documentation**: `webui/docs/CAMERA_API.md`
- **GPS EXIF Tagging**: `webui/docs/GPS_EXIF_USER_GUIDE.md`
- **Settings Management**: `docs/SETTINGS_GUIDE.md` *(coming soon)*
- **Gallery Management**: Web UI Gallery page
