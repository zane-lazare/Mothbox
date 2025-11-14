import { useEffect, useState } from 'react'

/**
 * useImagePreload Hook
 *
 * Preloads adjacent images for smoother navigation in the photo lightbox.
 * Loads current image first, then preloads previous and next images in background.
 *
 * @param {Object} params
 * @param {Object} params.currentPhoto - Current photo object
 * @param {Array} params.photos - Full array of photos
 * @param {number} params.currentIndex - Index of current photo
 * @returns {Object} { currentImage, isLoading }
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
