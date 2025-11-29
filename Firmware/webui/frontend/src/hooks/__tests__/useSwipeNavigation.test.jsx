import { describe, it, expect, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSwipeNavigation } from '../useSwipeNavigation'
import { HOVER_POPUP_CONFIG } from '../../constants/config'

describe('useSwipeNavigation', () => {
  describe('Initial State', () => {
    it('returns correct initial state', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      expect(result.current.currentPage).toBe(0)
      expect(result.current.totalPages).toBe(3)
      expect(result.current.startIndex).toBe(0)
      expect(result.current.endIndex).toBe(9)
      expect(result.current.handlers).toHaveProperty('onTouchStart')
      expect(result.current.handlers).toHaveProperty('onTouchMove')
      expect(result.current.handlers).toHaveProperty('onTouchEnd')
      expect(typeof result.current.goToPage).toBe('function')
      expect(typeof result.current.goNext).toBe('function')
      expect(typeof result.current.goPrev).toBe('function')
    })

    it('uses default visibleItems from config', () => {
      const { result } = renderHook(() => useSwipeNavigation({ totalItems: 27 }))

      expect(result.current.endIndex).toBe(HOVER_POPUP_CONFIG.MAX_PHOTOS)
    })
  })

  describe('Page Calculations', () => {
    it('calculates totalPages correctly', () => {
      const { result: result1 } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )
      expect(result1.current.totalPages).toBe(3) // 27 / 9 = 3

      const { result: result2 } = renderHook(() =>
        useSwipeNavigation({ totalItems: 28, visibleItems: 9 })
      )
      expect(result2.current.totalPages).toBe(4) // 28 / 9 = 3.11... → 4

      const { result: result3 } = renderHook(() =>
        useSwipeNavigation({ totalItems: 5, visibleItems: 9 })
      )
      expect(result3.current.totalPages).toBe(1) // 5 / 9 = 0.55... → 1
    })

    it('calculates startIndex and endIndex correctly for first page', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      expect(result.current.startIndex).toBe(0)
      expect(result.current.endIndex).toBe(9)
    })

    it('calculates startIndex and endIndex correctly for middle page', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      act(() => {
        result.current.goToPage(1)
      })

      expect(result.current.startIndex).toBe(9)
      expect(result.current.endIndex).toBe(18)
    })

    it('calculates startIndex and endIndex correctly for last page', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      act(() => {
        result.current.goToPage(2)
      })

      expect(result.current.startIndex).toBe(18)
      expect(result.current.endIndex).toBe(27)
    })

    it('handles partial last page correctly', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 25, visibleItems: 9 })
      )

      act(() => {
        result.current.goToPage(2)
      })

      expect(result.current.startIndex).toBe(18)
      expect(result.current.endIndex).toBe(25) // Only 7 items on last page
    })
  })

  describe('Page Navigation', () => {
    it('goNext advances to next page', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      act(() => {
        result.current.goNext()
      })

      expect(result.current.currentPage).toBe(1)
      expect(result.current.startIndex).toBe(9)
      expect(result.current.endIndex).toBe(18)
    })

    it('goPrev goes back to previous page', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      act(() => {
        result.current.goToPage(1)
      })

      act(() => {
        result.current.goPrev()
      })

      expect(result.current.currentPage).toBe(0)
      expect(result.current.startIndex).toBe(0)
      expect(result.current.endIndex).toBe(9)
    })

    it('goNext does nothing on last page', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      act(() => {
        result.current.goToPage(2) // Last page
      })

      act(() => {
        result.current.goNext()
      })

      expect(result.current.currentPage).toBe(2) // Still on last page
    })

    it('goPrev does nothing on first page', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      act(() => {
        result.current.goPrev()
      })

      expect(result.current.currentPage).toBe(0) // Still on first page
    })

    it('goToPage clamps to valid page range', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      act(() => {
        result.current.goToPage(-1)
      })
      expect(result.current.currentPage).toBe(0)

      act(() => {
        result.current.goToPage(5)
      })
      expect(result.current.currentPage).toBe(2) // Max page = 2
    })

    it('calls onPageChange callback when page changes', () => {
      const onPageChange = vi.fn()
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9, onPageChange })
      )

      act(() => {
        result.current.goNext()
      })

      expect(onPageChange).toHaveBeenCalledWith(9, 18)
    })
  })

  describe('Touch Gestures', () => {
    it('swipe left triggers goNext', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      // Simulate swipe left (next)
      act(() => {
        result.current.handlers.onTouchStart({
          touches: [{ clientX: 200, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchMove({
          touches: [{ clientX: 100, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchEnd()
      })

      expect(result.current.currentPage).toBe(1)
    })

    it('swipe right triggers goPrev', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      // Start on page 1
      act(() => {
        result.current.goToPage(1)
      })

      // Simulate swipe right (previous)
      act(() => {
        result.current.handlers.onTouchStart({
          touches: [{ clientX: 100, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchMove({
          touches: [{ clientX: 200, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchEnd()
      })

      expect(result.current.currentPage).toBe(0)
    })

    it('small swipe (below threshold) does nothing', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      // Simulate small swipe (less than SWIPE_THRESHOLD = 50px)
      act(() => {
        result.current.handlers.onTouchStart({
          touches: [{ clientX: 100, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchMove({
          touches: [{ clientX: 130, clientY: 100 }], // Only 30px
        })
      })

      act(() => {
        result.current.handlers.onTouchEnd()
      })

      expect(result.current.currentPage).toBe(0) // No change
    })

    it('vertical swipe does nothing', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      // Simulate vertical swipe
      act(() => {
        result.current.handlers.onTouchStart({
          touches: [{ clientX: 100, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchMove({
          touches: [{ clientX: 100, clientY: 200 }], // Vertical swipe (100px down)
        })
      })

      act(() => {
        result.current.handlers.onTouchEnd()
      })

      expect(result.current.currentPage).toBe(0) // No change
    })

    it('swipe threshold matches config constant', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      // Swipe exactly at threshold
      const threshold = HOVER_POPUP_CONFIG.SWIPE_THRESHOLD

      act(() => {
        result.current.handlers.onTouchStart({
          touches: [{ clientX: 200, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchMove({
          touches: [{ clientX: 200 - threshold - 1, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchEnd()
      })

      expect(result.current.currentPage).toBe(1) // Should trigger
    })
  })

  describe('Edge Cases', () => {
    it('handles zero totalItems', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 0, visibleItems: 9 })
      )

      expect(result.current.totalPages).toBe(0)
      expect(result.current.startIndex).toBe(0)
      expect(result.current.endIndex).toBe(0)
    })

    it('handles single item', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 1, visibleItems: 9 })
      )

      expect(result.current.totalPages).toBe(1)
      expect(result.current.startIndex).toBe(0)
      expect(result.current.endIndex).toBe(1)
    })

    it('handles visibleItems larger than totalItems', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 5, visibleItems: 9 })
      )

      expect(result.current.totalPages).toBe(1)
      expect(result.current.startIndex).toBe(0)
      expect(result.current.endIndex).toBe(5)
    })

    it('prevents navigation beyond boundaries with swipe', () => {
      const { result } = renderHook(() =>
        useSwipeNavigation({ totalItems: 27, visibleItems: 9 })
      )

      // Try to swipe right on first page
      act(() => {
        result.current.handlers.onTouchStart({
          touches: [{ clientX: 100, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchMove({
          touches: [{ clientX: 200, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchEnd()
      })

      expect(result.current.currentPage).toBe(0)

      // Go to last page
      act(() => {
        result.current.goToPage(2)
      })

      // Try to swipe left on last page
      act(() => {
        result.current.handlers.onTouchStart({
          touches: [{ clientX: 200, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchMove({
          touches: [{ clientX: 100, clientY: 100 }],
        })
      })

      act(() => {
        result.current.handlers.onTouchEnd()
      })

      expect(result.current.currentPage).toBe(2)
    })
  })
})
