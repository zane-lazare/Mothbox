/**
 * LRU (Least Recently Used) cache for loaded DOM Image objects
 * Prevents repeated network requests and image decoding
 *
 * Features:
 * - Fixed maximum size (100 images by default)
 * - Automatic eviction of least recently used items
 * - Time-based expiration (5 minutes default)
 * - Hit/miss statistics tracking
 * - Works with any key type (string, number, object)
 *
 * Usage:
 *   imageCache.set('photo-key', imageObject);
 *   const cached = imageCache.get('photo-key');
 *   const stats = imageCache.getStats();
 */

/**
 * Cache entry with metadata
 */
interface CacheEntry {
  image: HTMLImageElement
  timestamp: number
}

/**
 * Cache statistics
 */
interface CacheStats {
  size: number
  maxSize: number
  hits: number
  misses: number
  hitRatio: number
}

class ImageCache {
  private maxSize: number
  private ttlMs: number
  private cache: Map<unknown, CacheEntry>
  private hits: number
  private misses: number

  /**
   * @param {number} maxSize - Maximum number of images to cache (default: 100)
   * @param {number} ttlMs - Time to live for cached items in milliseconds (default: 5 minutes)
   */
  constructor(maxSize: number = 100, ttlMs: number = 5 * 60 * 1000) {
    this.maxSize = maxSize
    this.ttlMs = ttlMs
    this.cache = new Map()
    this.hits = 0
    this.misses = 0
  }

  /**
   * Get image from cache
   * Updates LRU position on hit and checks expiration
   *
   * @param {any} key - Cache key
   * @returns {Image|null} Cached image or null if not found/expired
   */
  get(key: unknown): HTMLImageElement | null {
    if (this.cache.has(key)) {
      const entry = this.cache.get(key)!

      // Check if expired
      if (Date.now() - entry.timestamp > this.ttlMs) {
        this.cache.delete(key)
        this.misses++
        return null
      }

      // Move to end (most recently used) - update timestamp on access
      this.cache.delete(key)
      entry.timestamp = Date.now()
      this.cache.set(key, entry)

      this.hits++
      return entry.image
    }

    this.misses++
    return null
  }

  /**
   * Store image in cache with timestamp
   * Evicts least recently used item if cache is full
   *
   * @param {any} key - Cache key
   * @param {Image} image - Image object to cache
   */
  set(key: unknown, image: HTMLImageElement): void {
    // Remove if exists (will re-add at end for LRU)
    if (this.cache.has(key)) {
      this.cache.delete(key)
    }

    // Wrap image with metadata
    const entry: CacheEntry = {
      image,
      timestamp: Date.now()
    }

    // Add to end (most recently used)
    this.cache.set(key, entry)

    // Evict oldest if over limit
    if (this.cache.size > this.maxSize) {
      // First key is least recently used
      const firstKey = this.cache.keys().next().value
      this.cache.delete(firstKey)
    }
  }

  /**
   * Clear all cached images and reset statistics
   * Nullifies image references to help garbage collection
   */
  clear(): void {
    // Help GC by nullifying src references before clearing cache
    // This is safe here because we're clearing the entire cache
    for (const entry of this.cache.values()) {
      const img = entry?.image
      if (img && img.src) {
        img.onload = null
        img.onerror = null
        // Setting to empty string is safe when explicitly clearing
        img.src = ''
      }
    }

    this.cache.clear()
    this.hits = 0
    this.misses = 0
  }

  /**
   * Get cache statistics
   *
   * @returns {object} { size, maxSize, hits, misses, hitRatio }
   */
  getStats(): CacheStats {
    const total = this.hits + this.misses
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      hits: this.hits,
      misses: this.misses,
      hitRatio: total > 0 ? this.hits / total : 0
    }
  }
}

/**
 * Global image cache instance
 * Shared across all components for maximum efficiency
 */
export const imageCache = new ImageCache(100)
