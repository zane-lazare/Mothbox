import { useState, useEffect, useRef, useCallback } from 'react'
import { getThumbnailUrl } from '../utils/api'
import { imageCache } from '../utils/imageCache'

/**
 * Progressive image loading stage
 */
type LoadingStage = 'idle' | 'thumbnail' | 'full' | 'loaded' | 'error'

/**
 * Options for progressive image loading
 */
interface UseProgressiveImageOptions {
  thumbnailSize?: number
  fullSize?: number
  autoLoad?: boolean
}

/**
 * Return type for useProgressiveImage hook
 */
interface UseProgressiveImageReturn {
  src: string | null
  isLoading: boolean
  error: Error | null
  loadImage: () => Promise<void>
  stage: LoadingStage
}

/**
 * Progressive image loading hook
 * Loads low-res thumbnail first, then full resolution for smooth blur-up effect
 *
 * Features:
 * - Two-stage loading (thumbnail → full)
 * - Browser cache integration (skips network if cached)
 * - LRU cache for decoded Image objects
 * - Automatic cleanup on unmount
 *
 * Loading stages:
 * - idle: Not started
 * - thumbnail: Loading/showing thumbnail (low-res)
 * - full: Loading full resolution
 * - loaded: Full resolution loaded
 * - error: Failed to load
 *
 * @param {string} photoPath - Photo path
 * @param {object} options - Configuration options
 * @param {number} [options.thumbnailSize=64] - Thumbnail size in pixels
 * @param {number} [options.fullSize=256] - Full image size in pixels
 * @param {boolean} [options.autoLoad=true] - Start loading automatically
 * @returns {object} { src, isLoading, error, loadImage, stage }
 */
export default function useProgressiveImage(
  photoPath: string,
  options: UseProgressiveImageOptions = {}
): UseProgressiveImageReturn {
  const {
    thumbnailSize = 64,
    fullSize = 256,
    autoLoad = true
  } = options

  const [stage, setStage] = useState<LoadingStage>('idle')
  const [currentSrc, setCurrentSrc] = useState<string | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const isMountedRef = useRef<boolean>(true)
  const pendingImagesRef = useRef<Set<HTMLImageElement>>(new Set())

  /**
   * Load an image and return promise that resolves with URL
   * Checks cache first to avoid redundant network requests
   * Properly cleans up Image object to prevent memory leaks
   * Tracks pending images to abort on unmount
   *
   * @param {string} url - Image URL to load
   * @param {string} cacheKey - Cache key for this image
   * @returns {Promise<string>} Resolves with URL on success, rejects with cleanup
   */
  const loadImage = useCallback((url: string, cacheKey: string): Promise<string> => {
    // Check cache first
    const cached = imageCache.get(cacheKey)
    if (cached) {
      // Return immediately with cached URL
      return Promise.resolve(url)
    }

    // Not in cache - load from network
    return new Promise((resolve, reject) => {
      const img = new Image()

      // Track pending image to allow cleanup on unmount
      pendingImagesRef.current.add(img)

      // Cleanup function to prevent memory leaks
      // Setting img.src = '' is necessary for proper garbage collection in Safari and older Chrome
      // Also aborts pending network requests
      const cleanup = () => {
        img.onload = null
        img.onerror = null
        img.src = '' // Required for GC - aborts pending network request
        pendingImagesRef.current.delete(img)
      }

      img.onload = () => {
        pendingImagesRef.current.delete(img)
        // Cache the loaded image object
        imageCache.set(cacheKey, img)
        resolve(url)
        // Don't cleanup here - image is cached and may be used again
      }

      img.onerror = (err) => {
        cleanup()
        reject(err)
      }

      img.src = url
    })
  }, [])

  /**
   * Start progressive loading sequence
   * Loads thumbnail first, then full resolution
   * Uses cache to skip network requests for previously loaded images
   */
  const startLoading = useCallback(async () => {
    if (!photoPath) {
      return
    }

    try {
      setError(null)

      // Stage 1: Load thumbnail (low-res)
      setStage('thumbnail')
      const thumbnailUrl = getThumbnailUrl(photoPath, thumbnailSize)
      const thumbnailCacheKey = `${photoPath}:${thumbnailSize}`

      await loadImage(thumbnailUrl, thumbnailCacheKey)

      if (!isMountedRef.current) return
      setCurrentSrc(thumbnailUrl)

      // Stage 2: Load full resolution
      setStage('full')
      const fullUrl = getThumbnailUrl(photoPath, fullSize)
      const fullCacheKey = `${photoPath}:${fullSize}`

      await loadImage(fullUrl, fullCacheKey)

      if (!isMountedRef.current) return
      setCurrentSrc(fullUrl)
      setStage('loaded')
    } catch (err) {
      if (!isMountedRef.current) return
      setError(err as Error)
      setStage('error')
    }
  }, [photoPath, thumbnailSize, fullSize, loadImage])

  // Auto-load on mount or when photoPath changes
  useEffect(() => {
    isMountedRef.current = true
    // Capture ref value for cleanup to avoid stale reference warning
    const pendingImages = pendingImagesRef.current

    if (autoLoad) {
      startLoading()
    }

    return () => {
      isMountedRef.current = false

      // Abort all pending image loads to prevent memory leaks and race conditions
      // This is critical when component unmounts while images are still loading
      pendingImages.forEach(img => {
        img.onload = null
        img.onerror = null
        img.src = '' // Abort network request
      })
      pendingImages.clear()
    }
  }, [autoLoad, startLoading])

  return {
    src: currentSrc,
    isLoading: ['thumbnail', 'full'].includes(stage),
    error,
    loadImage: startLoading,
    stage
  }
}
