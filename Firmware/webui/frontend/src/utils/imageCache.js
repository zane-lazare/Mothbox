/**
 * LRU (Least Recently Used) cache for loaded DOM Image objects
 * Prevents repeated network requests and image decoding
 *
 * Features:
 * - Fixed maximum size (100 images by default)
 * - Automatic eviction of least recently used items
 * - Hit/miss statistics tracking
 * - Works with any key type (string, number, object)
 *
 * Usage:
 *   imageCache.set('photo-key', imageObject);
 *   const cached = imageCache.get('photo-key');
 *   const stats = imageCache.getStats();
 */
class ImageCache {
  /**
   * @param {number} maxSize - Maximum number of images to cache (default: 100)
   */
  constructor(maxSize = 100) {
    this.maxSize = maxSize;
    this.cache = new Map();
    this.hits = 0;
    this.misses = 0;
  }

  /**
   * Get image from cache
   * Updates LRU position on hit
   *
   * @param {any} key - Cache key
   * @returns {Image|null} Cached image or null if not found
   */
  get(key) {
    if (this.cache.has(key)) {
      // Move to end (most recently used)
      const value = this.cache.get(key);
      this.cache.delete(key);
      this.cache.set(key, value);

      this.hits++;
      return value;
    }

    this.misses++;
    return null;
  }

  /**
   * Store image in cache
   * Evicts least recently used item if cache is full
   *
   * @param {any} key - Cache key
   * @param {Image} value - Image object to cache
   */
  set(key, value) {
    // Remove if exists (will re-add at end for LRU)
    if (this.cache.has(key)) {
      this.cache.delete(key);
    }

    // Add to end (most recently used)
    this.cache.set(key, value);

    // Evict oldest if over limit
    if (this.cache.size > this.maxSize) {
      // First key is least recently used
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
  }

  /**
   * Clear all cached images and reset statistics
   * Nullifies image references to help garbage collection
   */
  clear() {
    // Help GC by nullifying src references before clearing cache
    // This is safe here because we're clearing the entire cache
    for (const img of this.cache.values()) {
      if (img && img.src) {
        img.onload = null;
        img.onerror = null;
        // Setting to empty string is safe when explicitly clearing
        img.src = '';
      }
    }

    this.cache.clear();
    this.hits = 0;
    this.misses = 0;
  }

  /**
   * Get cache statistics
   *
   * @returns {object} { size, maxSize, hits, misses, hitRatio }
   */
  getStats() {
    const total = this.hits + this.misses;
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      hits: this.hits,
      misses: this.misses,
      hitRatio: total > 0 ? this.hits / total : 0
    };
  }
}

/**
 * Global image cache instance
 * Shared across all components for maximum efficiency
 */
export const imageCache = new ImageCache(100);
