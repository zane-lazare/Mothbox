import React, { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import L from 'leaflet'
import { MAP_CONFIG } from '../constants/config'

/**
 * BoundsUpdater - Internal component to auto-fit map bounds to all markers
 *
 * This component uses the useMap hook to access the Leaflet map instance
 * and update the bounds whenever locations change.
 */
function BoundsUpdater({ locations }) {
  const map = useMap()

  useEffect(() => {
    if (!locations || locations.length === 0) return

    // Build bounds array from all locations
    const bounds = locations.map((loc) => [loc.latitude, loc.longitude])

    // Fit map to show all markers
    if (bounds.length === 1) {
      // Single location: center on it with reasonable zoom
      map.setView(bounds[0], 12)
    } else {
      // Multiple locations: fit all markers in view
      map.fitBounds(bounds, { padding: [50, 50] })
    }
  }, [locations, map])

  return null
}

/**
 * MapView - Leaflet map component for displaying GPS-tagged photo locations
 *
 * Features:
 * - OpenStreetMap tiles (no API key required)
 * - Marker clustering for performance with many photos
 * - Auto-fit bounds to show all photo locations
 * - Photo thumbnail popups on marker click
 * - Loading skeleton and empty state
 * - Fully responsive
 *
 * @param {Object} props
 * @param {Array} props.locations - Array of photo location objects with {latitude, longitude, thumbnail_url, filename}
 * @param {Function} props.onPhotoClick - Callback when photo marker is clicked (receives location object)
 * @param {boolean} props.isLoading - Show loading skeleton instead of map
 * @param {string} props.className - Additional CSS classes for the map wrapper
 */
function MapView({ locations = [], onPhotoClick, isLoading = false, className = '' }) {
  // Normalize locations (handle null/undefined)
  const normalizedLocations = locations || []

  // Loading skeleton
  if (isLoading) {
    return (
      <div
        data-testid="map-loading-skeleton"
        aria-busy="true"
        className={`w-full h-full bg-gray-200 animate-pulse rounded-lg flex items-center justify-center ${className}`}
      >
        <div className="text-gray-500">Loading map...</div>
      </div>
    )
  }

  // Empty state
  if (normalizedLocations.length === 0) {
    return (
      <div
        role="status"
        className={`w-full h-full bg-gray-100 rounded-lg flex flex-col items-center justify-center p-8 text-center ${className}`}
      >
        <svg
          className="w-16 h-16 text-gray-400 mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
          />
        </svg>
        <h3 className="text-lg font-semibold text-gray-700 mb-2">No GPS-tagged photos</h3>
        <p className="text-sm text-gray-600">
          Photos with GPS coordinates will appear here on the map
        </p>
      </div>
    )
  }

  // Create custom marker icon (Leaflet default icon fix for bundlers)
  const customIcon = new L.Icon({
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  })

  return (
    <div className={`w-full h-full ${className}`}>
      <MapContainer
        data-testid="map-container"
        role="application"
        aria-label="Interactive map showing photo locations"
        center={MAP_CONFIG.DEFAULT_CENTER}
        zoom={MAP_CONFIG.DEFAULT_ZOOM}
        minZoom={MAP_CONFIG.MIN_ZOOM}
        maxZoom={MAP_CONFIG.MAX_ZOOM}
        style={{ width: '100%', height: '100%' }}
        className="rounded-lg"
        // Touch optimization settings for mobile devices
        tap={true} // Enable tap handler for touch devices
        tapTolerance={15} // Tolerance for tap detection (pixels)
        touchZoom={true} // Enable pinch-to-zoom on touch devices
        dragging={true} // Enable touch dragging/panning
        scrollWheelZoom={true} // Enable scroll wheel zoom (desktop) and pinch zoom (mobile)
        doubleClickZoom={true} // Enable double-click/tap zoom
        attributionControl={true} // Keep attribution visible
      >
        <TileLayer
          data-testid="tile-layer"
          url={MAP_CONFIG.TILE_URL}
          attribution={MAP_CONFIG.ATTRIBUTION}
          maxZoom={MAP_CONFIG.MAX_ZOOM}
        />

        <MarkerClusterGroup
          data-testid="marker-cluster-group"
          chunkedLoading
          maxClusterRadius={MAP_CONFIG.CLUSTER.MAX_RADIUS}
          spiderfyOnMaxZoom={MAP_CONFIG.CLUSTER.SPIDERFY_ON_MAX_ZOOM}
          showCoverageOnHover={MAP_CONFIG.CLUSTER.SHOW_COVERAGE_ON_HOVER}
        >
          {normalizedLocations.map((location, index) => (
            <Marker
              key={`${location.filename}-${index}`}
              position={[location.latitude, location.longitude]}
              icon={customIcon}
              eventHandlers={{
                click: () => {
                  if (onPhotoClick) {
                    onPhotoClick(location)
                  }
                },
              }}
            >
              <Popup maxWidth={MAP_CONFIG.POPUP.MAX_WIDTH}>
                <div className="text-center">
                  <img
                    src={location.thumbnail_url}
                    alt={location.filename}
                    className="w-full h-auto mb-2 rounded"
                    style={{ maxHeight: MAP_CONFIG.POPUP.THUMBNAIL_SIZE }}
                  />
                  <p className="text-sm font-semibold text-gray-800 truncate">
                    {location.filename}
                  </p>
                  <p className="text-xs text-gray-600 mt-1">
                    {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}
        </MarkerClusterGroup>

        <BoundsUpdater locations={normalizedLocations} />
      </MapContainer>
    </div>
  )
}

export default React.memo(MapView)
