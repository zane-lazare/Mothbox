import { useState, useCallback, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import { useInfiniteQuery } from '@tanstack/react-query'
import { getPhotosPaginated } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'
import { MAP_CONFIG } from '../constants/config'
import MapView from '../components/MapView'
import PhotoLightbox from '../components/PhotoLightbox'
import ErrorBoundary from '../components/ErrorBoundary'
import LightboxErrorFallback from '../components/LightboxErrorFallback'
import { usePhotoLocations } from '../hooks/usePhotoLocations'
import useMapLightboxSync from '../hooks/useMapLightboxSync'

/**
 * MapPage - Full-screen immersive map experience for GPS-tagged photos
 *
 * Displays all photos with GPS coordinates on an interactive map.
 * Clicking a marker opens the photo in a lightbox with full navigation.
 *
 * Features:
 * - Full-screen map layout (h-screen)
 * - Integration with photo locations API
 * - Lightbox for viewing photos
 * - Navigation back to gallery
 * - Error boundaries for graceful degradation
 *
 * @component
 * @example
 * // Route in App.jsx:
 * <Route path="/gallery/map" element={<MapPage />} />
 */
export default function MapPage() {
  const navigate = useNavigate()
  const mapRef = useRef(null)

  // Fetch all photos for lightbox navigation
  // Using infinite query to match Gallery.jsx pattern
  const {
    data: photosData,
  } = useInfiniteQuery({
    queryKey: QUERY_KEYS.PHOTOS_INFINITE,
    queryFn: ({ pageParam = 0 }) =>
      getPhotosPaginated({
        limit: MAP_CONFIG.PHOTO_BATCH_SIZE,
        offset: pageParam,
        sort: 'date_desc',
      }).then((res) => res.data),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      if (lastPage.pagination.has_next) {
        return lastPage.pagination.offset + lastPage.pagination.limit
      }
      return undefined
    },
  })

  // Flatten all pages into single photo array
  const photos = photosData?.pages.flatMap((page) => page.photos) ?? []

  // Fetch photo locations for map display
  const { locations, isLoading, totalWithGps, totalWithoutGps } = usePhotoLocations()

  // Map-Lightbox synchronization hook
  const {
    isLightboxOpen,
    currentPhoto,
    highlightedPhotoPath,
    hasNext,
    hasPrevious,
    goNext,
    goPrevious,
    openLightbox,
    closeLightbox,
    onMarkerClick,
    onClusterClick,
  } = useMapLightboxSync({ mapRef })

  // Handle map marker click - open lightbox with the clicked photo
  const handleMapPhotoClick = useCallback(
    (location) => {
      // Find the photo object in the photos array by matching the path
      // Note: location.photo_path from API, photos[].path from gallery API
      const photo = photos.find((p) => p.path === location.photo_path)
      if (photo) {
        // Create a "virtual cluster" containing all photos for navigation
        // This allows users to navigate through all photos even when clicking a single marker
        const virtualCluster = {
          getAllChildMarkers: () => {
            // Return array of mock markers with photo data in options
            return photos.map(p => ({
              options: { ...p }
            }))
          }
        }
        // Use onClusterClick to set up full photo navigation
        onClusterClick(virtualCluster, photo)
      } else {
        // Fallback: Create a minimal photo object from location data
        const minimalPhoto = {
          path: location.photo_path,
          filename: location.filename,
          thumbnail_url: location.thumbnail_url,
          date: location.timestamp,
        }
        onMarkerClick(null, minimalPhoto)
      }
    },
    [photos, onMarkerClick, onClusterClick]
  )

  // Handle lightbox navigation - simple forward to openLightbox
  const handleNavigate = useCallback(
    (photo) => {
      // Validate photo exists in current photos array before navigating
      if (photos.some((p) => p.path === photo.path)) {
        // Open lightbox with new photo (maintains cluster context if present)
        openLightbox(photo)
      }
    },
    [photos, openLightbox]
  )

  // Handle location click in lightbox (pan map to coordinates)
  const handleLocationClick = useCallback(
    (lat, lon) => {
      if (mapRef.current && lat !== null && lon !== null) {
        try {
          const currentZoom = mapRef.current.getZoom?.() || 13
          mapRef.current.flyTo?.([lat, lon], currentZoom)
        } catch (error) {
          console.warn('Error panning map to location:', error)
        }
      }
    },
    [mapRef]
  )

  return (
    <div className="h-screen flex flex-col">
      {/* Header with back navigation */}
      <header className="bg-gray-800 text-white p-4 flex items-center gap-4 shadow-lg z-10">
        <Link
          to="/gallery"
          className="hover:bg-gray-700 p-2 rounded transition-colors"
          aria-label="Back to gallery"
        >
          <ArrowLeftIcon className="h-6 w-6" />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-semibold">Photo Locations</h1>
          {!isLoading && totalWithGps > 0 && (
            <p className="text-sm text-gray-300 mt-1">
              {totalWithGps} photo{totalWithGps !== 1 ? 's' : ''} with GPS coordinates
              {totalWithoutGps > 0 &&
                ` (${totalWithoutGps} photo${totalWithoutGps !== 1 ? 's' : ''} without GPS)`}
            </p>
          )}
        </div>
      </header>

      {/* Map fills remaining screen space */}
      <div className="flex-1 relative">
        <MapView
          ref={mapRef}
          locations={locations}
          onPhotoClick={handleMapPhotoClick}
          isLoading={isLoading}
          className="h-full"
          highlightedPhotoPath={highlightedPhotoPath}
        />
      </div>

      {/* Photo Lightbox with Navigation (wrapped in ErrorBoundary) */}
      <ErrorBoundary
        fallback={({ error, onClose }) => (
          <LightboxErrorFallback error={error} onClose={onClose} />
        )}
        onReset={closeLightbox}
      >
        <PhotoLightbox
          photo={currentPhoto}
          photos={photos}
          onClose={closeLightbox}
          onNavigate={handleNavigate}
          onLocationClick={handleLocationClick}
        />
      </ErrorBoundary>
    </div>
  )
}
