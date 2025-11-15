import { useState, useEffect, useRef, useCallback } from 'react';
import { getThumbnailUrl } from '../utils/api';
import { imageCache } from '../utils/imageCache';

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
export default function useProgressiveImage(photoPath, options = {}) {
  const {
    thumbnailSize = 64,
    fullSize = 256,
    autoLoad = true
  } = options;

  const [stage, setStage] = useState('idle');
  const [currentSrc, setCurrentSrc] = useState(null);
  const [error, setError] = useState(null);
  const isMountedRef = useRef(true);

  /**
   * Load an image and return promise that resolves with URL
   * Checks cache first to avoid redundant network requests
   *
   * @param {string} url - Image URL to load
   * @param {string} cacheKey - Cache key for this image
   * @returns {Promise<string>} Resolves with URL on success
   */
  const loadImage = useCallback((url, cacheKey) => {
    // Check cache first
    const cached = imageCache.get(cacheKey);
    if (cached) {
      // Return immediately with cached URL
      return Promise.resolve(url);
    }

    // Not in cache - load from network
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        // Cache the loaded image object
        imageCache.set(cacheKey, img);
        resolve(url);
      };
      img.onerror = (err) => reject(err);
      img.src = url;
    });
  }, []);

  /**
   * Start progressive loading sequence
   * Loads thumbnail first, then full resolution
   * Uses cache to skip network requests for previously loaded images
   */
  const startLoading = useCallback(async () => {
    if (!photoPath) {
      return;
    }

    try {
      setError(null);

      // Stage 1: Load thumbnail (low-res)
      setStage('thumbnail');
      const thumbnailUrl = getThumbnailUrl(photoPath, thumbnailSize);
      const thumbnailCacheKey = `${photoPath}:${thumbnailSize}`;

      await loadImage(thumbnailUrl, thumbnailCacheKey);

      if (!isMountedRef.current) return;
      setCurrentSrc(thumbnailUrl);

      // Stage 2: Load full resolution
      setStage('full');
      const fullUrl = getThumbnailUrl(photoPath, fullSize);
      const fullCacheKey = `${photoPath}:${fullSize}`;

      await loadImage(fullUrl, fullCacheKey);

      if (!isMountedRef.current) return;
      setCurrentSrc(fullUrl);
      setStage('loaded');
    } catch (err) {
      if (!isMountedRef.current) return;
      setError(err);
      setStage('error');
    }
  }, [photoPath, thumbnailSize, fullSize, loadImage]);

  // Auto-load on mount or when photoPath changes
  useEffect(() => {
    isMountedRef.current = true;

    if (autoLoad) {
      startLoading();
    }

    return () => {
      isMountedRef.current = false;
    };
  }, [autoLoad, startLoading]);

  return {
    src: currentSrc,
    isLoading: ['thumbnail', 'full'].includes(stage),
    error,
    loadImage: startLoading,
    stage
  };
}
