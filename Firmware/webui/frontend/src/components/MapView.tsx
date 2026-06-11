import React, { useEffect, useMemo, forwardRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import L, { Map as LeafletMap, DivIcon, Icon } from 'leaflet'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIconRetina from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { MAP_CONFIG, CLUSTERING_CONFIG, Z_INDEX } from '../constants/config'
import MarkerHoverPopup from './MarkerHoverPopup'
import ErrorBoundary from './ErrorBoundary'
import { useHoverPopup } from '../hooks/useHoverPopup'
import { getThumbnailUrl as getThumbnailUrlSingle } from '../utils/thumbnailUrl'

export interface PhotoLocation {
  path: string
  filename: string
  latitude: number
  longitude: number
  thumbnail_url?: string
  timestamp?: number
  photo_path?: string
}

export interface GeoCluster {
  cluster_id: string
  center: {
    lat: number
    lon: number
  }
  count: number
  photos: Array<{
    path: string
    filename?: string
    latitude?: number
    longitude?: number
    thumbnail_url?: string
    timestamp?: number
  }>
  date_range: {
    earliest: string
    latest: string
  }
}

export interface ClusterSettings {
  enabled: boolean
  radius: number
  minSize?: number
}

export interface ClusteringControlsProps {
  settings: ClusterSettings
  onEnabledChange: (enabled: boolean) => void
  onRadiusChange: (radius: number) => void
}

export interface ClusterMarkerProps {
  cluster: GeoCluster
  onPhotoClick?: (photo: PhotoLocation) => void
  onMouseEnter?: (cluster: GeoCluster, event: MouseEvent) => void
  onMouseLeave?: () => void
  onPopupOpen?: (cluster: GeoCluster) => void
  onPopupClose?: () => void
}

export interface BoundsUpdaterProps {
  locations: PhotoLocation[]
  clusters: GeoCluster[]
}

export interface MapRefSetterProps {
  mapRef: React.RefObject<LeafletMap | null>
}

export interface MapViewProps {
  /** Array of individual photo location objects */
  locations?: PhotoLocation[]
  /** Array of geographic clusters from backend */
  clusters?: GeoCluster[]
  /** Clustering settings {enabled, radius, minSize} */
  clusterSettings?: ClusterSettings | null
  /** Callback when clustering is toggled */
  onClusterEnabledChange?: ((enabled: boolean) => void) | null
  /** Callback when cluster radius is changed */
  onClusterRadiusChange?: ((radius: number) => void) | null
  /** Callback when photo marker is clicked (receives location object) */
  onPhotoClick?: (location: PhotoLocation) => void
  /** Show loading skeleton instead of map */
  isLoading?: boolean
  /** Additional CSS classes for the map wrapper */
  className?: string
  /** Photo path to highlight on map (for lightbox sync) */
  highlightedPhotoPath?: string | null
}

/**
 * ClusteringControls - UI controls for geographic clustering settings
 *
 * Provides toggle for enabling/disabling clustering and slider for radius adjustment.
 * Settings are persisted in localStorage via the parent component's hook.
 */
function ClusteringControls({ settings, onEnabledChange, onRadiusChange }: ClusteringControlsProps) {
  return (
    <div className={`absolute top-4 right-4 ${Z_INDEX.MAP_CONTROLS} bg-white rounded-lg shadow-lg p-3 min-w-[200px]`}>
      <h3 className="font-medium text-sm mb-2">Geographic Clustering</h3>

      <label className="flex items-center gap-2 mb-2 cursor-pointer">
        <input
          type="checkbox"
          checked={settings.enabled}
          onChange={(e) => onEnabledChange(e.target.checked)}
          className="w-4 h-4 cursor-pointer"
        />
        <span className="text-sm">Enable backend clustering</span>
      </label>

      {settings.enabled && (
        <div className="mt-3">
          <label className="text-xs text-gray-600 block mb-1">
            Radius: {settings.radius}m
          </label>
          <input
            type="range"
            min={CLUSTERING_CONFIG.MIN_RADIUS}
            max={CLUSTERING_CONFIG.MAX_RADIUS}
            step={CLUSTERING_CONFIG.RADIUS_STEP}
            value={settings.radius}
            onChange={(e) => onRadiusChange(Number(e.target.value))}
            className="w-full cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>{CLUSTERING_CONFIG.MIN_RADIUS}m</span>
            <span>{CLUSTERING_CONFIG.MAX_RADIUS}m</span>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * ClusterMarker - Custom marker for geographic clusters
 *
 * Displays a circular badge with the number of photos in the cluster.
 * Clicking opens a popup with thumbnails and metadata.
 */
function ClusterMarker({ cluster, onPhotoClick, onMouseEnter, onMouseLeave, onPopupOpen, onPopupClose }: ClusterMarkerProps) {
  // Create custom cluster icon
  const icon: DivIcon = L.divIcon({
    className: 'cluster-marker',
    html: `<div class="cluster-badge">${cluster.count}</div>`,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    popupAnchor: [0, -20],
  })

  return (
    <Marker
      position={[cluster.center.lat, cluster.center.lon]}
      icon={icon}
      eventHandlers={{
        mouseover: (e) => onMouseEnter?.(cluster, e.originalEvent),
        mouseout: () => onMouseLeave?.(),
        popupopen: () => onPopupOpen?.(cluster),
        popupclose: () => onPopupClose?.(),
      }}
    >
      <Popup maxWidth={250}>
        <div className="cluster-popup">
          <h4 className="font-semibold text-sm mb-1">{cluster.count} photos</h4>
          <p className="text-xs text-gray-600 mb-2">
            {cluster.date_range.earliest} - {cluster.date_range.latest}
          </p>
          <div className="grid grid-cols-3 gap-1">
            {cluster.photos.slice(0, 6).map((photo) => (
              <img
                key={photo.path}
                src={photo.thumbnail_url || getThumbnailUrlSingle(photo.path)}
                alt={photo.filename || photo.path}
                className="w-full h-16 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                onClick={() => {
                  if (onPhotoClick && photo.filename && photo.latitude && photo.longitude) {
                    onPhotoClick({
                      path: photo.path,
                      filename: photo.filename,
                      latitude: photo.latitude,
                      longitude: photo.longitude,
                      thumbnail_url: photo.thumbnail_url,
                      timestamp: photo.timestamp,
                    })
                  }
                }}
              />
            ))}
          </div>
          {cluster.count > 6 && (
            <p className="text-xs text-gray-500 mt-1 text-center">
              +{cluster.count - 6} more photos
            </p>
          )}
        </div>
      </Popup>
    </Marker>
  )
}

/**
 * BoundsUpdater - Internal component to auto-fit map bounds to all markers
 *
 * This component uses the useMap hook to access the Leaflet map instance
 * and update the bounds whenever locations change.
 */
function BoundsUpdater({ locations, clusters }: BoundsUpdaterProps) {
  const map = useMap()

  useEffect(() => {
    // Collect all positions from both individual locations and clusters
    const allPositions: [number, number][] = []

    if (locations && locations.length > 0) {
      allPositions.push(...locations.map((loc) => [loc.latitude, loc.longitude] as [number, number]))
    }

    if (clusters && clusters.length > 0) {
      allPositions.push(...clusters.map((cluster) => [cluster.center.lat, cluster.center.lon] as [number, number]))
    }

    if (allPositions.length === 0) return

    // Fit map to show all markers
    if (allPositions.length === 1) {
      // Single location: center on it with reasonable zoom
      map.setView(allPositions[0], 12)
    } else {
      // Multiple locations: fit all markers in view
      map.fitBounds(allPositions, { padding: [50, 50] })
    }
  }, [locations, clusters, map])

  return null
}

/**
 * MapRefSetter - Internal component to expose map instance via ref
 *
 * This component uses the useMap hook to access the Leaflet map instance
 * and sets it on the parent ref.
 */
function MapRefSetter({ mapRef }: MapRefSetterProps) {
  const map = useMap()

  useEffect(() => {
    if (mapRef) {
      mapRef.current = map
    }
  }, [map, mapRef])

  return null
}

/**
 * MapView - Leaflet map component for displaying GPS-tagged photo locations
 *
 * Features:
 * - OpenStreetMap tiles (no API key required)
 * - Hybrid clustering: Backend geographic clusters + frontend pixel clustering
 * - Auto-fit bounds to show all photo locations
 * - Photo thumbnail popups on marker click
 * - Loading skeleton and empty state
 * - Fully responsive
 * - Clustering controls for adjusting backend clustering settings
 * - Marker highlighting support for map-lightbox integration
 */
const MapView = forwardRef<LeafletMap | null, MapViewProps>(function MapView({
  locations = [],
  clusters = [],
  clusterSettings = null,
  onClusterEnabledChange = null,
  onClusterRadiusChange = null,
  onPhotoClick,
  isLoading = false,
  className = '',
  highlightedPhotoPath = null
}, ref) {
  // Hover popup state management
  const {
    isVisible,
    targetCluster,
    position,
    handleMouseEnter,
    handleMouseLeave,
    handlePopupOpen,
    handlePopupClose,
  } = useHoverPopup()

  // Create custom marker icons with locally bundled assets (no CDN dependency)
  // Memoize to avoid recreation on every render
  // IMPORTANT: These hooks MUST be called before any conditional returns to follow Rules of Hooks
  const normalIcon = useMemo(() => new L.Icon({
    iconUrl: markerIcon,
    iconRetinaUrl: markerIconRetina,
    shadowUrl: markerShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  }), [])

  // Create highlighted marker icon using divIcon for CSS-based styling (no extra assets)
  // Orange color (#f97316) for highlighted, matches Tailwind orange-500
  const highlightedIcon = useMemo(() => L.divIcon({
    className: 'highlighted-marker',
    html: `<div style="
      background-color: #f97316;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 2px 6px rgba(0,0,0,0.4);
      transform: scale(1.2);
    "></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24],
  }), [])

  // Normalize locations and clusters (handle null/undefined)
  const normalizedLocations = locations || []
  const normalizedClusters = clusters || []

  /**
   * Get the appropriate icon for a location marker
   * Returns highlighted icon if this location matches the highlighted photo path
   */
  const getMarkerIcon = (location: PhotoLocation): Icon | DivIcon => {
    // Check both path and photo_path fields for compatibility
    const locationPath = location.path || location.photo_path
    if (highlightedPhotoPath && locationPath === highlightedPhotoPath) {
      return highlightedIcon
    }
    return normalIcon
  }

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

  // Empty state - show only if both locations and clusters are empty
  if (normalizedLocations.length === 0 && normalizedClusters.length === 0) {
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

  return (
    <div className={`w-full h-full relative ${className}`}>
      <MapContainer
        center={MAP_CONFIG.DEFAULT_CENTER as [number, number]}
        zoom={MAP_CONFIG.DEFAULT_ZOOM}
        minZoom={MAP_CONFIG.MIN_ZOOM}
        maxZoom={MAP_CONFIG.MAX_ZOOM}
        style={{ width: '100%', height: '100%' }}
        className="rounded-lg"
        scrollWheelZoom={true}
        attributionControl={true}
      >
        <TileLayer
          data-testid="tile-layer"
          url={MAP_CONFIG.TILE_URL}
          attribution={MAP_CONFIG.ATTRIBUTION}
          maxZoom={MAP_CONFIG.MAX_ZOOM}
        />

        {/* Expose map instance via ref */}
        <MapRefSetter mapRef={ref as React.RefObject<LeafletMap | null>} />

        {/* Backend geographic cluster markers (outside MarkerClusterGroup) */}
        {normalizedClusters.map((cluster) => (
          <ClusterMarker
            key={cluster.cluster_id}
            cluster={cluster}
            onPhotoClick={onPhotoClick}
            onMouseEnter={(c, e) => handleMouseEnter(c as any, e)}
            onMouseLeave={handleMouseLeave}
            onPopupOpen={(c) => handlePopupOpen(c as any)}
            onPopupClose={handlePopupClose}
          />
        ))}

        {/* Individual photo markers with frontend pixel clustering */}
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
              icon={getMarkerIcon(location)}
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

        <BoundsUpdater locations={normalizedLocations} clusters={normalizedClusters} />
      </MapContainer>

      {/* Hover popup overlay - wrapped in ErrorBoundary for graceful degradation */}
      <ErrorBoundary
        fallback={({ onClose }) => (
          <div
            className="fixed bg-white rounded-lg shadow-xl border border-gray-200 p-4"
            style={{
              left: position?.x || 0,
              top: position?.y || 0,
              zIndex: 1100,
            }}
          >
            <p className="text-red-600 text-sm mb-2">Failed to load preview</p>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-sm underline"
            >
              Close
            </button>
          </div>
        )}
        onReset={handleMouseLeave}
      >
        <MarkerHoverPopup
          cluster={targetCluster as any}
          isVisible={isVisible}
          position={position || undefined}
          onPhotoClick={onPhotoClick as any}
          onClose={handleMouseLeave}
        />
      </ErrorBoundary>

      {/* Clustering controls - only show if settings provided */}
      {clusterSettings && onClusterEnabledChange && onClusterRadiusChange && (
        <ClusteringControls
          settings={clusterSettings}
          onEnabledChange={onClusterEnabledChange}
          onRadiusChange={onClusterRadiusChange}
        />
      )}
    </div>
  )
})

export default React.memo(MapView)
