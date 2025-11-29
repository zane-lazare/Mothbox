import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeftIcon, ExclamationTriangleIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { useInfiniteQuery } from '@tanstack/react-query'
import { getPhotosPaginated } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'
import { MAP_CONFIG } from '../constants/config'
import MapView from '../components/MapView'
import PhotoLightbox from '../components/PhotoLightbox'
import ErrorBoundary from '../components/ErrorBoundary'
import LightboxErrorFallback from '../components/LightboxErrorFallback'
import { useClusteredLocations } from '../hooks/useClusteredLocations'

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
  const [selectedPhoto, setSelectedPhoto] = useState(null)

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

  // Fetch clustered photo locations (includes both clusters and unclustered)
  const {
    clusters,
    unclustered,
    metadata,
    isLoading: isLoadingClustered,
    isPartialResult,
    partialWarning,
    settings,
    setEnabled,
    setRadius,
    refetch,
  } = useClusteredLocations()

  // Calculate total counts for display
  const totalInClusters = clusters.reduce((sum, cluster) => sum + cluster.count, 0)
  const totalPhotos = totalInClusters + unclustered.length
  const totalWithGps = totalPhotos
  const totalWithoutGps = metadata.total_without_gps || 0

  // Handle map marker click - open lightbox with the clicked photo
  const handleMapPhotoClick = useCallback(
    (location) => {
      // Find the photo object in the photos array by matching the path
      // Note: location.photo_path from API, photos[].path from gallery API
      const photo = photos.find((p) => p.path === location.photo_path)
      if (photo) {
        setSelectedPhoto(photo)
      } else {
        // Fallback: Create a minimal photo object from location data
        // This ensures the lightbox can still open even if photo isn't in the loaded set
        setSelectedPhoto({
          path: location.photo_path,
          filename: location.filename,
          thumbnail_url: location.thumbnail_url,
          date: location.timestamp,
        })
      }
    },
    [photos]
  )

  // Lightbox navigation and close handlers
  const handleCloseLightbox = useCallback(() => setSelectedPhoto(null), [])
  const handleNavigate = useCallback(
    (photo) => {
      // Validate photo exists in current photos array before navigating
      if (photos.some((p) => p.path === photo.path)) {
        setSelectedPhoto(photo)
      }
    },
    [photos]
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
          {!isLoadingClustered && totalWithGps > 0 && (
            <p className="text-sm text-gray-300 mt-1">
              {totalWithGps} photo{totalWithGps !== 1 ? 's' : ''} with GPS coordinates
              {totalWithoutGps > 0 &&
                ` (${totalWithoutGps} photo${totalWithoutGps !== 1 ? 's' : ''} without GPS)`}
            </p>
          )}
        </div>
      </header>

      {/* Partial results warning banner */}
      {isPartialResult && (
        <div
          role="alert"
          className="bg-yellow-100 border-b border-yellow-300 px-4 py-2 flex items-center justify-between"
        >
          <div className="flex items-center gap-2 text-yellow-800">
            <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
            <span className="text-sm">
              {partialWarning || 'Some locations may be missing due to timeout'}
            </span>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1 text-sm text-yellow-800 hover:text-yellow-900 hover:bg-yellow-200 px-2 py-1 rounded transition-colors"
            aria-label="Retry loading all locations"
          >
            <ArrowPathIcon className="h-4 w-4" />
            Retry
          </button>
        </div>
      )}

      {/* Map fills remaining screen space */}
      <div className="flex-1 relative">
        <MapView
          locations={unclustered}
          clusters={clusters}
          clusterSettings={settings}
          onClusterEnabledChange={setEnabled}
          onClusterRadiusChange={setRadius}
          onPhotoClick={handleMapPhotoClick}
          isLoading={isLoadingClustered}
          className="h-full"
        />
      </div>

      {/* Photo Lightbox with Navigation (wrapped in ErrorBoundary) */}
      <ErrorBoundary
        fallback={({ error, onClose }) => (
          <LightboxErrorFallback error={error} onClose={onClose} />
        )}
        onReset={handleCloseLightbox}
      >
        <PhotoLightbox
          photo={selectedPhoto}
          photos={photos}
          onClose={handleCloseLightbox}
          onNavigate={handleNavigate}
        />
      </ErrorBoundary>
    </div>
  )
}
