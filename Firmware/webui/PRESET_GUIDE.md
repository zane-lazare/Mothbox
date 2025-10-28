# 🎨 Mothbox Camera Settings Presets Guide

## Overview

The preset system allows you to save, load, and share camera and liveview settings configurations. This eliminates the need to manually adjust 20+ parameters every time you want to switch between different photography scenarios (daylight, night, macro, etc.).

---

## What are Presets?

**Presets** are saved configurations that contain both **camera settings** (for full-resolution captures) and **liveview settings** (for the live preview stream). A single preset can include:

- **Camera Settings**: Exposure time, ISO/gain, focus mode, sharpness, HDR settings, focus bracketing, etc.
- **Liveview Settings**: Preview quality, brightness, contrast, autofocus mode, noise reduction, etc.

---

## Built-in Presets

Mothbox includes 5 professionally optimized built-in presets:

### ☀️ **Daylight Photography**
**Use when:** Photographing insects in bright outdoor conditions during the day

**Optimizations:**
- Fast shutter speed (5000µs / 0.005s)
- Low ISO (1.5 gain) for clean images
- Enhanced sharpness (2.0) for crisp details
- No HDR needed (single exposure)
- Noise reduction off (signal is clean)

**Ideal for:** Bright sunny days, butterfly photography, daytime pollinator monitoring

---

### 🌙 **Night Photography**
**Use when:** Photographing insects at night or in very low light

**Optimizations:**
- Long exposure (50000µs / 0.05s)
- High ISO (8.0 gain) for sensitivity
- 5-exposure HDR bracketing for dynamic range
- Maximum noise reduction (2) for clean night shots
- Slight brightness boost (+0.1)

**Ideal for:** Moth trapping, nocturnal insect monitoring, UV light setups

---

### 🔍 **Macro Photography**
**Use when:** Taking extreme close-up photos of small insects

**Optimizations:**
- Macro focus range (10cm - 50cm)
- 5-step focus bracketing for depth stacking
- Maximum sharpness (2.5) for incredible detail
- Lens settle delay (500ms) for stable focus transitions
- Locked color gains for consistent stacking

**Ideal for:** Tiny insects, extreme detail work, scientific documentation

---

### ⚡ **High Speed**
**Use when:** Photographing fast-moving subjects in flight

**Optimizations:**
- Very fast shutter (2000µs / 0.002s) to freeze motion
- Continuous autofocus (AfMode=2)
- Fast AF speed for quick tracking
- Full focus range (10cm - infinity)
- No HDR (speed priority)

**Ideal for:** Bees in flight, dragonflies, fast-moving pollinators

---

### ⚖️ **Balanced (General Purpose)**
**Use when:** You need versatile settings for mixed conditions

**Optimizations:**
- Moderate exposure (10000µs / 0.01s)
- Moderate ISO (4.0 gain)
- Auto exposure enabled
- Standard focus range
- Light noise reduction (1)

**Ideal for:** General monitoring, mixed lighting, when you're not sure which preset to use

---

## Using Presets

### 1. Viewing Available Presets

1. Navigate to **Settings** page
2. Click **"Camera Settings"** tab
3. At the top, you'll see the **Settings Presets** panel
4. Click the **"Quick Presets"** dropdown to see:
   - **Built-in Presets** (5 system presets)
   - **My Presets** (your custom presets)

### 2. Applying a Preset

1. Select a preset from the dropdown
2. Read the description below the dropdown
3. Choose where to apply it:
   - **📸 Capture** - Apply to full-resolution photo captures only
   - **👁️ Liveview** - Apply to live preview stream only
   - **🔄 Both** - Apply to both capture and liveview

4. Click the button - settings will be applied immediately
5. You'll see a success message confirming the preset was applied

**Tip:** Apply to "Liveview" first to test settings, then apply to "Capture" if you like the results!

---

## Creating Custom Presets

### Step-by-Step

1. **Configure your ideal settings:**
   - Adjust camera settings (exposure, focus, HDR, etc.)
   - Adjust liveview settings (sharpness, brightness, etc.)
   - Test with photos until you're satisfied

2. **Save as preset:**
   - Navigate to Settings → Camera Settings tab
   - Click **"💾 Save Current Settings as Preset"**
   - Enter a name (use letters, numbers, underscores only)
     - ✅ Good: `my_field_setup`, `garden_daylight`, `moth_trap_2024`
     - ❌ Bad: `my setup!`, `test@home`, `preset #1`
   - Add an optional description
   - Click **"Save Preset"**

3. **Use your preset:**
   - Your custom preset now appears in the **"My Presets"** section
   - Apply it just like built-in presets

### Preset Naming Best Practices

- **Use descriptive names:** `forest_night` instead of `preset1`
- **Include location:** `backyard_moths`, `field_site_a`
- **Include conditions:** `sunny_afternoon`, `rainy_evening`
- **Include subject:** `butterfly_macro`, `bee_flight`

---

## Managing Presets

### Deleting Custom Presets

1. Select your custom preset from the dropdown
2. Click **"🗑️ Delete Preset"** (only appears for user presets)
3. Confirm deletion

**Note:** Built-in presets cannot be deleted or modified

### Preset Storage

- **Built-in presets:** `/etc/mothbox/presets/built-in/`  (read-only)
- **User presets:** `/etc/mothbox/presets/user/`  (your custom presets)

---

## Advanced Usage

### Sharing Presets Between Mothboxes

You can manually copy preset files between devices:

```bash
# On source Mothbox, export your preset
sudo cp /etc/mothbox/presets/user/my_preset.json ~/my_preset.json
scp ~/my_preset.json user@other-mothbox:~/

# On destination Mothbox, import preset
ssh user@other-mothbox
sudo cp ~/my_preset.json /etc/mothbox/presets/user/
sudo chown mothbox:mothbox /etc/mothbox/presets/user/my_preset.json
```

### Viewing Preset Contents

Presets are stored as JSON files:

```bash
cat /etc/mothbox/presets/built-in/daylight.json
```

Example structure:
```json
{
  "name": "daylight",
  "display_name": "☀️ Daylight Photography",
  "description": "Optimized for bright outdoor conditions",
  "category": "built-in",
  "settings": {
    "camera": {
      "ExposureTime": 5000,
      "AnalogueGain": 1.5,
      "Sharpness": 2.0,
      ...
    },
    "liveview": {
      "sharpness": 1.5,
      "brightness": 0.0,
      ...
    }
  }
}
```

---

## Troubleshooting

### Preset doesn't appear in list

**Problem:** Created a preset but it doesn't show up

**Solutions:**
1. Refresh the Settings page (F5)
2. Check that the preset file exists: `ls /etc/mothbox/presets/user/`
3. Verify file permissions: `sudo chmod 644 /etc/mothbox/presets/user/*.json`
4. Check browser console for errors (F12)

---

### Preset fails to apply

**Problem:** "Failed to apply preset" error message

**Solutions:**
1. Verify the preset file is valid JSON: `cat /etc/mothbox/presets/user/preset.json | python3 -m json.tool`
2. Check that settings are within valid ranges
3. Review backend logs: `sudo journalctl -u mothbox-webui -n 50`
4. Try applying to just "Capture" or "Preview" instead of "Both"

---

### Settings don't change after applying preset

**Problem:** Applied preset but settings seem unchanged

**Solutions:**
1. Check which target you selected (Capture vs Liveview vs Both)
2. Verify settings files were updated:
   - Capture: `cat /etc/mothbox/camera_settings.csv`
   - Liveview: `cat /etc/mothbox/liveview_settings.txt`
3. For liveview changes, they apply to *new* liveview sessions (restart liveview)
4. For capture changes, they apply to the *next* photo

---

### Cannot delete built-in preset

**Problem:** Delete button doesn't appear for built-in presets

**This is intentional:** Built-in presets are protected from deletion to ensure you always have working defaults. If you want similar settings, create a custom preset based on the built-in one:

1. Apply the built-in preset
2. Make any tweaks you want
3. Save as a new custom preset

---

## Best Practices

### 1. Test Before Saving
Always test your settings with a few photos before saving as a preset. Use the **Test Capture** button on the Camera page.

### 2. Use Descriptive Names and Descriptions
Future you (and others) will thank you for clear naming:
```
Name: sunny_garden_butterflies
Description: Optimized for photographing butterflies in my garden
             on sunny afternoons. Works best between 2-5pm when
             light is bright but not harsh.
```

### 3. Create Presets for Locations
If you deploy multiple Mothboxes, create presets for each location:
- `forest_site_a_night`
- `meadow_site_b_day`
- `urban_garden_evening`

### 4. Version Your Presets
If you refine settings over time, use versioning:
- `moth_trap_v1`
- `moth_trap_v2_improved`
- `moth_trap_final`

### 5. Start with Built-in Presets
Rather than starting from scratch, apply a built-in preset that's closest to your needs, tweak it, then save as custom.

---

## Preset Workflow Examples

### Example 1: Daytime Butterfly Monitoring

**Goal:** Monitor butterfly activity in bright sunlight

**Workflow:**
1. Apply **☀️ Daylight** preset to **Both**
2. Take test photos
3. If images are too bright, reduce Exposure Time to 3000µs
4. If you want more pop, increase Saturation to 1.2
5. Save as custom preset: `butterfly_monitoring_sunny`

---

### Example 2: Night Moth Trap

**Goal:** Photograph moths at UV light trap at night

**Workflow:**
1. Apply **🌙 Night** preset to **Both**
2. Take test photos
3. If moths are blurry (moving), reduce exposure to 30000µs
4. If images are too noisy, increase AnalogueGain to 10.0
5. Enable focus bracketing (3 steps) if depth is an issue
6. Save as: `uv_moth_trap_night`

---

### Example 3: Macro Study of Tiny Insects

**Goal:** Extreme close-up photos for scientific documentation

**Workflow:**
1. Apply **🔍 Macro** preset to **Both**
2. Take test photos
3. Adjust focus bracket range (start/end) based on insect size
4. Increase settle delay to 800ms if vibrations are an issue
5. Save as: `scientific_macro_2mm_subjects`

---

## API Reference

For programmatic access to presets (e.g., automation, scripts):

### List Presets
```bash
curl http://localhost:5000/api/presets
```

### Get Preset Details
```bash
curl http://localhost:5000/api/presets/daylight
```

### Apply Preset
```bash
curl -X POST http://localhost:5000/api/presets/daylight/apply \
  -H "Content-Type: application/json" \
  -d '{"apply_to": "capture"}'
```

### Create Preset from Current Settings
```bash
curl -X POST http://localhost:5000/api/presets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_preset",
    "description": "My custom preset",
    "from_current": true
  }'
```

### Delete Preset
```bash
curl -X DELETE http://localhost:5000/api/presets/my_preset
```

---

## Summary

The preset system makes it easy to:
- ✅ Quickly switch between photography scenarios
- ✅ Save your perfect settings for reuse
- ✅ Share configurations between Mothboxes
- ✅ Start with professional defaults
- ✅ Avoid manually adjusting 20+ settings each time

**Get started:** Navigate to Settings → Camera Settings and try applying a built-in preset today!

---

**Questions or Issues?**
- Check the troubleshooting section above
- Review WebUI logs: `sudo journalctl -u mothbox-webui -f`
- Report issues: https://github.com/your-repo/issues
