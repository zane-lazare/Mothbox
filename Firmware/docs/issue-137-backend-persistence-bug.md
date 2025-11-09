# Issue #137 Sub-Issue: Gallery View Mode Not Persisting to Backend

**Parent Issue:** #137 - Gallery View Mode Toggle
**Severity:** Medium
**Component:** Backend (webui/backend/user_preferences.py)
**Discovered:** During code review of ViewModeToggle.jsx normalization logic

## Problem

The gallery view mode preference (`gallery_view_mode`) is **not being persisted to the backend** despite appearing to work in the UI. The feature only functions due to React Query's optimistic updates (client-side caching), meaning the preference is lost on page refresh or across devices.

## Root Cause

The `gallery_view_mode` key is **missing** from the `DEFAULT_PREFERENCES` dictionary in `webui/backend/user_preferences.py`.

**Current DEFAULT_PREFERENCES (lines 16-20):**
```python
DEFAULT_PREFERENCES = {
    'camera_presets_collapsed': True,
    'recent_presets_collapsed': False,
    'builtin_presets_collapsed': False,
}
```

**Backend validation (lines 136-138):**
```python
if key not in DEFAULT_PREFERENCES:
    print(f"Warning: Unknown preference key '{key}'")
    return False  # Silently fails to save
```

When the frontend calls `POST /api/preferences` with `gallery_view_mode`, the backend:
1. Prints a warning to console: `"Warning: Unknown preference key 'gallery_view_mode'"`
2. Returns `False` (failure)
3. Does not save the value

## Impact

**Current behavior:**
- ✅ View mode changes work within a single session (React Query cache)
- ❌ Preference is lost on page refresh
- ❌ Preference is not shared across devices/browsers
- ❌ Backend API silently fails with no user feedback

## Evidence

### Frontend expects persistence:
**File:** `webui/frontend/src/hooks/useViewMode.js:68-78`
```javascript
const mutation = useMutation({
  mutationFn: async (mode) => {
    await setUserPreference(PREFERENCE_KEY, mode)  // Calls backend API
    return mode
  },
  // ... optimistic updates
})
```

### Backend rejects the key:
**File:** `webui/backend/user_preferences.py:136-138`
```python
if key not in DEFAULT_PREFERENCES:
    print(f"Warning: Unknown preference key '{key}'")
    return False
```

## Solution

Add `gallery_view_mode` to the `DEFAULT_PREFERENCES` dictionary:

```python
DEFAULT_PREFERENCES = {
    'camera_presets_collapsed': True,
    'recent_presets_collapsed': False,
    'builtin_presets_collapsed': False,
    'gallery_view_mode': 'grid',  # ADD THIS LINE
}
```

## Testing Steps

### Verify the bug:
1. Open browser DevTools → Network tab
2. Change gallery view mode (grid ↔ list)
3. Look for POST to `/api/preferences`
4. Check backend console for: `"Warning: Unknown preference key 'gallery_view_mode'"`
5. Refresh the page → view mode resets to default

### Verify the fix:
1. Apply the change to `DEFAULT_PREFERENCES`
2. Restart the backend server
3. Change gallery view mode
4. Verify POST to `/api/preferences` returns success (200 OK)
5. Refresh the page → view mode should persist
6. Check `~/.mothbox/user_preferences.json` contains `"gallery_view_mode": "list"` or `"grid"`

## Related Files

- **Backend:** `webui/backend/user_preferences.py` (lines 16-20, 136-138)
- **Frontend:** `webui/frontend/src/hooks/useViewMode.js` (lines 68-78)
- **API Route:** `webui/backend/routes/preferences.py`

## Additional Notes

This is a classic case of frontend-backend contract mismatch:
- Frontend assumes the key is valid
- Backend uses a whitelist approach
- No validation feedback to the frontend
- Optimistic updates mask the failure

Consider adding:
1. Backend validation endpoint to check if a preference key is valid
2. Frontend error handling for failed preference saves
3. Unit test to ensure all frontend preference keys exist in backend defaults
