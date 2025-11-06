# Quick Testing Guide - Phase 1.1-1.3

## Remote Testing on Raspberry Pi

### Step 1: Pull Latest Code
```bash
cd ~/Mothbox
git pull origin feature/camera-controls-performance
```

### Step 2: Install Test Dependencies
```bash
cd ~/Mothbox/Firmware
pip3 install -r Tests/requirements-test.txt
```

### Step 3: Run Automated Tests
```bash
# Quick test (most important tests)
pytest Tests/unit/test_camera_stream.py::TestSimpleJPEGEncoding::test_encoding_speed_comparison -v -s

# Full unit test suite
pytest Tests/unit/ -v -s

# Full integration test suite
pytest Tests/integration/ -v -s

# Everything
pytest Tests/ -v -s
```

### Step 4: Manual WebUI Testing
```bash
# Start WebUI
python3 ~/Mothbox/Firmware/webui/backend/app.py
```

Then in browser at `http://pi-ip:5000`:

1. **Camera Page** - Test Preview
   - Click "Start Preview"
   - Wave hand → lag should be <500ms (not 2-3s)
   - Image should be sharp and clear
   - Stop and start preview a few times

2. **Settings Page** - Stream Settings Tab
   - Verify all controls present:
     * Resolution selector
     * Frame Rate slider (1-30)
     * JPEG Quality slider (50-100)
     * **Encoding Mode dropdown** ← NEW!
   - Change quality to 70, save, restart preview
   - Change quality to 95, save, restart preview
   - Verify 85 feels best (balanced)

3. **Settings Page** - Verify Defaults
   - Check JPEG Quality = 85 (not 95)
   - Check Encoding Mode = "Fast Software (simplejpeg)"

## Expected Test Results

### Encoding Speed Test
```
📊 Encoding Performance (1024x768, Q=85):
   PIL (optimize=True): ~180-200ms
   simplejpeg:          ~25-35ms
   Speedup:             ~6x ✓
```

### Sustained Performance Test
```
📊 Sustained 100 frames @ 10 FPS:
   Avg encoding: ~30ms
   Max encoding: ~45ms
   Frame budget: 100ms
   Headroom: ~70ms ✓
```

## Success Criteria

✅ **simplejpeg 5-7x faster than PIL**
✅ **Single frame encoding <50ms**
✅ **Sustained 10 FPS without backlog**
✅ **Preview lag <500ms** (measured by hand wave)
✅ **Default quality = 85** (in Settings UI)
✅ **Encoding mode dropdown visible** in Settings
✅ **No errors in browser console**
✅ **No errors in Python logs**

## Common Issues

### "simplejpeg not found"
Already installed! If you see this:
```bash
python3 -c "import simplejpeg; print(simplejpeg.__version__)"
# Should output: 1.8.1
```

### "Tests fail with import errors"
```bash
pip3 install pytest pytest-mock pytest-timeout
```

### "Preview still laggy"
- Check what quality is set (Settings > Stream Settings)
- Should be 85, not 95 or 100
- Restart preview after changing settings
- Check browser Network tab for frame rate

### "Settings don't persist"
- Check `/etc/mothbox/webui_settings.txt` exists
- Should contain `stream_mode=simplejpeg` line
- Check file permissions

## Performance Comparison

| Metric | Before (PIL Q=95) | After (simplejpeg Q=85) | Improvement |
|--------|-------------------|-------------------------|-------------|
| Encoding | 150-250ms | 20-40ms | **5-7x faster** |
| Preview Lag | 2-3s | <500ms | **83% reduction** |
| File Size | 100% | 60-70% | **30-40% smaller** |
| Throughput | ~4-6 FPS | 10 FPS | **2x increase** |

## Quick Verification Commands

```bash
# Check simplejpeg available
python3 -c "import simplejpeg; print('✓ simplejpeg', simplejpeg.__version__)"

# Check current settings
cat /etc/mothbox/webui_settings.txt

# Run single most important test
pytest Tests/unit/test_camera_stream.py::TestSimpleJPEGEncoding::test_encoding_speed_comparison -v -s

# Check WebUI logs for simplejpeg
tail -f ~/Mothbox/Firmware/webui/backend/app.log | grep simplejpeg
```

## Files to Check After Testing

1. **Browser Console** (F12)
   - Should show no errors
   - Network tab: frames arriving smoothly

2. **Python Logs**
   - Should show: "✓ simplejpeg available for fast JPEG encoding"
   - Should show: "Stream settings loaded: ... Mode: simplejpeg"

3. **Config File**: `/etc/mothbox/webui_settings.txt`
   ```
   preview_width=1024
   preview_height=768
   frame_rate=10
   jpeg_quality=85
   stream_mode=simplejpeg
   ```

## Report Results

Please report:
1. ✅/❌ for each success criteria above
2. Actual encoding speed from test output
3. Measured preview lag (stopwatch or feel)
4. Any errors in console or logs
5. Screenshots of Settings > Stream Settings page

---

**Ready to Test!** 🚀

If all tests pass, this implementation is ready to merge.
