# GPS Epoch Timestamp Fix

**Issue:** #381
**Date:** 2026-01-27
**Status:** Implementing

## Problem

`GPS.py` calculates incorrect Unix epoch timestamps due to Python's naive datetime handling. When `strptime()` parses a UTC time string, it creates a naive datetime. Calling `.timestamp()` on a naive datetime interprets it as local time, causing an offset equal to the system's UTC offset.

**Example (NZDT = UTC+13):**
- GPS returns: `"2026-01-27T05:00:00Z"` (5am UTC)
- Bug produces: epoch for `4pm UTC previous day` (13 hours off)

## Solution

Make the datetime timezone-aware before calling `.timestamp()`:

```python
from datetime import timezone
dt = dt.replace(tzinfo=timezone.utc)
epoch_time = int(dt.timestamp())
```

## Files Changed

1. `5.x/GPS.py` line 231 - Core fix
2. `4.x/GPS.py` line 231 - Same fix (identical code)
3. `Tests/fixtures/create_test_photos.py` line 75 - Test fixture consistency

## Testing

- Existing GPS tests should pass
- Manual verification with non-UTC timezone
