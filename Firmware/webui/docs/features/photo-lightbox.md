# Photo Lightbox User Guide

## Overview

The Mothbox Gallery includes an adaptive photo lightbox for viewing, zooming, and navigating through photos. The lightbox supports both desktop and mobile devices with intuitive controls optimized for each platform.

## Features

### Desktop Controls

| Action | Controls |
|--------|----------|
| **Open lightbox** | Click any photo thumbnail in the gallery |
| **Navigate photos** | Arrow keys (← →), navigation buttons, or click prev/next buttons |
| **Zoom in** | Mouse wheel up, `+` key, or click zoom in button |
| **Zoom out** | Mouse wheel down, `-` key, or click zoom out button |
| **Pan (when zoomed)** | Click and drag the image |
| **Reset zoom** | Click reset button (appears when zoomed > 1.0x) |
| **Close** | `ESC` key, close button (×), or click outside the photo |

#### Mouse Wheel Zoom
- Zoom centers on cursor position (zoom toward where you're pointing)
- Smooth zoom from 1.0x (100%) to 5.0x (500%)
- 0.5x increments per wheel step

### Mobile Controls

| Action | Gesture |
|--------|---------|
| **Open lightbox** | Tap any photo thumbnail |
| **Navigate photos** | Swipe left/right (when not zoomed), or tap navigation buttons |
| **Zoom in** | Pinch-out gesture (two fingers spread apart) or tap zoom in button |
| **Zoom out** | Pinch-in gesture (two fingers come together) or tap zoom out button |
| **Pan (when zoomed)** | Drag with one finger |
| **Quick zoom** | Double-tap: toggles between 1.0x and 2.5x zoom |
| **Close** | Close button (×) or tap outside the photo |

#### Touch Gestures
- **Pinch-to-zoom**: Natural two-finger gesture, centers on pinch midpoint
- **Double-tap zoom**: Quick way to zoom in/out
  - First double-tap: Zooms to 2.5x at tap position
  - Second double-tap: Returns to 1.0x (fit to screen)
- **Swipe navigation**: Disabled when zoomed (prevents accidental navigation)
  - Minimum swipe distance: 50 pixels
  - Minimum swipe velocity: 0.3 pixels/millisecond

### Visual Feedback

- **Zoom indicator**: Displays current zoom level (e.g., "150%") for 2 seconds after zooming
- **Loading spinner**: Shows while image is loading
- **Error message**: Displays if image fails to load
- **Cursor changes**:
  - Default cursor at 1.0x zoom
  - Grab cursor (open hand) when zoomed and hoverable
  - Grabbing cursor (closed fist) when panning
- **Photo counter**: Shows current position (e.g., "3 / 15") when multiple photos available

### Accessibility

The lightbox is fully accessible and meets WCAG 2.1 AA standards:

#### Keyboard Navigation
- `Tab` / `Shift+Tab`: Cycle through interactive controls
- `Arrow keys`: Navigate between photos
- `+` / `-`: Zoom in/out
- `ESC`: Close lightbox
- Focus trap: Tab navigation stays within lightbox when open

#### Screen Reader Support
- All controls have proper ARIA labels
- Zoom level announced as "Zoom level: [percentage]"
- Photo metadata announced: filename, date, size
- Navigation instructions provided
- Loading and error states announced

#### Touch Targets
- All buttons meet 44×44 pixel minimum size (WCAG AAA)
- Sufficient spacing between interactive elements

## Zoom & Pan Details

### Zoom Range
- **Minimum**: 1.0x (100%) - fits image to screen
- **Maximum**: 5.0x (500%) - maximum magnification
- **Step**: 0.5x (50%) increments for button/keyboard zoom

### Pan Boundaries
- Pan is constrained to prevent seeing outside the image
- Automatic boundary calculation based on image and container size
- Pan resets to center (0, 0) when zoom returns to 1.0x

### Zoom Persistence
- Zoom level is maintained when navigating between photos
- Allows comparing details at same zoom level across multiple images

## Performance

### Progressive Loading
- Current image loads first (priority)
- Adjacent images preloaded in background
- Previous and next photos ready for instant navigation

### Smooth Animations
- 60 FPS GPU-accelerated transforms
- CSS `translate3d()` and `scale()` for hardware acceleration
- Smooth transitions between zoom levels
- No layout shift when opening/closing

### Optimization
- Debounced resize handlers (300ms) prevent excessive recalculation
- Efficient event listener management with proper cleanup
- Touch gesture conflict prevention

## Tips & Tricks

### For Desktop Users
1. **Quick zoom**: Use mouse wheel for precise zoom control
2. **Navigate while zoomed**: Use arrow keys to compare same detail across photos
3. **Reset view**: Click reset button or zoom out to 1.0x to auto-center

### For Mobile Users
1. **Quick zoom toggle**: Double-tap for fast 1.0x ↔ 2.5x switching
2. **Precise zoom**: Use pinch gesture for fine control (1.0x - 5.0x)
3. **Navigate efficiently**: Swipe at 1.0x zoom, then zoom in to examine details

### Wraparound Navigation
- Navigate past the last photo to return to the first photo
- Navigate before the first photo to jump to the last photo
- Works with keyboard arrows, buttons, and swipe gestures

## Browser Compatibility

### Tested and Supported
- ✅ Chrome 120+ (desktop and mobile)
- ✅ Firefox 121+ (desktop)
- ✅ Edge 120+ (desktop)
- ⚠️ Safari 17+ (desktop and iOS) - should work but not extensively tested

### Requirements
- JavaScript enabled
- Modern browser with CSS transforms support
- Touch Events API (for mobile gestures)

## Troubleshooting

### Lightbox won't open
**Symptoms**: Clicking photo thumbnail does nothing

**Solutions**:
1. Ensure JavaScript is enabled in browser settings
2. Check browser console for errors (F12 → Console tab)
3. Try refreshing the page
4. Clear browser cache and reload

### Touch gestures not working (mobile)
**Symptoms**: Pinch-to-zoom or swipe not responding

**Solutions**:
1. Ensure device supports touch events
2. Try closing and reopening the lightbox
3. Check if browser has touch gesture support enabled
4. Update browser to latest version

### Images not loading
**Symptoms**: Spinner shows indefinitely or error message appears

**Solutions**:
1. Check internet connection
2. Verify image files exist on server
3. Check browser console for network errors
4. Try refreshing the page
5. Contact administrator if issue persists

### Pan not working when zoomed
**Symptoms**: Can't drag image after zooming in

**Solutions**:
1. Ensure zoom level is > 1.0x (check zoom indicator)
2. Try zooming in with zoom button instead of gesture
3. On mobile: Use single finger, not multiple touches
4. On desktop: Click and drag, don't just move mouse

### Zoom indicator stuck on screen
**Symptoms**: Zoom percentage display doesn't disappear

**Solutions**:
1. Wait 2 seconds - it should auto-hide
2. Try zooming again to refresh the timer
3. Close and reopen lightbox

### Performance issues (slow/laggy)
**Symptoms**: Animations stuttering, slow response

**Solutions**:
1. Close other browser tabs to free memory
2. Reduce zoom level (lower zoom = better performance)
3. Try using a more modern browser
4. Check device performance (older devices may struggle with large images)

## Advanced Usage

### Keyboard Power Users

Create efficient workflows with keyboard shortcuts:

```
1. Open gallery
2. Click first photo to open lightbox
3. Use arrow keys to quickly scan through photos
4. When you find something interesting:
   - Press '+' to zoom in
   - Click and drag to pan to area of interest
   - Press arrow keys to compare with adjacent photos at same zoom
   - Press '-' to zoom out
5. Press ESC to close when done
```

### Mobile Workflow

Efficient mobile examination:

```
1. Tap photo to open lightbox
2. Swipe through photos at 1.0x to find interesting specimen
3. Double-tap to zoom to 2.5x
4. Use pinch gesture for fine zoom adjustment (if needed)
5. Pan with one finger to examine details
6. Swipe won't work when zoomed - use nav buttons or zoom out first
7. Double-tap again to return to 1.0x
8. Tap outside photo to close
```

## Technical Details

### Zoom Algorithm
- Zoom levels: 1.0x, 1.5x, 2.0x, 2.5x, 3.0x, 3.5x, 4.0x, 4.5x, 5.0x
- Cursor-relative zoom (desktop): Keeps point under cursor stationary
- Center zoom (mobile buttons): Zooms toward image center
- Pinch/double-tap zoom: Centers on gesture midpoint/tap position

### Pan Constraints
```
scaledWidth = imageNaturalWidth × zoom
scaledHeight = imageNaturalHeight × zoom

maxPanX = max(0, (scaledWidth - containerWidth) / 2)
maxPanY = max(0, (scaledHeight - containerHeight) / 2)

constrainedPanX = clamp(panX, -maxPanX, maxPanX)
constrainedPanY = clamp(panY, -maxPanY, maxPanY)
```

### Touch Gesture Thresholds
- **Swipe minimum distance**: 50 pixels
- **Swipe minimum velocity**: 0.3 px/ms
- **Double-tap threshold**: 300 milliseconds
- **Touch target minimum**: 44×44 pixels

### Performance Targets
- **Frame rate**: 60 FPS during all interactions
- **Lightbox open/close**: < 200ms animation
- **Photo navigation**: < 100ms transition
- **Image preload**: Background, non-blocking

## Support

For technical issues or feature requests:
- GitHub Issues: [Mothbox Issue #101](https://github.com/Digital-Naturalism-Laboratories/Mothbox/issues/101)
- Documentation: See `webui/frontend/src/components/PhotoLightbox.jsx` JSDoc comments for developer details

---

**Version**: 1.0
**Last Updated**: November 2025
**Component**: PhotoLightbox v1.0 (Issue #101)
