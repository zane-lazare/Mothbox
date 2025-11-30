import { useRef, useCallback } from 'react'
import { useMap } from 'react-leaflet'

/**
 * Custom hook for controlled access to Leaflet map instance via React ref
 *
 * Provides a ref-based wrapper around react-leaflet's useMap() hook, along with
 * convenience methods for common map operations (flyTo, setZoom, etc). Designed
 * for programmatic map control from parent components without prop drilling.
 *
 * IMPORTANT: This hook must be used inside a <MapContainer> component from react-leaflet,
 * as it relies on the useMap() hook which requires the map context.
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
  // Note: This will be null if used outside MapContainer
  let map = null
  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    map = useMap()
  } catch {
    // useMap throws if not inside MapContainer - catch and leave map as null
    // This allows hook to be used outside map context without crashing
  }

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
      } catch (error) {
        // Silently handle errors (invalid coordinates, etc)
        console.warn('flyTo error:', error)
      }
    },
    [mapRef]
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
      } catch (error) {
        console.warn('setZoom error:', error)
      }
    },
    [mapRef]
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
    } catch (error) {
      console.warn('getCenter error:', error)
      return null
    }
  }, [mapRef])

  /**
   * Get current map zoom level
   *
   * @returns {number|null} Zoom level or null if map not initialized
   */
  const getZoom = useCallback(() => {
    if (!mapRef.current) return null

    try {
      return mapRef.current.getZoom()
    } catch (error) {
      console.warn('getZoom error:', error)
      return null
    }
  }, [mapRef])

  /**
   * Get current map bounds
   *
   * @returns {Object|null} Leaflet LatLngBounds object or null if map not initialized
   */
  const getBounds = useCallback(() => {
    if (!mapRef.current) return null

    try {
      return mapRef.current.getBounds()
    } catch (error) {
      console.warn('getBounds error:', error)
      return null
    }
  }, [mapRef])

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
      } catch (error) {
        console.warn('fitBounds error:', error)
      }
    },
    [mapRef]
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
