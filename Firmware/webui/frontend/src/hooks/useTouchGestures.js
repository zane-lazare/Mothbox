import { useState, useCallback, useRef } from 'react'

/**
 * Custom hook for handling touch gestures on mobile devices
 *
 * Provides:
 * - Pinch-to-zoom (two-finger zoom)
 * - Swipe navigation (left/right)
 * - Double-tap zoom toggle
 * - Touch pan when zoomed
 *
 * @param {Object} config - Configuration object
 * @param {React.RefObject} config.imageRef - Reference to the image element
 * @param {number} config.zoom - Current zoom level
 * @param {Function} config.setZoom - Function to update zoom level
 * @param {Object} config.pan - Current pan position {x, y}
 * @param {Function} config.setPan - Function to update pan position
 * @param {Function} config.onNavigate - Callback for swipe navigation (receives 'prev' or 'next')
 * @param {boolean} config.isZoomed - Whether currently zoomed (zoom > 1.0)
 * @param {number} config.imageWidth - Natural width of the image
 * @param {number} config.imageHeight - Natural height of the image
 * @param {number} config.containerWidth - Width of the container
 * @param {number} config.containerHeight - Height of the container
 *
 * @returns {Object} Touch event handlers
 * @returns {Function} handleTouchStart - Touch start event handler
 * @returns {Function} handleTouchMove - Touch move event handler
 * @returns {Function} handleTouchEnd - Touch end event handler
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
  containerWidth,
  containerHeight,
}) {
  // Touch gesture state
  const [touchStartPos, setTouchStartPos] = useState(null)
  const [initialPinchDistance, setInitialPinchDistance] = useState(null)
  const [initialZoom, setInitialZoom] = useState(1.0)
  const [initialPan, setInitialPan] = useState({ x: 0, y: 0 })
  const [lastTapTime, setLastTapTime] = useState(0)
  const [isPinching, setIsPinching] = useState(false)

  // Use ref for animation frame to avoid stale closures
  const animationFrameRef = useRef(null)

  // Constants
  const MIN_ZOOM = 1.0
  const MAX_ZOOM = 5.0
  const DOUBLE_TAP_THRESHOLD = 300 // ms
  const SWIPE_MIN_DISTANCE = 50 // pixels
  const SWIPE_MIN_VELOCITY = 0.3 // pixels per millisecond
  const ZOOM_DOUBLE_TAP = 2.5 // zoom level for double-tap

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
  }, [])

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
        setIsPinching(true)

        const distance = getPinchDistance(touches[0], touches[1])
        const midpoint = getPinchMidpoint(touches[0], touches[1])

        setInitialPinchDistance(distance)
        setInitialZoom(zoom)
        setInitialPan(pan)
        setTouchStartPos({ x: midpoint.x, y: midpoint.y, timestamp: Date.now() })
      } else if (touches.length === 1) {
        // Single touch: could be tap, double-tap, pan, or swipe
        event.preventDefault()

        const touch = touches[0]
        setTouchStartPos({
          x: touch.clientX,
          y: touch.clientY,
          timestamp: Date.now(),
        })

        // Store initial pan for panning gestures
        setInitialPan(pan)

        // Reset pinch state
        setIsPinching(false)
        setInitialPinchDistance(null)
      }
    },
    [zoom, pan, getPinchDistance, getPinchMidpoint]
  )

  /**
   * Handle touch move event
   * Updates zoom for pinch or pan position for single-finger drag
   */
  const handleTouchMove = useCallback(
    (event) => {
      const touches = event.touches

      if (touches.length === 2 && isPinching && initialPinchDistance !== null) {
        // Pinch-to-zoom
        event.preventDefault()

        const currentDistance = getPinchDistance(touches[0], touches[1])
        const scale = currentDistance / initialPinchDistance
        const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, initialZoom * scale))

        // Calculate new pan to keep pinch center stable
        const midpoint = getPinchMidpoint(touches[0], touches[1])
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
      } else if (touches.length === 1 && !isPinching && isZoomed && touchStartPos) {
        // Single-finger pan (only when zoomed)
        event.preventDefault()

        const touch = touches[0]
        const deltaX = touch.clientX - touchStartPos.x
        const deltaY = touch.clientY - touchStartPos.y

        setPan({
          x: initialPan.x + deltaX,
          y: initialPan.y + deltaY,
        })
      }
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
    ]
  )

  /**
   * Handle touch end event
   * Detects double-tap or swipe gestures
   */
  const handleTouchEnd = useCallback(
    (event) => {
      // Cancel any pending animation frame
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
        animationFrameRef.current = null
      }

      if (!touchStartPos) return

      const touch = event.changedTouches?.[0]
      if (!touch) {
        // Pinch end (two fingers lifted)
        setIsPinching(false)
        setInitialPinchDistance(null)
        setTouchStartPos(null)
        return
      }

      const endX = touch.clientX
      const endY = touch.clientY
      const duration = Date.now() - touchStartPos.timestamp
      const distance = Math.sqrt(
        Math.pow(endX - touchStartPos.x, 2) + Math.pow(endY - touchStartPos.y, 2)
      )

      // Check for double-tap (short tap, minimal movement)
      if (distance < 10 && duration < 200) {
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

          setLastTapTime(0) // Reset to prevent triple-tap
        } else {
          // First tap of potential double-tap
          setLastTapTime(now)
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
      setIsPinching(false)
      setInitialPinchDistance(null)
      setTouchStartPos(null)
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
    ]
  )

  return {
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
  }
}

export default useTouchGestures
