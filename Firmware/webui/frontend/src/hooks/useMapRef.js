import { useRef, useCallback } from 'react'
import { useMap } from 'react-leaflet'

/**
 * Custom hook for controlled access to Leaflet map instance via React ref
 *
 * Provides a ref-based wrapper around react-leaflet's useMap() hook, along with
 * convenience methods for common map operations (flyTo, setZoom, etc). Designed
 * for programmatic map control from parent components without prop drilling.
 *
 * IMPORTANT: This hook MUST be used inside a <MapContainer> component from react-leaflet.
 * Using it outside of MapContainer will throw an error. If you need graceful handling
 * outside MapContainer, use the MapRefSetter component pattern instead (see MapView.jsx).
 *
 * @throws {Error} If used outside of a MapContainer component
 *
 * @returns {Object} Hook state
 * @returns {React.RefObject} mapRef - React ref containing the Leaflet map instance
 * @returns {Function} flyTo - Pan map to coordinates with optional zoom
 * @returns {Function} setZoom - Set map zoom level
 * @returns {Function} getCenter - Get current map center coordinates
 * @returns {Function} getZoom - Get current map zoom level
 * @returns {Function} getBounds - Get current map bounds
 * @returns {Function} fitBounds - Fit map to show specified bounds
 *
 * @example
 * // In a component inside MapContainer:
 * const { mapRef, flyTo, setZoom } = useMapRef()
 *
 * // Programmatic pan to location
 * flyTo(40.7128, -74.006, 15)
 *
 * // Change zoom level
 * setZoom(18)
 *
 * // Direct access to map instance
 * mapRef.current?.invalidateSize()
 *
 * @example
 * // Integration with map-lightbox workflow:
 * function MapWithLightbox() {
 *   const { mapRef, flyTo } = useMapRef()
 *
 *   const handlePhotoSelect = (photo) => {
 *     if (photo.latitude && photo.longitude) {
 *       // Pan map to photo location when selected in lightbox
 *       flyTo(photo.latitude, photo.longitude, 15)
 *     }
 *   }
 *
 *   return <PhotoLightbox onPhotoChange={handlePhotoSelect} />
 * }
 */
export function useMapRef() {
  // Get Leaflet map instance from react-leaflet context
  // This hook MUST be used inside a <MapContainer> - will throw if not
  const map = useMap()

  // Store map instance in ref for external access
  const mapRef = useRef(map)

  // Update ref when map instance changes
  if (map !== mapRef.current) {
    mapRef.current = map
  }

  /**
   * Pan map to specified coordinates with optional zoom level
   *
   * Uses Leaflet's flyTo() for smooth animated panning. If map is not
   * initialized, this method safely does nothing.
   *
   * @param {number} lat - Latitude in decimal degrees
   * @param {number} lng - Longitude in decimal degrees
   * @param {number} [zoom] - Optional zoom level (uses current zoom if not specified)
   */
  const flyTo = useCallback(
    (lat, lng, zoom) => {
      if (!mapRef.current) return

      try {
        if (zoom !== undefined) {
          mapRef.current.flyTo([lat, lng], zoom)
        } else {
          // Use current zoom level if not specified
          const currentZoom = mapRef.current.getZoom()
          mapRef.current.flyTo([lat, lng], currentZoom)
        }
      } catch {
        // Silently handle errors (invalid coordinates, etc)
        // This is expected for photos without valid GPS
      }
    },
    [] // mapRef is a stable ref, no need to include in deps
  )

  /**
   * Set map zoom level
   *
   * @param {number} level - Zoom level (Leaflet clamps to valid range automatically)
   */
  const setZoom = useCallback(
    (level) => {
      if (!mapRef.current) return

      try {
        mapRef.current.setZoom(level)
      } catch {
        // Silently handle errors (invalid zoom level, etc)
      }
    },
    [] // mapRef is a stable ref, no need to include in deps
  )

  /**
   * Get current map center coordinates
   *
   * @returns {Object|null} Center object with {lat, lng} or null if map not initialized
   */
  const getCenter = useCallback(() => {
    if (!mapRef.current) return null

    try {
      return mapRef.current.getCenter()
    } catch {
      return null
    }
  }, []) // mapRef is a stable ref, no need to include in deps

  /**
   * Get current map zoom level
   *
   * @returns {number|null} Zoom level or null if map not initialized
   */
  const getZoom = useCallback(() => {
    if (!mapRef.current) return null

    try {
      return mapRef.current.getZoom()
    } catch {
      return null
    }
  }, []) // mapRef is a stable ref, no need to include in deps

  /**
   * Get current map bounds
   *
   * @returns {Object|null} Leaflet LatLngBounds object or null if map not initialized
   */
  const getBounds = useCallback(() => {
    if (!mapRef.current) return null

    try {
      return mapRef.current.getBounds()
    } catch {
      return null
    }
  }, []) // mapRef is a stable ref, no need to include in deps

  /**
   * Fit map to show specified geographic bounds
   *
   * @param {Array} bounds - Array of [lat, lng] coordinate pairs: [[lat1, lng1], [lat2, lng2]]
   * @param {Object} [options] - Leaflet fitBounds options (e.g., {padding: [50, 50]})
   */
  const fitBounds = useCallback(
    (bounds, options) => {
      if (!mapRef.current) return

      try {
        mapRef.current.fitBounds(bounds, options)
      } catch {
        // Silently handle errors (invalid bounds, etc)
      }
    },
    [] // mapRef is a stable ref, no need to include in deps
  )

  return {
    mapRef,
    flyTo,
    setZoom,
    getCenter,
    getZoom,
    getBounds,
    fitBounds,
  }
}
