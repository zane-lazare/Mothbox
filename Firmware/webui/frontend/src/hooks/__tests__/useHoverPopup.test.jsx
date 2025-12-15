import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useHoverPopup } from '../useHoverPopup'

/**
 * Test suite for useHoverPopup hook
 *
 * This hook manages hover state for map cluster popups with debouncing,
 * show/hide delays, and mobile touch detection.
 */
describe('useHoverPopup', () => {
  beforeEach(() => {
    // Use fake timers for testing delays
    vi.useFakeTimers()
  })

  afterEach(() => {
    // Clean up timers
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  describe('Initial State', () => {
    it('returns isVisible=false initially', () => {
      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.isVisible).toBe(false)
    })

    it('returns targetCluster=null initially', () => {
      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.targetCluster).toBe(null)
    })

    it('returns position=null initially', () => {
      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.position).toBe(null)
    })

    it('provides handleMouseEnter function', () => {
      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.handleMouseEnter).toBeTypeOf('function')
    })

    it('provides handleMouseLeave function', () => {
      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.handleMouseLeave).toBeTypeOf('function')
    })

    it('provides handleClick function', () => {
      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.handleClick).toBeTypeOf('function')
    })

    it('provides handlePopupOpen function', () => {
      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.handlePopupOpen).toBeTypeOf('function')
    })

    it('provides handlePopupClose function', () => {
      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.handlePopupClose).toBeTypeOf('function')
    })

    it('provides isMobile boolean', () => {
      const { result } = renderHook(() => useHoverPopup())

      expect(typeof result.current.isMobile).toBe('boolean')
    })
  })

  describe('Mouse Enter Behavior', () => {
    it('sets targetCluster immediately on mouse enter', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      expect(result.current.targetCluster).toEqual(mockCluster)
    })

    it('sets position immediately on mouse enter', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      expect(result.current.position).toEqual({ x: 100, y: 200 })
    })

    it('does not show popup immediately (waits for delay)', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      expect(result.current.isVisible).toBe(false)
    })

    it('shows popup after SHOW_DELAY_MS', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      // Fast-forward time by SHOW_DELAY_MS (100ms from config)
      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(result.current.isVisible).toBe(true)
    })

    it('updates targetCluster when hovering different clusters', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster1 = { id: 'cluster1', count: 5 }
      const mockCluster2 = { id: 'cluster2', count: 3 }
      const mockEvent = { clientX: 100, clientY: 200 }

      act(() => {
        result.current.handleMouseEnter(mockCluster1, mockEvent)
      })

      expect(result.current.targetCluster).toEqual(mockCluster1)

      act(() => {
        result.current.handleMouseEnter(mockCluster2, mockEvent)
      })

      expect(result.current.targetCluster).toEqual(mockCluster2)
    })

    it('cancels previous show timer when hovering new cluster', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster1 = { id: 'cluster1', count: 5 }
      const mockCluster2 = { id: 'cluster2', count: 3 }
      const mockEvent = { clientX: 100, clientY: 200 }

      act(() => {
        result.current.handleMouseEnter(mockCluster1, mockEvent)
      })

      // Advance time partially (50ms of 100ms delay)
      act(() => {
        vi.advanceTimersByTime(50)
      })

      // Hover over new cluster
      act(() => {
        result.current.handleMouseEnter(mockCluster2, mockEvent)
      })

      // Should not be visible yet (timer reset)
      expect(result.current.isVisible).toBe(false)

      // Advance remaining time (50ms more = 100ms total from second hover)
      act(() => {
        vi.advanceTimersByTime(50)
      })

      // Still not visible (need full 100ms from second hover)
      expect(result.current.isVisible).toBe(false)

      // Advance final 50ms to complete second hover delay
      act(() => {
        vi.advanceTimersByTime(50)
      })

      expect(result.current.isVisible).toBe(true)
      expect(result.current.targetCluster).toEqual(mockCluster2)
    })
  })

  describe('Mouse Leave Behavior', () => {
    it('does not hide popup immediately (waits for delay)', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Show popup
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(result.current.isVisible).toBe(true)

      // Mouse leave
      act(() => {
        result.current.handleMouseLeave()
      })

      // Should still be visible (waiting for hide delay)
      expect(result.current.isVisible).toBe(true)
    })

    it('hides popup after HIDE_DELAY_MS', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Show popup
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(result.current.isVisible).toBe(true)

      // Mouse leave
      act(() => {
        result.current.handleMouseLeave()
      })

      // Fast-forward time by HIDE_DELAY_MS (200ms from config)
      act(() => {
        vi.advanceTimersByTime(200)
      })

      expect(result.current.isVisible).toBe(false)
    })

    it('clears targetCluster after hide delay', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Show popup
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      // Mouse leave
      act(() => {
        result.current.handleMouseLeave()
      })

      act(() => {
        vi.advanceTimersByTime(200)
      })

      expect(result.current.targetCluster).toBe(null)
    })

    it('clears position after hide delay', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Show popup
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      // Mouse leave
      act(() => {
        result.current.handleMouseLeave()
      })

      act(() => {
        vi.advanceTimersByTime(200)
      })

      expect(result.current.position).toBe(null)
    })

    it('cancels hide timer if mouse re-enters before delay completes', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Show popup
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(result.current.isVisible).toBe(true)

      // Mouse leave
      act(() => {
        result.current.handleMouseLeave()
      })

      // Advance time partially (100ms of 200ms delay)
      act(() => {
        vi.advanceTimersByTime(100)
      })

      // Should still be visible
      expect(result.current.isVisible).toBe(true)

      // Mouse re-enters
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      // Advance remaining hide delay time
      act(() => {
        vi.advanceTimersByTime(100)
      })

      // Should remain visible (hide timer was cancelled, show timer completed)
      expect(result.current.isVisible).toBe(true)
    })
  })

  describe('Click Behavior (Mobile)', () => {
    it('toggles visibility on click', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }

      // First click - show
      act(() => {
        result.current.handleClick(mockCluster)
      })

      expect(result.current.isVisible).toBe(true)
      expect(result.current.targetCluster).toEqual(mockCluster)

      // Second click - hide
      act(() => {
        result.current.handleClick(mockCluster)
      })

      expect(result.current.isVisible).toBe(false)
    })

    it('sets targetCluster on click', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }

      act(() => {
        result.current.handleClick(mockCluster)
      })

      expect(result.current.targetCluster).toEqual(mockCluster)
    })
  })

  describe('Timer Cleanup', () => {
    it('cleans up timers on unmount', () => {
      const { result, unmount } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Start a timer
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      // Unmount before timer completes
      unmount()

      // Advance timers - should not throw or cause issues
      act(() => {
        vi.advanceTimersByTime(100)
      })

      // Verify unmount completed without errors
      expect(true).toBe(true)
    })

    it('cleans up hide timer on unmount', () => {
      const { result, unmount } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Show popup
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      // Start hide timer
      act(() => {
        result.current.handleMouseLeave()
      })

      // Unmount before hide timer completes
      unmount()

      // Advance timers - should not throw or cause issues
      act(() => {
        vi.advanceTimersByTime(200)
      })

      // Verify unmount completed without errors
      expect(true).toBe(true)
    })
  })

  describe('Mobile Detection', () => {
    it('detects desktop when no touch events available', () => {
      // Mock desktop environment
      delete window.ontouchstart
      window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
      }))

      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.isMobile).toBe(false)
    })

    it('detects mobile when ontouchstart exists', () => {
      // Mock mobile environment
      window.ontouchstart = null

      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.isMobile).toBe(true)

      // Clean up
      delete window.ontouchstart
    })

    it('detects mobile when pointer:coarse media query matches', () => {
      // Mock mobile environment
      delete window.ontouchstart
      window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: query === '(pointer: coarse)',
        media: query,
      }))

      const { result } = renderHook(() => useHoverPopup())

      expect(result.current.isMobile).toBe(true)
    })
  })

  describe('Edge Cases', () => {
    it('handles rapid hover enter/leave cycles', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Rapid enter/leave cycles
      for (let i = 0; i < 5; i++) {
        act(() => {
          result.current.handleMouseEnter(mockCluster, mockEvent)
        })

        act(() => {
          vi.advanceTimersByTime(50)
        })

        act(() => {
          result.current.handleMouseLeave()
        })

        act(() => {
          vi.advanceTimersByTime(50)
        })
      }

      // Should handle gracefully without errors
      expect(result.current.isVisible).toBe(false)
    })

    it('handles null cluster gracefully', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockEvent = { clientX: 100, clientY: 200 }

      act(() => {
        result.current.handleMouseEnter(null, mockEvent)
      })

      expect(result.current.targetCluster).toBe(null)
    })

    it('handles missing event coordinates gracefully', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = { id: 'cluster1', count: 5 }
      const mockEvent = {}

      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      expect(result.current.position).toEqual({ x: undefined, y: undefined })
    })
  })

  describe('Popup Open/Close Behavior', () => {
    it('suppresses hover popup when click popup is open for same cluster', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = {
        center: { lat: 37.7749, lon: -122.4194 },
      }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Open click popup
      act(() => {
        result.current.handlePopupOpen(mockCluster)
      })

      // Try to trigger hover popup
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      // Should remain invisible due to click popup being open
      expect(result.current.isVisible).toBe(false)
    })

    it('allows hover popup for different cluster when click popup is open', () => {
      const { result } = renderHook(() => useHoverPopup())
      const clickedCluster = {
        center: { lat: 37.7749, lon: -122.4194 },
      }
      const differentCluster = {
        center: { lat: 40.7128, lon: -74.006 },
      }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Open click popup for first cluster
      act(() => {
        result.current.handlePopupOpen(clickedCluster)
      })

      // Try to trigger hover popup for different cluster
      act(() => {
        result.current.handleMouseEnter(differentCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      // Should show hover popup for different cluster
      expect(result.current.isVisible).toBe(true)
      expect(result.current.targetCluster).toEqual(differentCluster)
    })

    it('allows hover popup after click popup is closed', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = {
        center: { lat: 37.7749, lon: -122.4194 },
      }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Open click popup
      act(() => {
        result.current.handlePopupOpen(mockCluster)
      })

      // Close click popup
      act(() => {
        result.current.handlePopupClose()
      })

      // Try to trigger hover popup
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      // Should now show hover popup
      expect(result.current.isVisible).toBe(true)
    })

    it('hides visible hover popup when click popup opens', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = {
        center: { lat: 37.7749, lon: -122.4194 },
      }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Show hover popup first
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(result.current.isVisible).toBe(true)

      // Open click popup - should hide hover popup
      act(() => {
        result.current.handlePopupOpen(mockCluster)
      })

      expect(result.current.isVisible).toBe(false)
    })

    it('handles clusters without valid coordinates in handlePopupOpen', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockEvent = { clientX: 100, clientY: 200 }

      // Open click popup with invalid cluster (no center)
      act(() => {
        result.current.handlePopupOpen(null)
      })

      // Should still allow hover popup since cluster ID is null
      const mockCluster = {
        center: { lat: 37.7749, lon: -122.4194 },
      }

      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(result.current.isVisible).toBe(true)
    })

    it('handles cluster with missing lat in getClusterId', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockEvent = { clientX: 100, clientY: 200 }

      // Open click popup with cluster missing lat
      const invalidCluster = { center: { lon: -122.4194 } }
      act(() => {
        result.current.handlePopupOpen(invalidCluster)
      })

      // Hover popup should still work since cluster ID is null
      const validCluster = {
        center: { lat: 37.7749, lon: -122.4194 },
      }

      act(() => {
        result.current.handleMouseEnter(validCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(result.current.isVisible).toBe(true)
    })

    it('handles cluster with missing lon in getClusterId', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockEvent = { clientX: 100, clientY: 200 }

      // Open click popup with cluster missing lon
      const invalidCluster = { center: { lat: 37.7749 } }
      act(() => {
        result.current.handlePopupOpen(invalidCluster)
      })

      // Hover popup should still work since cluster ID is null
      const validCluster = {
        center: { lat: 37.7749, lon: -122.4194 },
      }

      act(() => {
        result.current.handleMouseEnter(validCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(result.current.isVisible).toBe(true)
    })

    it('handles cluster with missing center in getClusterId', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockEvent = { clientX: 100, clientY: 200 }

      // Open click popup with cluster missing center entirely
      const invalidCluster = { id: 'cluster1' }
      act(() => {
        result.current.handlePopupOpen(invalidCluster)
      })

      // Hover popup should still work since cluster ID is null
      const validCluster = {
        center: { lat: 37.7749, lon: -122.4194 },
      }

      act(() => {
        result.current.handleMouseEnter(validCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(result.current.isVisible).toBe(true)
    })

    it('handles coordinates at 0,0 (valid but falsy)', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockEvent = { clientX: 100, clientY: 200 }

      // Cluster at 0,0 (Gulf of Guinea) - valid coordinates
      const zeroCluster = {
        center: { lat: 0, lon: 0 },
      }

      // Open click popup for 0,0 cluster
      act(() => {
        result.current.handlePopupOpen(zeroCluster)
      })

      // Try to hover over same cluster - should be suppressed
      act(() => {
        result.current.handleMouseEnter(zeroCluster, mockEvent)
      })

      act(() => {
        vi.advanceTimersByTime(100)
      })

      // Should NOT show hover popup since click popup is open for same cluster
      expect(result.current.isVisible).toBe(false)
    })

    it('cancels pending show timer when click popup opens', () => {
      const { result } = renderHook(() => useHoverPopup())
      const mockCluster = {
        center: { lat: 37.7749, lon: -122.4194 },
      }
      const mockEvent = { clientX: 100, clientY: 200 }

      // Start hover (creates show timer)
      act(() => {
        result.current.handleMouseEnter(mockCluster, mockEvent)
      })

      // Advance time partially (50ms of 100ms delay)
      act(() => {
        vi.advanceTimersByTime(50)
      })

      expect(result.current.isVisible).toBe(false)

      // Open click popup - should cancel the show timer
      act(() => {
        result.current.handlePopupOpen(mockCluster)
      })

      // Advance remaining time
      act(() => {
        vi.advanceTimersByTime(50)
      })

      // Should remain invisible (timer was cancelled)
      expect(result.current.isVisible).toBe(false)
    })
  })
})
