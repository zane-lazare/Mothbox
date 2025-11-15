import { useReducer, useCallback, useMemo, useRef, useEffect } from 'react'
import { LIGHTBOX_CONFIG } from '../constants/config'

/**
 * Reducer for managing touch gesture state.
 * Centralizes state updates for cleaner state management vs. 6+ separate useState calls.
 *
 * @param {Object} state - Current state
 * @param {Object} action - Action object with type and payload
 * @returns {Object} New state
 */
function touchGestureReducer(state, action) {
  switch (action.type) {
    case 'PINCH_START':
      return {
        ...state,
        isPinching: true,
        initialPinchDistance: action.payload.distance,
        initialZoom: action.payload.zoom,
        initialPan: action.payload.pan,
        touchStartPos: action.payload.touchStartPos,
      }

    case 'SINGLE_TOUCH_START':
      return {
        ...state,
        touchStartPos: action.payload.touchStartPos,
        initialPan: action.payload.pan,
        isPinching: false,
        initialPinchDistance: null,
      }

    case 'TAP_DETECTED':
      return {
        ...state,
        lastTapTime: action.payload.timestamp,
      }

    case 'RESET_TAP':
      return {
        ...state,
        lastTapTime: 0,
      }

    case 'TOUCH_END':
      return {
        ...state,
        isPinching: false,
        initialPinchDistance: null,
        touchStartPos: null,
      }

    case 'RESET':
      return {
        touchStartPos: null,
        initialPinchDistance: null,
        initialZoom: 1.0,
        initialPan: { x: 0, y: 0 },
        lastTapTime: 0,
        isPinching: false,
      }

    default:
      return state
  }
}

/**
 * Custom hook for managing touch gestures in the photo lightbox.
 *
 * Handles mobile interactions: pinch-to-zoom, touch pan, swipe navigation,
 * and double-tap zoom toggle. All gestures include proper boundary constraints
 * and conflict prevention (e.g., swipe disabled when zoomed).
 *
 * State Management: Uses useReducer instead of 6 separate useState calls for
 * cleaner state updates and easier maintenance. All gesture state transitions
 * are centralized in touchGestureReducer.
 *
 * @hook
 * @param {Object} config - Hook configuration
 * @param {React.RefObject} config.imageRef - Reference to image element for bounds calculation
 * @param {number} config.zoom - Current zoom level (from useZoomPan)
 * @param {Function} config.setZoom - Zoom setter (from useZoomPan)
 * @param {Object} config.pan - Current pan offset {x, y} (from useZoomPan)
 * @param {Function} config.setPan - Pan setter (from useZoomPan)
 * @param {Function} config.onNavigate - Navigation callback: (direction: 'prev' | 'next') => void
 * @param {boolean} config.isZoomed - True if zoom > 1.0 (disables swipe navigation)
 * @param {number} config.imageWidth - Natural image width in pixels
 * @param {number} config.imageHeight - Natural image height in pixels
 * @param {number} config.minZoom - Minimum zoom level (e.g., 1.0)
 * @param {number} config.maxZoom - Maximum zoom level (e.g., 5.0)
 *
 * @returns {Object} Touch event handlers
 * @returns {Function} returns.handleTouchStart - Touch start event handler
 * @returns {Function} returns.handleTouchMove - Touch move event handler
 * @returns {Function} returns.handleTouchEnd - Touch end event handler
 *
 * @example
 * const { handleTouchStart, handleTouchMove, handleTouchEnd } = useTouchGestures({
 *   imageRef,
 *   zoom,
 *   setZoom,
 *   pan,
 *   setPan,
 *   onNavigate: (direction) => console.log('Navigate:', direction),
 *   isZoomed: zoom > 1.0,
 *   imageWidth: 1920,
 *   imageHeight: 1080,
 *   containerWidth: 1280,
 *   containerHeight: 720,
 * })
 *
 * <img
 *   onTouchStart={handleTouchStart}
 *   onTouchMove={handleTouchMove}
 *   onTouchEnd={handleTouchEnd}
 * />
 *
 * @gestures
 * - Pinch-to-zoom: Two-finger pinch in/out (1.0x - 5.0x)
 * - Touch pan: Single-finger drag when zoomed (boundary-constrained)
 * - Swipe navigation: Horizontal swipe left/right (≥50px, ≥0.3px/ms velocity)
 * - Double-tap: Two taps within 300ms (toggles 1.0x ↔ 2.5x zoom)
 *
 * @algorithm Pinch Distance
 * - Distance = √((x2-x1)² + (y2-y1)²)
 * - Scale = currentDistance / initialDistance
 * - newZoom = clamp(initialZoom × scale, minZoom, maxZoom)
 *
 * @algorithm Swipe Detection
 * 1. Horizontal movement > vertical movement
 * 2. Distance ≥ 50px
 * 3. Velocity ≥ 0.3px/ms
 * 4. Only when NOT zoomed (isZoomed = false)
 *
 * @algorithm Double-Tap
 * 1. Tap 1: Record timestamp
 * 2. Tap 2: If within 300ms of tap 1, trigger zoom
 * 3. Zoom out if currently zoomed, zoom to 2.5x if at 1.0x
 * 4. Zoom centers on tap position
 */
function useTouchGestures({
  imageRef,
  zoom,
  setZoom,
  pan,
  setPan,
  onNavigate,
  isZoomed,
  imageWidth,
  imageHeight,
  minZoom,
  maxZoom,
}) {
  // Touch gesture state (managed via reducer for cleaner state updates)
  const [gestureState, dispatch] = useReducer(touchGestureReducer, {
    touchStartPos: null,
    initialPinchDistance: null,
    initialZoom: 1.0,
    initialPan: { x: 0, y: 0 },
    lastTapTime: 0,
    isPinching: false,
  })

  // Destructure for cleaner access
  const {
    touchStartPos,
    initialPinchDistance,
    initialZoom,
    initialPan,
    lastTapTime,
    isPinching,
  } = gestureState

  // RAF throttle for touch move (prevents 60+ updates/sec)
  const rafIdRef = useRef(null)
  const latestTouchDataRef = useRef(null)

  // Gesture detection thresholds (from LIGHTBOX_CONFIG for consistency)
  const { TOUCH_GESTURES } = LIGHTBOX_CONFIG
  const DOUBLE_TAP_THRESHOLD = TOUCH_GESTURES.DOUBLE_TAP_TIMEOUT
  const TAP_MAX_DURATION = TOUCH_GESTURES.TAP_MAX_DURATION
  const SWIPE_MIN_DISTANCE = TOUCH_GESTURES.SWIPE_MIN_DISTANCE
  const SWIPE_MIN_VELOCITY = TOUCH_GESTURES.SWIPE_MIN_VELOCITY
  const ZOOM_DOUBLE_TAP = LIGHTBOX_CONFIG.ZOOM_DOUBLE_TAP

  // DPI-aware double-tap distance threshold for Retina/high-DPI displays
  // Scales base value (15px@1x) by device pixel ratio: 15px@1x, 30px@2x, 45px@3x
  const DOUBLE_TAP_DISTANCE = useMemo(
    () => (window.devicePixelRatio || 1) * TOUCH_GESTURES.DOUBLE_TAP_DISTANCE_BASE,
    [TOUCH_GESTURES.DOUBLE_TAP_DISTANCE_BASE]
  )

  // Cleanup pending RAF on unmount to prevent state updates after unmount
  useEffect(() => {
    return () => {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current)
        rafIdRef.current = null
      }
    }
  }, [])

  /**
   * Calculate distance between two touch points
   * Uses Pythagorean theorem: √(dx² + dy²)
   *
   * @param {Touch} touch1 - First touch point
   * @param {Touch} touch2 - Second touch point
   * @returns {number} Distance in pixels
   */
  const getPinchDistance = useCallback((touch1, touch2) => {
    const dx = touch2.clientX - touch1.clientX
    const dy = touch2.clientY - touch1.clientY
    return Math.sqrt(dx * dx + dy * dy)
  }, [])

  /**
   * Calculate midpoint between two touch points
   * Used as the center point for pinch-to-zoom
   *
   * @param {Touch} touch1 - First touch point
   * @param {Touch} touch2 - Second touch point
   * @returns {Object} Midpoint {x, y}
   */
  const getPinchMidpoint = useCallback((touch1, touch2) => {
    return {
      x: (touch1.clientX + touch2.clientX) / 2,
      y: (touch1.clientY + touch2.clientY) / 2,
    }
  }, [])

  /**
   * Detect swipe gesture from touch start/end positions
   *
   * @param {number} startX - Starting X position
   * @param {number} startY - Starting Y position
   * @param {number} endX - Ending X position
   * @param {number} endY - Ending Y position
   * @param {number} duration - Time duration in milliseconds
   * @returns {string|null} Swipe direction ('left', 'right') or null
   */
  const detectSwipe = useCallback((startX, startY, endX, endY, duration) => {
    const deltaX = endX - startX
    const deltaY = endY - startY
    const distance = Math.abs(deltaX)
    const velocity = duration > 0 ? distance / duration : 0 // px/ms

    const isHorizontal = Math.abs(deltaX) > Math.abs(deltaY)
    const meetsThreshold = distance >= SWIPE_MIN_DISTANCE
    const meetsVelocity = velocity >= SWIPE_MIN_VELOCITY

    if (isHorizontal && meetsThreshold && meetsVelocity) {
      return deltaX > 0 ? 'right' : 'left'
    }
    return null
  }, [SWIPE_MIN_DISTANCE, SWIPE_MIN_VELOCITY])

  /**
   * Handle touch start event
   * Detects gesture type: single tap, double tap, pinch, or pan
   */
  const handleTouchStart = useCallback(
    (event) => {
      const touches = event.touches

      if (touches.length === 2) {
        // Two-finger pinch gesture
        event.preventDefault()

        const distance = getPinchDistance(touches[0], touches[1])
        const midpoint = getPinchMidpoint(touches[0], touches[1])

        dispatch({
          type: 'PINCH_START',
          payload: {
            distance,
            zoom,
            pan,
            touchStartPos: { x: midpoint.x, y: midpoint.y, timestamp: Date.now() },
          },
        })
      } else if (touches.length === 1) {
        // Single touch: could be tap, double-tap, pan, or swipe
        event.preventDefault()

        const touch = touches[0]
        dispatch({
          type: 'SINGLE_TOUCH_START',
          payload: {
            touchStartPos: {
              x: touch.clientX,
              y: touch.clientY,
              timestamp: Date.now(),
            },
            pan,
          },
        })
      }
    },
    [zoom, pan, getPinchDistance, getPinchMidpoint]
  )

  /**
   * Handle touch move event
   * Updates zoom for pinch or pan position for single-finger drag
   * Uses RAF throttling with queuing to prevent 60+ updates/sec while preserving latest input
   */
  const handleTouchMove = useCallback(
    (event) => {
      const touches = event.touches

      // Prevent default for pinch-to-zoom and single-finger pan when zoomed
      if (
        (touches.length === 2 && isPinching && initialPinchDistance !== null) ||
        (touches.length === 1 && !isPinching && isZoomed && touchStartPos)
      ) {
        event.preventDefault()
      }

      // Capture touch data before RAF (touches list is reused by browser)
      const touchData = Array.from(touches).map((t) => ({
        clientX: t.clientX,
        clientY: t.clientY,
      }))

      // Queue latest touch data (don't drop updates on high-frequency devices)
      latestTouchDataRef.current = touchData

      // RAF throttle: Schedule frame if not already scheduled
      if (rafIdRef.current !== null) {
        return // Update queued, will process on next frame
      }

      // Schedule update for next frame
      rafIdRef.current = requestAnimationFrame(() => {
        const touchData = latestTouchDataRef.current
        if (!touchData) {
          rafIdRef.current = null
          return
        }

        if (touchData.length === 2 && isPinching && initialPinchDistance !== null) {
          // Pinch-to-zoom
          const currentDistance = getPinchDistance(touchData[0], touchData[1])
          const scale = currentDistance / initialPinchDistance
          const newZoom = Math.max(minZoom, Math.min(maxZoom, initialZoom * scale))

          // Calculate new pan to keep pinch center stable
          const midpoint = getPinchMidpoint(touchData[0], touchData[1])
          const rect = imageRef.current?.getBoundingClientRect()

          if (rect) {
            // Get normalized position relative to image (-0.5 to 0.5)
            const relX = (midpoint.x - rect.left) / rect.width - 0.5
            const relY = (midpoint.y - rect.top) / rect.height - 0.5

            // Calculate pan adjustment to keep pinch point stable
            const deltaZoom = newZoom - zoom
            const newPan = {
              x: initialPan.x - relX * deltaZoom * imageWidth,
              y: initialPan.y - relY * deltaZoom * imageHeight,
            }

            setZoom(newZoom)
            setPan(newPan)
          } else {
            setZoom(newZoom)
          }
        } else if (touchData.length === 1 && !isPinching && isZoomed && touchStartPos) {
          // Single-finger pan (only when zoomed)
          const touch = touchData[0]
          const deltaX = touch.clientX - touchStartPos.x
          const deltaY = touch.clientY - touchStartPos.y

          setPan({
            x: initialPan.x + deltaX,
            y: initialPan.y + deltaY,
          })
        }

        // Clear RAF ID after update completes
        rafIdRef.current = null
      })
    },
    [
      isPinching,
      initialPinchDistance,
      initialZoom,
      initialPan,
      isZoomed,
      touchStartPos,
      zoom,
      imageWidth,
      imageHeight,
      imageRef,
      getPinchDistance,
      getPinchMidpoint,
      setZoom,
      setPan,
      minZoom,
      maxZoom,
    ]
  )

  /**
   * Handle touch end event
   * Detects double-tap or swipe gestures
   */
  const handleTouchEnd = useCallback(
    (event) => {
      if (!touchStartPos) {
        // Clean up any dirty state before early return (race condition fix)
        dispatch({ type: 'TOUCH_END' })
        return
      }

      const touch = event.changedTouches?.[0]
      if (!touch) {
        // Pinch end (two fingers lifted)
        dispatch({ type: 'TOUCH_END' })
        return
      }

      const endX = touch.clientX
      const endY = touch.clientY
      const duration = Date.now() - touchStartPos.timestamp
      const distance = Math.sqrt(
        Math.pow(endX - touchStartPos.x, 2) + Math.pow(endY - touchStartPos.y, 2)
      )

      // Check for double-tap (short tap, minimal movement)
      if (distance < DOUBLE_TAP_DISTANCE && duration < TAP_MAX_DURATION) {
        const now = Date.now()
        const timeSinceLastTap = now - lastTapTime

        if (timeSinceLastTap < DOUBLE_TAP_THRESHOLD) {
          // Double-tap detected
          event.preventDefault()

          if (isZoomed) {
            // Reset to 1.0x
            setZoom(1.0)
            setPan({ x: 0, y: 0 })
          } else {
            // Zoom to 2.5x at tap position
            const rect = imageRef.current?.getBoundingClientRect()
            if (rect) {
              const relX = (endX - rect.left) / rect.width - 0.5
              const relY = (endY - rect.top) / rect.height - 0.5

              const deltaZoom = ZOOM_DOUBLE_TAP - zoom
              const newPan = {
                x: -relX * deltaZoom * imageWidth,
                y: -relY * deltaZoom * imageHeight,
              }

              setZoom(ZOOM_DOUBLE_TAP)
              setPan(newPan)
            } else {
              setZoom(ZOOM_DOUBLE_TAP)
            }
          }

          dispatch({ type: 'RESET_TAP' }) // Reset to prevent triple-tap
        } else {
          // First tap of potential double-tap
          dispatch({ type: 'TAP_DETECTED', payload: { timestamp: now } })
        }
      } else if (!isZoomed) {
        // Check for swipe (only when not zoomed)
        const swipeDirection = detectSwipe(
          touchStartPos.x,
          touchStartPos.y,
          endX,
          endY,
          duration
        )

        if (swipeDirection && onNavigate) {
          event.preventDefault()
          if (swipeDirection === 'right') {
            onNavigate('prev')
          } else if (swipeDirection === 'left') {
            onNavigate('next')
          }
        }
      }

      // Clean up
      dispatch({ type: 'TOUCH_END' })
    },
    [
      touchStartPos,
      lastTapTime,
      isZoomed,
      zoom,
      imageWidth,
      imageHeight,
      imageRef,
      detectSwipe,
      onNavigate,
      setZoom,
      setPan,
      DOUBLE_TAP_DISTANCE,
      DOUBLE_TAP_THRESHOLD,
      TAP_MAX_DURATION,
      ZOOM_DOUBLE_TAP,
    ]
  )

  return {
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
  }
}

export default useTouchGestures
