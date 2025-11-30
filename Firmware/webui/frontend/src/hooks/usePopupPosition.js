import { useMemo, useEffect, useState, useLayoutEffect } from 'react'
import { HOVER_POPUP_CONFIG } from '../constants/config'

/**
 * Hook for calculating viewport-aware popup positioning
 *
 * @param {Object} options - Configuration options
 * @param {Object} options.triggerPosition - {x, y} position of trigger element
 * @param {number} [options.popupWidth] - Width of popup
 * @param {number} [options.popupHeight] - Estimated height of popup (used as fallback)
 * @param {number} [options.offset] - Offset from trigger position
 * @param {boolean} [options.isVisible] - Whether popup is visible
 * @param {Object} [options.popupRef] - Ref to popup element for dynamic height measurement
 * @returns {Object} { position: {left, top}, placement: 'above'|'below', measuredHeight }
 */
export function usePopupPosition({
  triggerPosition,
  popupWidth = HOVER_POPUP_CONFIG.POPUP_WIDTH,
  popupHeight = 350,
  offset = 10,
  isVisible = false,
  popupRef = null,
}) {
  const [viewport, setViewport] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1024,
    height: typeof window !== 'undefined' ? window.innerHeight : 768,
  })

  // Dynamic height measurement from actual popup element
  const [measuredHeight, setMeasuredHeight] = useState(null)

  // Measure popup height after render using useLayoutEffect
  // This runs synchronously after DOM mutations but before paint
  useLayoutEffect(() => {
    if (popupRef?.current && isVisible) {
      const rect = popupRef.current.getBoundingClientRect()
      if (rect.height > 0) {
        setMeasuredHeight(rect.height)
      }
    } else if (!isVisible) {
      // Reset measured height when popup closes
      setMeasuredHeight(null)
    }
  }, [isVisible, popupRef])

  // Use measured height if available, otherwise fall back to estimated
  const actualHeight = measuredHeight ?? popupHeight

  // Update viewport on resize
  useEffect(() => {
    if (typeof window === 'undefined') return

    const handleResize = () => {
      setViewport({
        width: window.innerWidth,
        height: window.innerHeight,
      })
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const { position, placement } = useMemo(() => {
    if (!triggerPosition || !isVisible) {
      return { position: { left: 0, top: 0 }, placement: 'below' }
    }

    const { x, y } = triggerPosition
    const margin = 10 // Keep popup away from viewport edges

    // Calculate available space
    const spaceBelow = viewport.height - y - offset
    const spaceAbove = y - offset

    // Determine vertical placement (use actualHeight which may be measured or estimated)
    let top
    let placement
    if (spaceBelow >= actualHeight + margin) {
      // Enough space below
      top = y + offset
      placement = 'below'
    } else if (spaceAbove >= actualHeight + margin) {
      // Place above
      top = y - actualHeight - offset
      placement = 'above'
    } else {
      // Not enough space either way, place where there's more room
      if (spaceBelow >= spaceAbove) {
        top = y + offset
        placement = 'below'
      } else {
        top = Math.max(margin, y - actualHeight - offset)
        placement = 'above'
      }
    }

    // Determine horizontal position (try to center on trigger, but stay in bounds)
    let left = x - popupWidth / 2

    // Clamp to viewport
    left = Math.max(margin, Math.min(left, viewport.width - popupWidth - margin))
    top = Math.max(margin, Math.min(top, viewport.height - actualHeight - margin))

    return {
      position: { left, top },
      placement,
    }
  }, [triggerPosition, popupWidth, actualHeight, offset, isVisible, viewport])

  return { position, placement, measuredHeight }
}
