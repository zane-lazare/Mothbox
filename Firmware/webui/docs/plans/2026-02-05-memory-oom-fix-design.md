# Memory OOM Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix OOM failures during scheduled photo capture on Raspberry Pi 5 by disabling watermark boost and improving memory hygiene.

**Architecture:** Three-pronged approach: (1) kernel sysctl tuning to disable NUMA watermark boost accumulation, (2) explicit resource cleanup in thumbnail generation, (3) proper camera resource release in photo capture script. Integrated into installer/updater for all future deployments.

**Tech Stack:** Linux sysctl, Python/PIL, Picamera2, Bash scripting

---

## Related Issues

- #393 - Primary: watermark_boost_factor fix
- #394 - Secondary: thumbnail_cache.py explicit image close
- #395 - Tertiary: TakePhoto.py camera close

---

### Task 1: Apply Primary Fix to mothbox-remote

**Files:**
- Create: `/etc/sysctl.d/99-mothbox-memory.conf` (on remote)

**Step 1: Verify current watermark_boost_factor value**

Run:
```bash
ssh mothbox-remote "cat /proc/sys/vm/watermark_boost_factor"
```
Expected: `15000` (default value)

**Step 2: Create sysctl configuration file**

Run:
```bash
ssh mothbox-remote "sudo tee /etc/sysctl.d/99-mothbox-memory.conf > /dev/null << 'EOF'
# Mothbox memory tuning for Raspberry Pi 5
# Disables watermark boost to prevent OOM during photo capture
# See: https://github.com/zane-lazare/Mothbox/issues/393
#
# The Pi 5 uses numa=fake=8 for performance, but the default
# watermark_boost_factor (15000) reserves too much memory per
# NUMA node during memory pressure, causing OOM accumulation.

vm.watermark_boost_factor = 0
EOF"
```
Expected: No output (success)

**Step 3: Apply configuration immediately**

Run:
```bash
ssh mothbox-remote "sudo sysctl -p /etc/sysctl.d/99-mothbox-memory.conf"
```
Expected: `vm.watermark_boost_factor = 0`

**Step 4: Verify configuration applied**

Run:
```bash
ssh mothbox-remote "cat /proc/sys/vm/watermark_boost_factor"
```
Expected: `0`

---

### Task 2: Deploy Monitoring Script

**Files:**
- Create: `/opt/mothbox/scripts/memory_health_check.sh` (on remote)

**Step 1: Create scripts directory if needed**

Run:
```bash
ssh mothbox-remote "sudo mkdir -p /opt/mothbox/scripts && sudo mkdir -p /var/log/mothbox"
```
Expected: No output (success)

**Step 2: Create monitoring script**

Run:
```bash
ssh mothbox-remote "sudo tee /opt/mothbox/scripts/memory_health_check.sh > /dev/null << 'SCRIPT'
#!/bin/bash
# Memory health check for Mothbox
# Run via cron: 0 * * * * /opt/mothbox/scripts/memory_health_check.sh >> /var/log/mothbox/memory_health.log 2>&1

echo \"=== Memory Health Check \$(date) ===\"

# Check for OOM events in kernel buffer
OOM_COUNT=\$(dmesg | grep -ci \"out of memory\" || echo 0)
echo \"OOM events (kernel buffer): \$OOM_COUNT\"

# Check allocation stalls
ALLOC_STALLS=\$(cat /proc/vmstat | grep -E \"allocstall_dma|allocstall_normal\" | awk '{sum+=\$2} END {print sum}')
echo \"Allocation stalls (total): \$ALLOC_STALLS\"

# Check compaction stats
COMPACT_STALLS=\$(cat /proc/vmstat | grep compact_stall | awk '{print \$2}')
echo \"Compaction stalls: \$COMPACT_STALLS\"

# Check current watermark boost state
echo \"Watermark boost by node:\"
cat /proc/zoneinfo | grep -E \"(^Node.*zone.*DMA\$|boost)\" | paste - - | head -8

# Memory summary
echo \"Memory summary:\"
free -h

echo \"\"
SCRIPT"
```
Expected: No output (success)

**Step 3: Make script executable**

Run:
```bash
ssh mothbox-remote "sudo chmod +x /opt/mothbox/scripts/memory_health_check.sh"
```
Expected: No output (success)

**Step 4: Test script execution**

Run:
```bash
ssh mothbox-remote "/opt/mothbox/scripts/memory_health_check.sh"
```
Expected: Output showing memory stats, OOM count = 0, boost values

**Step 5: Add hourly cron job**

Run:
```bash
ssh mothbox-remote "echo '0 * * * * /opt/mothbox/scripts/memory_health_check.sh >> /var/log/mothbox/memory_health.log 2>&1' | sudo tee /etc/cron.d/mothbox-memory-health"
```
Expected: Cron entry echoed back

---

### Task 3: Establish Baseline Metrics

**Step 1: Record current vmstat counters**

Run:
```bash
ssh mothbox-remote "cat /proc/vmstat | grep -E 'allocstall|compact_stall|oom_kill' | tee /tmp/vmstat_baseline.txt"
```
Expected: Current counter values saved

**Step 2: Check current OOM count in dmesg**

Run:
```bash
ssh mothbox-remote "dmesg | grep -ci 'out of memory' || echo 0"
```
Expected: Number (note this as baseline)

**Step 3: Verify scheduler is running with photos**

Run:
```bash
ssh mothbox-remote "crontab -l | grep -c TakePhoto"
```
Expected: Number > 0 (active schedule entries)

---

### Task 4: Fix thumbnail_cache.py - Write Test

**Files:**
- Create: `Tests/unit/test_thumbnail_memory.py`
- Modify: `webui/backend/services/thumbnail_cache.py:184-191`

**Step 1: Write failing test for explicit image close**

Create file `Tests/unit/test_thumbnail_memory.py`:
```python
"""Tests for thumbnail cache memory management."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestThumbnailMemoryManagement:
    """Test that thumbnail generation properly releases image resources."""

    @patch('webui.backend.services.thumbnail_cache.Image')
    def test_image_closed_after_thumbnail_generation(self, mock_image_module):
        """Verify Image.open() result is properly closed via context manager."""
        from webui.backend.services.thumbnail_cache import ThumbnailCache

        # Setup mock
        mock_img = MagicMock()
        mock_img.__enter__ = Mock(return_value=mock_img)
        mock_img.__exit__ = Mock(return_value=False)
        mock_image_module.open.return_value = mock_img
        mock_image_module.LANCZOS = 1

        # Create cache instance with temp directory
        cache = ThumbnailCache(cache_dir=Path('/tmp/test_thumbnails'))

        # Mock the photo path and cache path
        with patch.object(cache, '_get_cache_path', return_value=Path('/tmp/test_cache.jpg')):
            with patch.object(Path, 'exists', return_value=True):
                with patch('fcntl.flock'):
                    with patch('builtins.open', MagicMock()):
                        # This should use context manager
                        try:
                            cache.get_thumbnail(Path('/tmp/test.jpg'), size=200)
                        except Exception:
                            pass  # We're testing the context manager usage, not full flow

        # Verify context manager was used (enter/exit called)
        mock_img.__enter__.assert_called()
        mock_img.__exit__.assert_called()
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && python -m pytest Tests/unit/test_thumbnail_memory.py -v
```
Expected: FAIL (context manager not used in current implementation)

---

### Task 5: Fix thumbnail_cache.py - Implement

**Files:**
- Modify: `webui/backend/services/thumbnail_cache.py:184-191`

**Step 1: Update thumbnail generation to use context manager**

In `webui/backend/services/thumbnail_cache.py`, replace lines 184-190:

Old:
```python
                    # Open and resize
                    img = Image.open(photo_path)

                    # Preserve aspect ratio, fit within size
                    img.thumbnail((size, size), Image.LANCZOS)

                    # Save as JPEG with quality 85
                    img.save(cache_path, format="JPEG", quality=85)
```

New:
```python
                    # Open and resize with explicit resource cleanup
                    with Image.open(photo_path) as img:
                        # Preserve aspect ratio, fit within size
                        img.thumbnail((size, size), Image.LANCZOS)

                        # Save as JPEG with quality 85
                        img.save(cache_path, format="JPEG", quality=85)
```

**Step 2: Run test to verify it passes**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && python -m pytest Tests/unit/test_thumbnail_memory.py -v
```
Expected: PASS

**Step 3: Run existing thumbnail tests to ensure no regression**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && python -m pytest Tests/unit/test_thumbnail*.py -v
```
Expected: All tests PASS

**Step 4: Commit**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && git add Tests/unit/test_thumbnail_memory.py webui/backend/services/thumbnail_cache.py && git commit -m "fix(memory): use context manager for image cleanup in thumbnail_cache.py

Fixes #394

Previously Image.open() results were not explicitly closed, relying on
garbage collection. This could cause memory spikes during cache warming
when processing multiple 64MP images.

Now uses 'with' context manager to ensure immediate resource release."
```

---

### Task 6: Fix TakePhoto.py - Write Test

**Files:**
- Create: `Tests/unit/test_takephoto_cleanup.py`
- Modify: `5.x/TakePhoto.py:898-906`
- Modify: `4.x/TakePhoto.py` (same location)

**Step 1: Write test for camera close in cleanup**

Create file `Tests/unit/test_takephoto_cleanup.py`:
```python
"""Tests for TakePhoto.py resource cleanup."""

import pytest


class TestTakePhotoCleanup:
    """Test that TakePhoto.py properly cleans up camera resources."""

    def test_finally_block_includes_picam2_close(self):
        """Verify TakePhoto.py finally block calls picam2.close()."""
        import re
        from pathlib import Path

        # Check 5.x version
        takephoto_5x = Path(__file__).parent.parent.parent / '5.x' / 'TakePhoto.py'
        content_5x = takephoto_5x.read_text()

        # Find the finally block and check for picam2.close()
        finally_match = re.search(r'finally:\s*\n(.*?)(?=\nsys\.exit|$)', content_5x, re.DOTALL)
        assert finally_match, "Could not find finally block in 5.x/TakePhoto.py"

        finally_block = finally_match.group(1)
        assert 'picam2.close()' in finally_block, \
            "5.x/TakePhoto.py finally block must call picam2.close()"

    def test_4x_finally_block_includes_picam2_close(self):
        """Verify 4.x/TakePhoto.py finally block calls picam2.close()."""
        import re
        from pathlib import Path

        # Check 4.x version
        takephoto_4x = Path(__file__).parent.parent.parent / '4.x' / 'TakePhoto.py'
        content_4x = takephoto_4x.read_text()

        # Find the finally block and check for picam2.close()
        finally_match = re.search(r'finally:\s*\n(.*?)(?=\nsys\.exit|$)', content_4x, re.DOTALL)
        assert finally_match, "Could not find finally block in 4.x/TakePhoto.py"

        finally_block = finally_match.group(1)
        assert 'picam2.close()' in finally_block, \
            "4.x/TakePhoto.py finally block must call picam2.close()"
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && python -m pytest Tests/unit/test_takephoto_cleanup.py -v
```
Expected: FAIL (picam2.close() not in finally block)

---

### Task 7: Fix TakePhoto.py - Implement

**Files:**
- Modify: `5.x/TakePhoto.py:898-906`
- Modify: `4.x/TakePhoto.py` (same location)

**Step 1: Update 5.x/TakePhoto.py finally block**

In `5.x/TakePhoto.py`, replace lines 898-906:

Old:
```python
finally:
    # Cleanup flash relay (Relay_Ch2) on exit to ensure it's off
    # Note: We don't cleanup Relay_Ch3 (attractor) as it's intentionally left on
    try:
        GPIO.cleanup(Relay_Ch2)
        print("GPIO cleanup completed for flash relay")
    except Exception as e:
        print(f"Warning: GPIO cleanup failed: {e}")
```

New:
```python
finally:
    # Cleanup camera resources to prevent memory leaks
    try:
        picam2.close()
        print("Camera closed successfully")
    except Exception as e:
        print(f"Warning: Camera close failed: {e}")

    # Cleanup flash relay (Relay_Ch2) on exit to ensure it's off
    # Note: We don't cleanup Relay_Ch3 (attractor) as it's intentionally left on
    try:
        GPIO.cleanup(Relay_Ch2)
        print("GPIO cleanup completed for flash relay")
    except Exception as e:
        print(f"Warning: GPIO cleanup failed: {e}")
```

**Step 2: Update 4.x/TakePhoto.py with same change**

Apply identical change to `4.x/TakePhoto.py` finally block.

**Step 3: Run test to verify it passes**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && python -m pytest Tests/unit/test_takephoto_cleanup.py -v
```
Expected: PASS

**Step 4: Commit**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && git add Tests/unit/test_takephoto_cleanup.py 5.x/TakePhoto.py 4.x/TakePhoto.py && git commit -m "fix(camera): add picam2.close() in TakePhoto.py cleanup

Fixes #395

Previously only GPIO was cleaned up in the finally block. Camera
resources (DMA buffers, kernel handles) were not explicitly released.

Now calls picam2.close() before GPIO cleanup to ensure proper resource
release. Applied to both 4.x and 5.x versions."
```

---

### Task 8: Integrate into install_mothbox.sh

**Files:**
- Modify: `install_mothbox.sh`

**Step 1: Add configure_memory_tuning function**

Add after line ~91 (after validate_positive_integer function):

```bash
# Configure kernel memory parameters for Pi 5 NUMA compatibility
configure_memory_tuning() {
    echo ""
    echo -e "${BLUE}Configuring kernel memory parameters...${NC}"

    # Only apply on Pi 5 with fake NUMA
    if grep -q "numa=fake" /proc/cmdline 2>/dev/null; then
        echo "Detected Pi 5 with fake NUMA - applying memory tuning"

        SYSCTL_FILE="/etc/sysctl.d/99-mothbox-memory.conf"

        sudo tee "$SYSCTL_FILE" > /dev/null <<EOF
# Mothbox memory tuning for Raspberry Pi 5
# Disables watermark boost to prevent OOM during photo capture
# See: https://github.com/zane-lazare/Mothbox/issues/393
#
# The Pi 5 uses numa=fake=8 for performance, but the default
# watermark_boost_factor (15000) reserves too much memory per
# NUMA node during memory pressure, causing OOM accumulation.

vm.watermark_boost_factor = 0
EOF

        # Apply immediately
        sudo sysctl -p "$SYSCTL_FILE" > /dev/null

        echo -e "${GREEN}✓ Memory tuning configured: $SYSCTL_FILE${NC}"
    else
        echo "Not a Pi 5 with fake NUMA - skipping memory tuning"
    fi
}
```

**Step 2: Call function in installation flow**

Find the section near the end where services are configured (around line 1250) and add:

```bash
# Configure memory tuning for Pi 5
configure_memory_tuning
```

**Step 3: Commit**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && git add install_mothbox.sh && git commit -m "feat(installer): add Pi 5 memory tuning configuration

Part of #393

Adds configure_memory_tuning() function that:
- Detects Pi 5 with fake NUMA via /proc/cmdline
- Creates /etc/sysctl.d/99-mothbox-memory.conf
- Sets vm.watermark_boost_factor=0 to prevent OOM accumulation
- Skips on non-Pi 5 systems"
```

---

### Task 9: Integrate into update_mothbox.sh

**Files:**
- Modify: `update_mothbox.sh`

**Step 1: Add ensure_memory_tuning function**

Add near other utility functions:

```bash
# Ensure memory tuning is applied (for existing installations)
ensure_memory_tuning() {
    SYSCTL_FILE="/etc/sysctl.d/99-mothbox-memory.conf"

    # Only apply on Pi 5 with fake NUMA
    if grep -q "numa=fake" /proc/cmdline 2>/dev/null; then
        if [ ! -f "$SYSCTL_FILE" ]; then
            echo -e "${YELLOW}Applying memory tuning for Pi 5...${NC}"

            sudo tee "$SYSCTL_FILE" > /dev/null <<EOF
# Mothbox memory tuning for Raspberry Pi 5
# Disables watermark boost to prevent OOM during photo capture
# See: https://github.com/zane-lazare/Mothbox/issues/393

vm.watermark_boost_factor = 0
EOF

            sudo sysctl -p "$SYSCTL_FILE" > /dev/null
            echo -e "${GREEN}✓ Memory tuning configured${NC}"
        else
            echo -e "${GREEN}✓ Memory tuning already configured${NC}"
        fi
    fi
}
```

**Step 2: Call function in update flow**

Add call near the end of the update process:

```bash
# Ensure memory tuning for Pi 5
ensure_memory_tuning
```

**Step 3: Commit**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && git add update_mothbox.sh && git commit -m "feat(updater): add Pi 5 memory tuning check

Part of #393

Adds ensure_memory_tuning() that applies memory tuning config
if missing on Pi 5 systems. Ensures existing installations get
the fix when updated."
```

---

### Task 10: Integrate into uninstall_mothbox.sh

**Files:**
- Modify: `uninstall_mothbox.sh`

**Step 1: Add optional memory tuning cleanup**

Add near other cleanup sections:

```bash
# Optionally remove memory tuning configuration
if [ -f "/etc/sysctl.d/99-mothbox-memory.conf" ]; then
    echo ""
    echo -e "${YELLOW}Remove Mothbox memory tuning configuration?${NC}"
    echo "This will restore default kernel memory settings."
    read -p "(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo rm /etc/sysctl.d/99-mothbox-memory.conf
        sudo sysctl -w vm.watermark_boost_factor=15000 > /dev/null
        echo -e "${GREEN}✓ Memory tuning removed, default restored${NC}"
    else
        echo "Memory tuning configuration kept"
    fi
fi
```

**Step 2: Commit**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && git add uninstall_mothbox.sh && git commit -m "feat(uninstaller): add optional memory tuning cleanup

Part of #393

Prompts user to optionally remove memory tuning config during
uninstall and restore kernel defaults."
```

---

### Task 11: Update CLAUDE.md Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add memory tuning section**

Add to the "Configuration Files" section:

```markdown
### Memory Tuning (Pi 5)

On Raspberry Pi 5 with `numa=fake=8`, the installer creates `/etc/sysctl.d/99-mothbox-memory.conf`:
- Sets `vm.watermark_boost_factor=0` to prevent OOM during photo capture
- Only applied when fake NUMA detected in `/proc/cmdline`
- See issue #393 for technical details
```

**Step 2: Commit**

Run:
```bash
cd /home/zane/projects/Mothbox/Firmware && git add CLAUDE.md && git commit -m "docs: add Pi 5 memory tuning to CLAUDE.md

Documents the sysctl configuration for Pi 5 NUMA compatibility
and references issue #393 for details."
```

---

### Task 12: Validate on mothbox-remote (24-48 hours)

**Step 1: Verify schedule is running**

Run:
```bash
ssh mothbox-remote "crontab -l | grep TakePhoto | head -5"
```
Expected: Active cron entries

**Step 2: Check for OOM events after 24 hours**

Run:
```bash
ssh mothbox-remote "dmesg | grep -i 'out of memory' | tail -10"
```
Expected: No new OOM events

**Step 3: Check photo capture success rate**

Run:
```bash
ssh mothbox-remote "ls -la /var/lib/mothbox/photos/\$(date +%Y-%m-%d)/ 2>/dev/null | wc -l"
```
Expected: Count matches expected captures for elapsed time

**Step 4: Review memory health log**

Run:
```bash
ssh mothbox-remote "tail -100 /var/log/mothbox/memory_health.log"
```
Expected: Consistent metrics, no warnings

---

## Success Criteria

- [ ] Zero OOM events during 24-48 hour validation
- [ ] Photo capture success rate >99%
- [ ] All tests pass
- [ ] Code changes committed
- [ ] Installer/updater integration complete
- [ ] Documentation updated

## Rollback Procedure

If issues occur during validation:

```bash
# Immediate rollback
ssh mothbox-remote "echo 15000 | sudo tee /proc/sys/vm/watermark_boost_factor"

# Permanent rollback
ssh mothbox-remote "sudo rm /etc/sysctl.d/99-mothbox-memory.conf && sudo reboot"
```
