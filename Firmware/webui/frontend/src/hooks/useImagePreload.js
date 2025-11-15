import { useEffect, useState } from 'react'
import { getPhotoUrl } from '../utils/api'

/**
 * Custom hook for progressive image preloading in the photo lightbox.
 *
 * Preloads the current image first (priority), then preloads adjacent images
 * (previous and next) in the background for smooth navigation. Uses native
 * Image() API for efficient browser caching.
 *
 * This hook works primarily via side effects (browser cache population).
 * The return values are currently unused by PhotoLightbox.jsx but are
 * exported for future use cases (e.g., loading spinners, skeleton screens).
 *
 * @hook
 * @param {Object} config - Hook configuration
 * @param {Object} config.currentPhoto - Current photo object {path, filename, ...}
 * @param {Array<Object>} config.photos - Array of all photos
 * @param {number} config.currentIndex - Current photo index in photos array
 *
 * @returns {Object} Preload state (optional - can be ignored if only using for caching)
 * @returns {string|null} returns.currentImage - Current image URL (null while loading)
 * @returns {boolean} returns.isLoading - True while current image loading
 *
 * @example
 * // Current usage (side-effect only)
 * useImagePreload({ currentPhoto: photos[5], photos, currentIndex: 5 })
 *
 * // Future usage with loading state
 * const { currentImage, isLoading } = useImagePreload({
 *   currentPhoto: photos[5],
 *   photos,
 *   currentIndex: 5,
 * })
 * {isLoading && <Spinner />}
 * {currentImage && <img src={currentImage} />}
 *
 * @strategy Preload Priority
 * 1. Current image: Loads first, updates isLoading state
 * 2. Next image: Preloads in background after current loads
 * 3. Previous image: Preloads in background after current loads
 *
 * @performance
 * - Uses browser's native image cache
 * - Non-blocking background preloading
 * - Automatic cleanup on unmount
 * - Restarts preload sequence when currentPhoto changes
 */
function useImagePreload({ currentPhoto, photos, currentIndex }) {
  const [isLoading, setIsLoading] = useState(true)
  const [currentImage, setCurrentImage] = useState(null)

  useEffect(() => {
    if (!currentPhoto || !photos || currentIndex < 0) {
      setIsLoading(false)
      return
    }

    let cancelled = false // Prevent state updates after unmount
    setIsLoading(true)

    // Build list of images to preload (max 3: current + next + prev)
    // Note: Rapid navigation is handled by cleanup - previous effect cancels
    // pending loads before starting new ones, preventing request queue buildup
    const imagesToPreload = []

    // Always load current image first
    const currentUrl = getPhotoUrl(currentPhoto.path)
    imagesToPreload.push({ url: currentUrl, priority: 'current' })

    // Preload next image
    if (currentIndex < photos.length - 1) {
      const nextPhoto = photos[currentIndex + 1]
      const nextUrl = getPhotoUrl(nextPhoto.path)
      imagesToPreload.push({ url: nextUrl, priority: 'next' })
    }

    // Preload previous image
    if (currentIndex > 0) {
      const prevPhoto = photos[currentIndex - 1]
      const prevUrl = getPhotoUrl(prevPhoto.path)
      imagesToPreload.push({ url: prevUrl, priority: 'prev' })
    }

    // Track loaded images - create ALL images synchronously for proper cleanup
    const images = []

    // Create current image
    const currentImg = new Image()
    images.push(currentImg)

    // Create adjacent images immediately (before onload callback)
    // This ensures cleanup function has access to all images
    const adjacentImages = imagesToPreload.slice(1).map(() => new Image())
    images.push(...adjacentImages)

    currentImg.onload = () => {
      if (cancelled) return // Prevent state updates after unmount
      setCurrentImage(currentUrl)
      setIsLoading(false)

      // After current loads, start preloading adjacent images
      adjacentImages.forEach((img, index) => {
        const item = imagesToPreload[index + 1]

        img.onload = () => {
          if (cancelled) return // Prevent callbacks after unmount
          if (import.meta.env.DEV) {
            console.debug(`[ImagePreload] Preloaded ${item.priority} image:`, item.url)
          }
        }
        img.onerror = (e) => {
          if (cancelled) return // Prevent callbacks after unmount
          if (import.meta.env.DEV) {
            console.warn(`[ImagePreload] Failed to preload ${item.priority} image:`, item.url, e)
          }
        }
        img.src = item.url
      })
    }

    currentImg.onerror = (e) => {
      if (cancelled) return // Prevent state updates after unmount
      setIsLoading(false)
      if (import.meta.env.DEV) {
        console.error('[ImagePreload] Failed to load current image:', currentUrl, e)
      }
    }

    currentImg.src = currentUrl

    // Cleanup function - set cancellation flag FIRST, then clean up images
    return () => {
      cancelled = true // Set flag first to prevent any pending callbacks
      images.forEach((img) => {
        img.onload = null
        img.onerror = null
        img.src = '' // Cancel any pending loads and free image data
      })
      // Clear array to help garbage collection
      images.length = 0
    }
  }, [currentPhoto, photos, currentIndex])

  return {
    currentImage,
    isLoading,
  }
}

export default useImagePreload
