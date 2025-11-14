import { useEffect, useState } from 'react'

/**
 * Custom hook for progressive image preloading in the photo lightbox.
 *
 * Preloads the current image first (priority), then preloads adjacent images
 * (previous and next) in the background for smooth navigation. Uses native
 * Image() API for efficient browser caching.
 *
 * @hook
 * @param {Object} config - Hook configuration
 * @param {Object} config.currentPhoto - Current photo object {path, filename, ...}
 * @param {Array<Object>} config.photos - Array of all photos
 * @param {number} config.currentIndex - Current photo index in photos array
 *
 * @returns {Object} Preload state
 * @returns {string|null} returns.currentImage - Current image URL (null while loading)
 * @returns {boolean} returns.isLoading - True while current image loading
 *
 * @example
 * const { currentImage, isLoading } = useImagePreload({
 *   currentPhoto: photos[5],
 *   photos,
 *   currentIndex: 5,
 * })
 *
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

    setIsLoading(true)

    // Build list of images to preload
    const imagesToPreload = []

    // Always load current image first
    const currentUrl = `/api/gallery/photo/${currentPhoto.path}`
    imagesToPreload.push({ url: currentUrl, priority: 'current' })

    // Preload next image
    if (currentIndex < photos.length - 1) {
      const nextPhoto = photos[currentIndex + 1]
      const nextUrl = `/api/gallery/photo/${nextPhoto.path}`
      imagesToPreload.push({ url: nextUrl, priority: 'next' })
    }

    // Preload previous image
    if (currentIndex > 0) {
      const prevPhoto = photos[currentIndex - 1]
      const prevUrl = `/api/gallery/photo/${prevPhoto.path}`
      imagesToPreload.push({ url: prevUrl, priority: 'prev' })
    }

    // Track loaded images
    let loadedCount = 0
    const images = []

    // Load current image first
    const currentImg = new Image()
    images.push(currentImg)

    currentImg.onload = () => {
      setCurrentImage(currentUrl)
      setIsLoading(false)
      loadedCount++

      // After current loads, preload adjacent images
      imagesToPreload.slice(1).forEach((item) => {
        const img = new Image()
        images.push(img)
        img.onload = () => {
          loadedCount++
        }
        img.onerror = () => {
          loadedCount++
        }
        img.src = item.url
      })
    }

    currentImg.onerror = () => {
      setIsLoading(false)
      loadedCount++
    }

    currentImg.src = currentUrl

    // Cleanup function
    return () => {
      images.forEach((img) => {
        img.onload = null
        img.onerror = null
      })
    }
  }, [currentPhoto, photos, currentIndex])

  return {
    currentImage,
    isLoading,
  }
}

export default useImagePreload
