## 🔄 Implementation Approach Update

After architecture review, we're implementing GPS EXIF embedding using a **post-processing approach** rather than modifying `TakePhoto.py` directly.

### 📋 TL;DR

**What changed:** GPS coordinates are added to photos AFTER capture via a post-processing script, not during photo capture.

**Why:** Better separation of concerns, zero firmware modifications, enables retroactive tagging of existing photos.

### ✅ All Original Requirements Still Met

- ✅ GPS coordinates embedded in EXIF when available
- ✅ Graceful fallback when GPS unavailable
- ✅ Standard EXIF format (degrees, minutes, seconds)
- ✅ Works with scheduled captures (via optional systemd service)
- ✅ No regression in photo capture performance (actually BETTER - zero overhead)

### 🏗️ Architecture Highlights

**Old approach (original issue):**
```
TakePhoto.py → Capture + Embed GPS inline → Save JPEG
```

**New approach (post-processing):**
```
TakePhoto.py → Capture → Save JPEG (no GPS)
                            ↓
GPS Tagger Script → Read GPS from controls.txt → Add GPS EXIF → Update JPEG
```

### 🎯 Key Benefits

1. **Zero firmware modifications** - `TakePhoto.py` (4.x and 5.x) remain completely untouched
2. **Retroactive tagging** - Can add GPS to photos captured before this feature existed
3. **Multiple deployment modes** - Choose immediate (systemd), lazy (on-demand), or batch
4. **Better testability** - GPS embedding can be tested independently of photo capture
5. **Easier rollback** - Can disable GPS tagging without affecting photo captures

### 📦 Deliverables

**Files to create:**
- `shared_utils/gps_exif_lib.py` - GPS coordinate conversion utilities
- `shared_utils/gps_exif_tagger.py` - Main tagging script
- `shared_utils/scripts/batch_tag_photos.py` - Batch processing utility
- `shared_utils/scripts/verify_gps_exif.py` - Validation tool
- `systemd/mothbox-gps-tagger.service` - Optional systemd service (immediate mode)
- Tests: `Tests/unit/test_gps_exif.py` and `Tests/integration/test_gps_exif_integration.py`

**Files to modify:**
- `5.x/GPS.py` - Add altitude storage (~3 lines)
- `4.x/GPS.py` - Add altitude storage (~3 lines)

### 📖 Full Specification

Complete implementation details, function signatures, testing strategy, and deployment options available in: [ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md](https://github.com/zane-lazare/Mothbox/issues/98#issuecomment-3513641316)

### 🚀 Implementation Timeline

Estimated: 2-3 days (unchanged from original estimate)

**Phase breakdown:**
1. Core library (GPS conversions) - 1 day
2. Main tagger script - 0.5 day
3. Testing - 0.5 day
4. Optional systemd service - 0.5 day (if deploying immediate mode)

### ❓ Questions?

The full spec answers:
- How GPS data flows from GPS.py → controls.txt → photos
- How to handle photos without GPS fix
- How to deploy in different modes (immediate/lazy/batch)
- How to validate GPS EXIF correctness
- How to handle edge cases (corrupted EXIF, timestamp mismatches, etc.)

Ready for implementation! 🎉
