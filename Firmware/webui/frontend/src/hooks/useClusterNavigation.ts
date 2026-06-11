import { useState, useCallback, useMemo } from 'react'

/**
 * Photo type (simplified for cluster navigation)
 */
interface Photo {
  [key: string]: unknown
}

/**
 * Return type for useClusterNavigation hook
 */
interface UseClusterNavigationResult {
  currentPhoto: Photo | null
  currentIndex: number
  total: number
  position: string
  hasNext: boolean
  hasPrevious: boolean
  goNext: () => void
  goPrevious: () => void
  goToIndex: (index: number) => void
  setCluster: (photos: Photo[], startIndex?: number) => void
  clearCluster: () => void
}

/**
 * Custom hook for navigating within cluster photos in the photo lightbox.
 *
 * Provides navigation controls for moving between photos within a single cluster,
 * with wrap-around behavior at cluster boundaries. Supports keyboard navigation,
 * direct index jumping, and displays current position within the cluster.
 *
 * @hook
 *
 * @returns {Object} Navigation state and controls
 * @returns {Object|null} returns.currentPhoto - Current photo object
 * @returns {number} returns.currentIndex - 0-based index (-1 if no cluster)
 * @returns {number} returns.total - Total photos in cluster
 * @returns {string} returns.position - Display string (e.g., "3 of 5")
 * @returns {boolean} returns.hasNext - True if not at last photo
 * @returns {boolean} returns.hasPrevious - True if not at first photo
 * @returns {Function} returns.goNext - Navigate to next photo (wraps around)
 * @returns {Function} returns.goPrevious - Navigate to previous photo (wraps around)
 * @returns {Function} returns.goToIndex - Navigate to specific index
 * @returns {Function} returns.setCluster - Set cluster photos and starting index
 * @returns {Function} returns.clearCluster - Reset to empty state
 *
 * @example
 * // Initialize and set cluster
 * const {
 *   currentPhoto,
 *   position,
 *   hasNext,
 *   hasPrevious,
 *   goNext,
 *   goPrevious,
 * } = useClusterNavigation()
 *
 * // Set cluster when photo clicked
 * setCluster(clusterPhotos, clickedPhotoIndex)
 *
 * // Navigate
 * <button onClick={goPrevious} disabled={!hasPrevious}>Previous</button>
 * <span>{position}</span>
 * <button onClick={goNext} disabled={!hasNext}>Next</button>
 *
 * @strategy Navigation Behavior
 * - Wraps around at boundaries (last → first, first → last)
 * - Single photo clusters: navigation disabled (hasNext/hasPrevious = false)
 * - Empty clusters: returns null photo, -1 index, "0 of 0" position
 * - Invalid index in goToIndex(): silently ignored (maintains current index)
 *
 * @performance
 * - Uses useMemo for derived values (hasNext, hasPrevious, position)
 * - Uses useCallback for stable function references
 * - No external dependencies or API calls
 */
function useClusterNavigation(): UseClusterNavigationResult {
  const [clusterPhotos, setClusterPhotos] = useState<Photo[]>([])
  const [currentIndex, setCurrentIndex] = useState(-1)

  /**
   * Navigate to next photo in cluster (wraps to first if at end)
   */
  const goNext = useCallback(() => {
    setCurrentIndex((prevIndex) => {
      if (clusterPhotos.length === 0) return -1
      if (clusterPhotos.length === 1) return prevIndex
      return (prevIndex + 1) % clusterPhotos.length
    })
  }, [clusterPhotos.length])

  /**
   * Navigate to previous photo in cluster (wraps to last if at start)
   */
  const goPrevious = useCallback(() => {
    setCurrentIndex((prevIndex) => {
      if (clusterPhotos.length === 0) return -1
      if (clusterPhotos.length === 1) return prevIndex
      return prevIndex - 1 < 0 ? clusterPhotos.length - 1 : prevIndex - 1
    })
  }, [clusterPhotos.length])

  /**
   * Navigate to specific index in cluster
   * @param {number} index - Target index (0-based)
   */
  const goToIndex = useCallback(
    (index: number) => {
      if (index >= 0 && index < clusterPhotos.length) {
        setCurrentIndex(index)
      }
      // Silently ignore invalid indices
    },
    [clusterPhotos.length]
  )

  /**
   * Set cluster photos and optional starting index
   * @param {Array<Object>} photos - Array of photo objects
   * @param {number} [startIndex=0] - Starting index (defaults to 0)
   */
  const setCluster = useCallback((photos: Photo[], startIndex = 0) => {
    if (!photos || photos.length === 0) {
      setClusterPhotos([])
      setCurrentIndex(-1)
      return
    }

    setClusterPhotos(photos)
    const validStartIndex = startIndex >= 0 && startIndex < photos.length ? startIndex : 0
    setCurrentIndex(validStartIndex)
  }, [])

  /**
   * Clear cluster and reset to empty state
   */
  const clearCluster = useCallback(() => {
    setClusterPhotos([])
    setCurrentIndex(-1)
  }, [])

  // Derived values (memoized for performance)
  const currentPhoto = useMemo(() => {
    if (currentIndex >= 0 && currentIndex < clusterPhotos.length) {
      return clusterPhotos[currentIndex]
    }
    return null
  }, [clusterPhotos, currentIndex])

  const total = clusterPhotos.length

  const hasNext = useMemo(() => {
    if (clusterPhotos.length <= 1) return false
    return currentIndex < clusterPhotos.length - 1
  }, [clusterPhotos.length, currentIndex])

  const hasPrevious = useMemo(() => {
    if (clusterPhotos.length <= 1) return false
    return currentIndex > 0
  }, [clusterPhotos.length, currentIndex])

  const position = useMemo(() => {
    if (clusterPhotos.length === 0) return '0 of 0'
    return `${currentIndex + 1} of ${clusterPhotos.length}`
  }, [clusterPhotos.length, currentIndex])

  return {
    currentPhoto,
    currentIndex,
    total,
    position,
    hasNext,
    hasPrevious,
    goNext,
    goPrevious,
    goToIndex,
    setCluster,
    clearCluster,
  }
}

export default useClusterNavigation
