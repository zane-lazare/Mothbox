import { useState, useCallback, useEffect } from 'react'
import useClusterNavigation from './useClusterNavigation'
import { extractPhotosFromCluster, findPhotoIndexInCluster } from '../utils/clusterUtils'

/**
 * Custom hook for orchestrating two-way synchronization between map and lightbox components.
 *
 * Manages the integration between the interactive map view and the photo lightbox,
 * providing seamless synchronization when users navigate photos via either interface.
 * Handles marker highlighting, cluster expansion (spiderfy), and graceful GPS handling.
 *
 * @hook
 *
 * @param {Object} props - Hook configuration
 * @param {React.RefObject} props.mapRef - React ref containing Leaflet map instance
 *
 * @returns {Object} Synchronization state and controls
 * @returns {boolean} returns.isLightboxOpen - Whether lightbox is currently open
 * @returns {Object|null} returns.currentPhoto - Current photo being displayed
 * @returns {string|null} returns.highlightedPhotoPath - Path of highlighted marker
 * @returns {Array} returns.clusterPhotos - Photos in current cluster (from navigation)
 * @returns {number} returns.currentIndex - Current index in cluster (-1 if no cluster)
 * @returns {boolean} returns.hasNext - True if can navigate to next photo
 * @returns {boolean} returns.hasPrevious - True if can navigate to previous photo
 * @returns {Function} returns.goNext - Navigate to next photo in cluster
 * @returns {Function} returns.goPrevious - Navigate to previous photo in cluster
 * @returns {Function} returns.openLightbox - Open lightbox with photo (and optional cluster)
 * @returns {Function} returns.closeLightbox - Close lightbox and reset state
 * @returns {Function} returns.selectPhoto - Change current photo (syncs map)
 * @returns {Function} returns.onMarkerClick - Handler for individual marker clicks
 * @returns {Function} returns.onClusterClick - Handler for cluster marker clicks
 *
 * @example
 * // In MapView component
 * const { mapRef } = useMapRef()
 * const {
 *   isLightboxOpen,
 *   currentPhoto,
 *   highlightedPhotoPath,
 *   openLightbox,
 *   closeLightbox,
 *   onMarkerClick,
 *   onClusterClick,
 * } = useMapLightboxSync({ mapRef })
 *
 * // Render markers with highlight
 * <Marker
 *   onClick={() => onMarkerClick(marker, photo)}
 *   icon={photo.path === highlightedPhotoPath ? highlightIcon : normalIcon}
 * />
 *
 * // Render cluster markers
 * <MarkerClusterGroup
 *   onClick={(cluster) => onClusterClick(cluster, clickedPhoto)}
 * />
 *
 * // Render lightbox
 * {isLightboxOpen && (
 *   <PhotoLightbox
 *     photo={currentPhoto}
 *     onClose={closeLightbox}
 *   />
 * )}
 *
 * @strategy Synchronization Behavior
 * - **Lightbox → Map**: When photo changes in lightbox, map pans to location and highlights marker
 * - **Map → Lightbox**: When marker clicked, lightbox opens and displays photo
 * - **Cluster handling**: Auto-spiderfies clusters when lightbox opens on clustered photo
 * - **Missing GPS**: Gracefully handles photos without coordinates (no map pan, but lightbox still opens)
 *
 * @strategy Marker Highlighting
 * - Uses `highlightedPhotoPath` to track which marker should be highlighted
 * - MapView component checks if marker's photo path matches highlighted path
 * - Applies different icon/color for highlighted state (implementation in MapView)
 * - Clears highlight when lightbox closes
 *
 * @strategy Cluster Navigation
 * - Delegates to useClusterNavigation hook for photo navigation state
 * - Extracts photos from cluster marker using clusterUtils
 * - Automatically sets up cluster context when cluster marker clicked
 * - Syncs map position as user navigates within cluster
 *
 * @performance
 * - Uses useCallback for stable function references
 * - Minimal re-renders via focused state updates
 * - No external API calls or network requests
 */
function useMapLightboxSync({ mapRef }) {
  // Lightbox state
  const [isLightboxOpen, setIsLightboxOpen] = useState(false)
  const [currentPhoto, setCurrentPhoto] = useState(null)
  const [highlightedPhotoPath, setHighlightedPhotoPath] = useState(null)
  const [, setCurrentClusterMarker] = useState(null)

  // Cluster navigation state (delegated to useClusterNavigation)
  const {
    currentPhoto: clusterCurrentPhoto,
    currentIndex,
    total,
    position,
    hasNext,
    hasPrevious,
    goNext: clusterGoNext,
    goPrevious: clusterGoPrevious,
    goToIndex,
    setCluster,
    clearCluster,
  } = useClusterNavigation()

  // Get cluster photos array for external access
  const [clusterPhotos, setClusterPhotos] = useState([])

  /**
   * Pan map to photo location if GPS coordinates available
   *
   * @private
   * @param {Object} photo - Photo object with latitude/longitude
   */
  const panMapToPhoto = useCallback(
    (photo) => {
      if (!mapRef?.current || !photo) return

      // Check if photo has valid GPS coordinates
      const hasValidGPS =
        photo.latitude !== null &&
        photo.latitude !== undefined &&
        photo.longitude !== null &&
        photo.longitude !== undefined

      if (!hasValidGPS) return

      try {
        const currentZoom = mapRef.current.getZoom?.() || 13
        mapRef.current.flyTo([photo.latitude, photo.longitude], currentZoom)
      } catch {
        // Silently handle map errors (expected for certain edge cases)
      }
    },
    [mapRef]
  )

  /**
   * Open lightbox with photo and optional cluster context
   *
   * @param {Object} photo - Photo object to display
   * @param {Object} [clusterMarker] - Optional cluster marker (for spiderfy and navigation)
   */
  const openLightbox = useCallback(
    (photo, clusterMarker = null) => {
      if (!photo) return

      setCurrentPhoto(photo)
      setIsLightboxOpen(true)
      setHighlightedPhotoPath(photo.path || null)

      // Pan map to photo location (if GPS available)
      panMapToPhoto(photo)

      // Handle cluster context if provided
      if (clusterMarker) {
        setCurrentClusterMarker(clusterMarker)

        // Spiderfy cluster if method exists
        if (typeof clusterMarker.spiderfy === 'function') {
          try {
            clusterMarker.spiderfy()
          } catch (error) {
            console.warn('Error spiderfying cluster:', error)
          }
        }

        // Extract photos from cluster for navigation
        const photos = extractPhotosFromCluster(clusterMarker)
        setClusterPhotos(photos)

        // Set up cluster navigation
        if (photos.length > 0) {
          const startIndex = findPhotoIndexInCluster(photos, photo.path)
          setCluster(photos, startIndex >= 0 ? startIndex : 0)
        }
      } else {
        // No cluster - clear cluster state
        setCurrentClusterMarker(null)
        setClusterPhotos([])
        clearCluster()
      }
    },
    [panMapToPhoto, setCluster, clearCluster]
  )

  /**
   * Close lightbox and reset all state
   */
  const closeLightbox = useCallback(() => {
    setIsLightboxOpen(false)
    setCurrentPhoto(null)
    setHighlightedPhotoPath(null)
    setCurrentClusterMarker(null)
    setClusterPhotos([])
    clearCluster()
  }, [clearCluster])

  /**
   * Select/change current photo (syncs map position and highlight)
   *
   * @param {Object} photo - New photo to select
   */
  const selectPhoto = useCallback(
    (photo) => {
      if (!photo) return

      setCurrentPhoto(photo)
      setHighlightedPhotoPath(photo.path || null)
      panMapToPhoto(photo)
    },
    [panMapToPhoto]
  )

  /**
   * Handler for individual marker clicks
   *
   * @param {Object} marker - Leaflet marker instance
   * @param {Object} photo - Photo data associated with marker
   */
  const onMarkerClick = useCallback(
    (marker, photo) => {
      openLightbox(photo)
    },
    [openLightbox]
  )

  /**
   * Handler for cluster marker clicks
   *
   * @param {Object} clusterMarker - Leaflet cluster marker with getAllChildMarkers
   * @param {Object} clickedPhoto - Photo data that was clicked within cluster
   */
  const onClusterClick = useCallback(
    (clusterMarker, clickedPhoto) => {
      openLightbox(clickedPhoto, clusterMarker)
    },
    [openLightbox]
  )

  /**
   * Navigate to next photo in cluster
   */
  const goNext = useCallback(() => {
    clusterGoNext()
  }, [clusterGoNext])

  /**
   * Navigate to previous photo in cluster
   */
  const goPrevious = useCallback(() => {
    clusterGoPrevious()
  }, [clusterGoPrevious])

  /**
   * Sync current photo when cluster navigation changes
   */
  useEffect(() => {
    if (clusterCurrentPhoto && isLightboxOpen) {
      selectPhoto(clusterCurrentPhoto)
    }
  }, [clusterCurrentPhoto, isLightboxOpen, selectPhoto])

  return {
    // State
    isLightboxOpen,
    currentPhoto,
    highlightedPhotoPath,

    // Cluster navigation (from useClusterNavigation)
    clusterPhotos,
    currentIndex,
    total,
    position,
    hasNext,
    hasPrevious,
    goNext,
    goPrevious,
    goToIndex,

    // Actions
    openLightbox,
    closeLightbox,
    selectPhoto,

    // Map event handlers
    onMarkerClick,
    onClusterClick,
  }
}

export default useMapLightboxSync
