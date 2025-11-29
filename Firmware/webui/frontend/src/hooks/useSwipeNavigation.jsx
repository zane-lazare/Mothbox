import { useState, useCallback, useRef } from 'react'
import { HOVER_POPUP_CONFIG } from '../constants/config'

/**
 * Custom hook for swipe-based navigation with touch gestures
 *
 * Provides paginated navigation with touch/swipe support for mobile devices.
 * Calculates visible item ranges and handles swipe gestures to navigate between pages.
 *
 * @param {Object} options - Hook configuration
 * @param {number} options.totalItems - Total number of items to navigate
 * @param {number} [options.visibleItems=9] - Number of visible items per page (default from config)
 * @param {Function} [options.onPageChange] - Callback when page changes, receives (startIndex, endIndex)
 *
 * @returns {Object} Navigation state and handlers
 * @returns {number} return.currentPage - Current page number (0-indexed)
 * @returns {number} return.totalPages - Total number of pages
 * @returns {number} return.startIndex - First visible item index
 * @returns {number} return.endIndex - Last visible item index (exclusive)
 * @returns {Object} return.handlers - Touch event handlers
 * @returns {Function} return.handlers.onTouchStart - Touch start event handler
 * @returns {Function} return.handlers.onTouchMove - Touch move event handler
 * @returns {Function} return.handlers.onTouchEnd - Touch end event handler
 * @returns {Function} return.goToPage - Navigate to specific page (pageNumber)
 * @returns {Function} return.goNext - Navigate to next page
 * @returns {Function} return.goPrev - Navigate to previous page
 *
 * @example
 * const {
 *   currentPage,
 *   totalPages,
 *   handlers,
 *   goNext,
 *   goPrev
 * } = useSwipeNavigation({
 *   totalItems: 27,
 *   visibleItems: 9,
 *   onPageChange: (start, end) => console.log(`Showing items ${start}-${end}`)
 * })
 *
 * // Apply handlers to container using spread syntax
 * // Example: <div {...handlers}>content</div>
 */
export function useSwipeNavigation({
  totalItems,
  visibleItems = HOVER_POPUP_CONFIG.MAX_PHOTOS,
  onPageChange,
}) {
  const [currentPage, setCurrentPage] = useState(0)
  const touchStartRef = useRef({ x: 0, y: 0 })
  const touchEndRef = useRef({ x: 0, y: 0 })

  const totalPages = Math.ceil(totalItems / visibleItems)

  const startIndex = currentPage * visibleItems
  const endIndex = Math.min(startIndex + visibleItems, totalItems)

  const goToPage = useCallback(
    (page) => {
      const newPage = Math.max(0, Math.min(page, totalPages - 1))
      setCurrentPage(newPage)
      const newStart = newPage * visibleItems
      const newEnd = Math.min(newStart + visibleItems, totalItems)
      onPageChange?.(newStart, newEnd)
    },
    [totalPages, visibleItems, totalItems, onPageChange]
  )

  const goNext = useCallback(() => {
    if (currentPage < totalPages - 1) {
      goToPage(currentPage + 1)
    }
  }, [currentPage, totalPages, goToPage])

  const goPrev = useCallback(() => {
    if (currentPage > 0) {
      goToPage(currentPage - 1)
    }
  }, [currentPage, goToPage])

  const onTouchStart = useCallback((e) => {
    touchStartRef.current = {
      x: e.touches[0].clientX,
      y: e.touches[0].clientY,
    }
  }, [])

  const onTouchMove = useCallback((e) => {
    touchEndRef.current = {
      x: e.touches[0].clientX,
      y: e.touches[0].clientY,
    }
  }, [])

  const onTouchEnd = useCallback(() => {
    const deltaX = touchStartRef.current.x - touchEndRef.current.x
    const deltaY = touchStartRef.current.y - touchEndRef.current.y

    // Only trigger if horizontal swipe is greater than vertical
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      if (deltaX > HOVER_POPUP_CONFIG.SWIPE_THRESHOLD) {
        goNext() // Swipe left = next page
      } else if (deltaX < -HOVER_POPUP_CONFIG.SWIPE_THRESHOLD) {
        goPrev() // Swipe right = previous page
      }
    }
  }, [goNext, goPrev])

  return {
    currentPage,
    totalPages,
    startIndex,
    endIndex,
    handlers: {
      onTouchStart,
      onTouchMove,
      onTouchEnd,
    },
    goToPage,
    goNext,
    goPrev,
  }
}
