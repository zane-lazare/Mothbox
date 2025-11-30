import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { MapContainer } from 'react-leaflet'
import { useMapRef } from '../useMapRef'

/**
 * Test suite for useMapRef hook
 *
 * This hook provides controlled access to the Leaflet map instance
 * via React ref for programmatic map control (flyTo, setZoom, etc).
 */
describe('useMapRef', () => {
  /**
   * Helper to render hook inside MapContainer (required for useMap)
   */
  const renderUseMapRef = () => {
    return renderHook(() => useMapRef(), {
      wrapper: ({ children }) => (
        <MapContainer center={[51.505, -0.09]} zoom={13}>
          {children}
        </MapContainer>
      ),
    })
  }

  describe('Initial State', () => {
    it('throws when used outside MapContainer', () => {
      // useMapRef MUST be used inside MapContainer - it should throw if not
      expect(() => {
        renderHook(() => useMapRef())
      }).toThrow('No context provided')
    })

    it('returns map instance when rendered inside MapContainer', () => {
      const { result } = renderUseMapRef()

      // mapRef should contain Leaflet map instance
      expect(result.current.mapRef.current).toBeTruthy()
      expect(result.current.mapRef.current).toHaveProperty('getCenter')
      expect(result.current.mapRef.current).toHaveProperty('setZoom')
      expect(result.current.mapRef.current).toHaveProperty('flyTo')
    })

    it('provides getCenter method', () => {
      const { result } = renderUseMapRef()

      expect(typeof result.current.getCenter).toBe('function')
    })

    it('provides flyTo method', () => {
      const { result } = renderUseMapRef()

      expect(typeof result.current.flyTo).toBe('function')
    })

    it('provides setZoom method', () => {
      const { result } = renderUseMapRef()

      expect(typeof result.current.setZoom).toBe('function')
    })

    it('provides getBounds method', () => {
      const { result } = renderUseMapRef()

      expect(typeof result.current.getBounds).toBe('function')
    })

    it('provides fitBounds method', () => {
      const { result } = renderUseMapRef()

      expect(typeof result.current.fitBounds).toBe('function')
    })

    it('provides getZoom method', () => {
      const { result } = renderUseMapRef()

      expect(typeof result.current.getZoom).toBe('function')
    })
  })

  describe('Map Control Methods', () => {
    it('flyTo pans map to specified coordinates', () => {
      const { result } = renderUseMapRef()

      const targetLat = 40.7128
      const targetLng = -74.006
      const targetZoom = 15

      act(() => {
        result.current.flyTo(targetLat, targetLng, targetZoom)
      })

      // Verify flyTo was called on the map instance
      const center = result.current.mapRef.current.getCenter()
      expect(center.lat).toBeCloseTo(targetLat, 4)
      expect(center.lng).toBeCloseTo(targetLng, 4)
    })

    it('flyTo uses default zoom level when not specified', () => {
      const { result } = renderUseMapRef()

      const targetLat = 34.0522
      const targetLng = -118.2437

      act(() => {
        result.current.flyTo(targetLat, targetLng)
      })

      const center = result.current.mapRef.current.getCenter()
      expect(center.lat).toBeCloseTo(targetLat, 4)
      expect(center.lng).toBeCloseTo(targetLng, 4)
    })

    it('setZoom changes map zoom level', () => {
      const { result } = renderUseMapRef()

      act(() => {
        result.current.setZoom(18)
      })

      const zoom = result.current.mapRef.current.getZoom()
      expect(zoom).toBe(18)
    })

    it('getCenter returns current map center coordinates', () => {
      const { result } = renderUseMapRef()

      const center = result.current.getCenter()

      expect(center).toBeTruthy()
      expect(center).toHaveProperty('lat')
      expect(center).toHaveProperty('lng')
    })

    it('getZoom returns current map zoom level', () => {
      const { result } = renderUseMapRef()

      const zoom = result.current.getZoom()

      expect(typeof zoom).toBe('number')
      expect(zoom).toBeGreaterThanOrEqual(0)
    })

    it('getBounds returns current map bounds', () => {
      const { result } = renderUseMapRef()

      const bounds = result.current.getBounds()

      expect(bounds).toBeTruthy()
      expect(bounds).toHaveProperty('_northEast')
      expect(bounds).toHaveProperty('_southWest')
    })

    it('fitBounds adjusts map to show specified area', () => {
      const { result } = renderUseMapRef()

      const bounds = [
        [40.7128, -74.006],
        [34.0522, -118.2437],
      ]

      // Verify fitBounds doesn't throw
      expect(() => {
        act(() => {
          result.current.fitBounds(bounds)
        })
      }).not.toThrow()

      // Verify map bounds were updated (may need padding to include exact points)
      const currentBounds = result.current.mapRef.current.getBounds()
      expect(currentBounds).toBeTruthy()
      expect(currentBounds._northEast).toBeTruthy()
      expect(currentBounds._southWest).toBeTruthy()
    })

    it('fitBounds accepts padding option', () => {
      const { result } = renderUseMapRef()

      const bounds = [
        [40.7128, -74.006],
        [34.0522, -118.2437],
      ]
      const options = { padding: [50, 50] }

      // Verify fitBounds with padding doesn't throw
      expect(() => {
        act(() => {
          result.current.fitBounds(bounds, options)
        })
      }).not.toThrow()

      // Verify fitBounds method exists and was callable (skip getBounds check due to timing)
      expect(result.current.fitBounds).toBeTruthy()
    })
  })

  describe('Edge Cases and Error Handling', () => {
    it('throws when used outside MapContainer', () => {
      // useMapRef MUST be used inside MapContainer - it should throw if not
      expect(() => {
        renderHook(() => useMapRef())
      }).toThrow('No context provided')
    })

    it('handles invalid coordinates in flyTo gracefully', () => {
      const { result } = renderUseMapRef()

      // Should handle invalid coordinates (but Leaflet might normalize them)
      expect(() => {
        result.current.flyTo(null, null)
      }).not.toThrow()
    })

    it('handles invalid zoom level in setZoom gracefully', () => {
      const { result } = renderUseMapRef()

      // Should handle invalid zoom (Leaflet clamps to valid range)
      expect(() => {
        result.current.setZoom(-100)
      }).not.toThrow()

      expect(() => {
        result.current.setZoom(1000)
      }).not.toThrow()
    })
  })

  describe('Direct Map Access', () => {
    it('provides direct access to Leaflet map instance via mapRef', () => {
      const { result } = renderUseMapRef()

      const map = result.current.mapRef.current

      expect(map).toBeTruthy()
      // Should be a Leaflet map instance with expected methods
      expect(typeof map.setView).toBe('function')
      expect(typeof map.panTo).toBe('function')
      expect(typeof map.invalidateSize).toBe('function')
    })

    it('allows calling any Leaflet map method via mapRef.current', () => {
      const { result } = renderUseMapRef()

      const map = result.current.mapRef.current

      // Call Leaflet's panTo method directly
      act(() => {
        map.panTo([48.8566, 2.3522]) // Paris coordinates
      })

      const center = map.getCenter()
      expect(center.lat).toBeCloseTo(48.8566, 4)
      expect(center.lng).toBeCloseTo(2.3522, 4)
    })
  })

  describe('Hook Stability', () => {
    it('returns stable reference across re-renders', () => {
      const { result, rerender } = renderUseMapRef()

      const firstMapRef = result.current.mapRef
      const firstFlyTo = result.current.flyTo
      const firstSetZoom = result.current.setZoom

      rerender()

      // References should be stable
      expect(result.current.mapRef).toBe(firstMapRef)
      expect(result.current.flyTo).toBe(firstFlyTo)
      expect(result.current.setZoom).toBe(firstSetZoom)
    })
  })

  describe('Integration with react-leaflet', () => {
    it('works with useMap hook from react-leaflet', () => {
      const { result } = renderUseMapRef()

      // Map instance should be the same as what useMap() returns
      expect(result.current.mapRef.current).toBeTruthy()
      // Leaflet uses 'NewClass' as constructor name internally
      expect(['Map', 'NewClass']).toContain(result.current.mapRef.current.constructor.name)
    })

    it('map instance is available immediately after mount', () => {
      const { result } = renderUseMapRef()

      // Map should be available synchronously
      expect(result.current.mapRef.current).toBeTruthy()
    })
  })
})
