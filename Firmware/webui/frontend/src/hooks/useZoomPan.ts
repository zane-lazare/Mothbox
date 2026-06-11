import { useState, useCallback, useRef, useEffect } from 'react'

interface PanPosition {
  x: number
  y: number
}

interface Boundaries {
  maxX: number
  maxY: number
}

interface UseZoomPanConfig {
  minZoom?: number
  maxZoom?: number
  zoomStep?: number
  imageWidth?: number
  imageHeight?: number
  containerWidth?: number
  containerHeight?: number
}

interface UseZoomPanResult {
  zoom: number
  pan: PanPosition
  setZoom: (newZoom: number) => void
  setPan: (newPan: PanPosition) => void
  handleZoomIn: () => void
  handleZoomOut: () => void
  handleWheel: (event: React.WheelEvent) => void
  resetZoom: () => void
}

/**
 * Custom hook for managing zoom and pan state in the photo lightbox.
 *
 * Handles desktop interactions (mouse wheel zoom, click-drag pan) with
 * boundary constraints to prevent over-panning. Automatically resets pan
 * when zoom returns to 1.0.
 *
 * @hook
 * @param {Object} config - Hook configuration
 * @param {number} config.minZoom - Minimum zoom level (e.g., 1.0 = 100%)
 * @param {number} config.maxZoom - Maximum zoom level (e.g., 5.0 = 500%)
 * @param {number} config.zoomStep - Zoom increment/decrement per step (e.g., 0.5 = 50%)
 * @param {number} config.imageWidth - Natural width of the image in pixels
 * @param {number} config.imageHeight - Natural height of the image in pixels
 * @param {number} config.containerWidth - Container width in pixels
 * @param {number} config.containerHeight - Container height in pixels
 *
 * @returns {Object} Zoom and pan state and handlers
 * @returns {number} returns.zoom - Current zoom level (1.0 = 100%, 2.0 = 200%, etc.)
 * @returns {Object} returns.pan - Current pan offset {x, y} in pixels
 * @returns {Function} returns.setZoom - Set zoom level (automatically clamped to min/max)
 * @returns {Function} returns.setPan - Set pan offset (automatically constrained to boundaries)
 * @returns {Function} returns.handleZoomIn - Increment zoom by zoomStep
 * @returns {Function} returns.handleZoomOut - Decrement zoom by zoomStep
 * @returns {Function} returns.handleWheel - Wheel event handler for cursor-relative zoom
 * @returns {Function} returns.resetZoom - Reset to 1.0x zoom and {0, 0} pan
 *
 * @example
 * const { zoom, pan, handleZoomIn, handleWheel } = useZoomPan({
 *   minZoom: 1.0,
 *   maxZoom: 5.0,
 *   zoomStep: 0.5,
 *   imageWidth: 1920,
 *   imageHeight: 1080,
 *   containerWidth: 1280,
 *   containerHeight: 720,
 * })
 *
 * // Apply to image element
 * <img
 *   style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
 *   onWheel={handleWheel}
 * />
 *
 * @algorithm Pan Boundary Calculation
 * - Scaled dimensions = natural dimensions × zoom
 * - Max pan offset = (scaled dimension - container dimension) / 2
 * - Constrained pan = clamp(pan, -maxOffset, maxOffset)
 *
 * @algorithm Cursor-Relative Zoom (handleWheel)
 * 1. Get cursor position relative to image center (-0.5 to 0.5)
 * 2. Calculate zoom delta from wheel direction
 * 3. Adjust pan to keep cursor position stable: pan' = pan - cursor × delta × imageSize
 * 4. Apply boundary constraints to final pan
 */
function useZoomPan({
  minZoom = 1.0,
  maxZoom = 5.0,
  zoomStep = 0.5,
  imageWidth = 0,
  imageHeight = 0,
  containerWidth = 0,
  containerHeight = 0,
}: UseZoomPanConfig): UseZoomPanResult {
  const [zoom, setZoomState] = useState(1.0)
  const [pan, setPanState] = useState<PanPosition>({ x: 0, y: 0 })

  // Use refs to track current zoom/pan without triggering callback recreations
  const zoomRef = useRef(zoom)
  const panRef = useRef(pan)
  useEffect(() => {
    zoomRef.current = zoom
    panRef.current = pan
  }, [zoom, pan])

  /**
   * Calculate pan boundaries based on current zoom and dimensions
   *
   * @param {number} currentZoom - Current zoom level
   * @returns {Object} Boundaries {maxX, maxY}
   */
  const getBoundaries = useCallback(
    (currentZoom: number): Boundaries => {
      // Guard against invalid dimensions to prevent division by zero or NaN
      if (containerWidth <= 0 || containerHeight <= 0 || imageWidth <= 0 || imageHeight <= 0) {
        return { maxX: 0, maxY: 0 }
      }

      const scaledWidth = imageWidth * currentZoom
      const scaledHeight = imageHeight * currentZoom

      const maxX = Math.max(0, (scaledWidth - containerWidth) / 2)
      const maxY = Math.max(0, (scaledHeight - containerHeight) / 2)

      return { maxX, maxY }
    },
    [imageWidth, imageHeight, containerWidth, containerHeight]
  )

  /**
   * Constrain pan position to boundaries
   *
   * @param {Object} panPosition - Pan position {x, y}
   * @param {Object} boundaries - Boundaries {maxX, maxY}
   * @returns {Object} Constrained pan position {x, y}
   */
  const constrainPan = useCallback((panPosition: PanPosition, boundaries: Boundaries): PanPosition => {
    return {
      x: Math.max(-boundaries.maxX, Math.min(boundaries.maxX, panPosition.x)),
      y: Math.max(-boundaries.maxY, Math.min(boundaries.maxY, panPosition.y)),
    }
  }, [])

  /**
   * Set zoom level (clamped to min/max)
   *
   * Uses functional setState to avoid race conditions from multiple state updates.
   *
   * @param {number} newZoom - New zoom level
   */
  const setZoom = useCallback(
    (newZoom: number) => {
      const clampedZoom = Math.max(minZoom, Math.min(maxZoom, newZoom))
      setZoomState(clampedZoom)

      // Use functional update to avoid race conditions
      setPanState((currentPan) => {
        if (clampedZoom === 1.0) {
          // Reset pan when zoom returns to 1.0
          return { x: 0, y: 0 }
        }
        // Recalculate boundaries and constrain existing pan
        const boundaries = getBoundaries(clampedZoom)
        return constrainPan(currentPan, boundaries)
      })
    },
    [minZoom, maxZoom, getBoundaries, constrainPan]
  )

  /**
   * Set pan position (constrained to boundaries)
   *
   * @param {Object} newPan - New pan position {x, y}
   *
   * Note: Uses zoomRef instead of zoom dependency to prevent callback recreation
   * on every zoom change, which would cause event listener churn in PhotoLightbox
   */
  const setPan = useCallback(
    (newPan: PanPosition) => {
      const boundaries = getBoundaries(zoomRef.current)
      const constrainedPan = constrainPan(newPan, boundaries)
      setPanState(constrainedPan)
    },
    [getBoundaries, constrainPan]
  )

  /**
   * Increment zoom by zoomStep
   */
  const handleZoomIn = useCallback(() => {
    setZoom(zoom + zoomStep)
  }, [zoom, zoomStep, setZoom])

  /**
   * Decrement zoom by zoomStep
   */
  const handleZoomOut = useCallback(() => {
    setZoom(zoom - zoomStep)
  }, [zoom, zoomStep, setZoom])

  /**
   * Reset zoom to 1.0 and pan to {0, 0}
   */
  const resetZoom = useCallback(() => {
    setZoomState(1.0)
    setPanState({ x: 0, y: 0 })
  }, [])

  /**
   * Handle wheel events for zooming
   * Zooms in/out at cursor position to keep point under cursor stationary
   *
   * Uses zoomRef and panRef to avoid recreating callback on every zoom/pan change,
   * which would cause event listener churn in PhotoLightbox.
   *
   * @param {WheelEvent} event - Wheel event
   */
  const handleWheel = useCallback(
    (event: React.WheelEvent) => {
      event.preventDefault()

      const currentZoom = zoomRef.current
      const currentPan = panRef.current

      const delta = event.deltaY
      const zoomDirection = delta > 0 ? -1 : 1
      const newZoom = Math.max(minZoom, Math.min(maxZoom, currentZoom + zoomDirection * zoomStep))

      if (newZoom === currentZoom) {
        // No zoom change, already at boundary
        return
      }

      // Get cursor position relative to image
      const rect = (event.currentTarget as HTMLElement)?.getBoundingClientRect()
      if (!rect) {
        // Element not available (unmounted or invalid), skip cursor-relative zoom
        return
      }

      const x = (event.clientX - rect.left) / rect.width - 0.5 // Normalized -0.5 to 0.5
      const y = (event.clientY - rect.top) / rect.height - 0.5

      // Calculate new pan to keep cursor position stable
      const deltaZoom = newZoom - currentZoom
      const newPan = {
        x: currentPan.x - x * deltaZoom * imageWidth,
        y: currentPan.y - y * deltaZoom * imageHeight,
      }

      // Update zoom first
      setZoomState(newZoom)

      // Then update pan with constraints
      if (newZoom === 1.0) {
        setPanState({ x: 0, y: 0 })
      } else {
        const boundaries = getBoundaries(newZoom)
        setPanState(constrainPan(newPan, boundaries))
      }
    },
    [minZoom, maxZoom, zoomStep, imageWidth, imageHeight, getBoundaries, constrainPan]
  )

  return {
    zoom,
    pan,
    setZoom,
    setPan,
    handleZoomIn,
    handleZoomOut,
    handleWheel,
    resetZoom,
  }
}

export default useZoomPan
