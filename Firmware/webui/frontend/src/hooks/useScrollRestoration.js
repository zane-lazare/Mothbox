import { useRef, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'gallery-scroll-position';
const POSITION_TTL_MS = 30000; // 30 seconds

/**
 * Scroll position restoration for virtual grid
 * Saves and restores scroll position across navigation
 *
 * Used in Gallery component to restore scroll position when:
 * - Returning from lightbox view to gallery grid
 * - Navigating between pages
 *
 * Features:
 * - Automatic scroll position restoration on mount
 * - TTL-based expiration (30 seconds)
 * - Key-based isolation for multiple instances
 * - Works with both native scroll and react-window grids
 *
 * @param {string} key - Unique key for this scroll context
 * @returns {object} { scrollRef, saveScrollPosition, scrollTo }
 */
export default function useScrollRestoration(key = 'default') {
  const scrollRef = useRef(null);

  /**
   * Save current scroll position to sessionStorage
   * Handles QuotaExceededError gracefully (privacy mode, storage full)
   */
  const saveScrollPosition = useCallback(() => {
    if (!scrollRef.current) return;

    const position = {
      scrollTop: scrollRef.current.scrollTop,
      timestamp: Date.now(),
      key
    };

    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(position));
    } catch (e) {
      // QuotaExceededError occurs in:
      // - Private browsing mode (Safari, Firefox)
      // - When sessionStorage quota is full
      // Gracefully degrade: scroll restoration disabled, but app continues working
      if (e.name === 'QuotaExceededError') {
        console.warn('SessionStorage quota exceeded, scroll position not saved');
      } else {
        // Log unexpected errors for debugging
        console.error('Failed to save scroll position:', e);
      }
    }
  }, [key]);

  /**
   * Scroll to a specific offset
   * Works with both react-window grids and native elements
   *
   * @param {number} offset - Scroll offset in pixels
   */
  const scrollTo = useCallback((offset) => {
    if (!scrollRef.current) return;

    // For react-window FixedSizeGrid (has scrollTo method)
    if (typeof scrollRef.current.scrollTo === 'function') {
      scrollRef.current.scrollTo({ scrollTop: offset });
    } else {
      // For native scrollable elements
      scrollRef.current.scrollTop = offset;
    }
  }, []);

  /**
   * Restore scroll position from sessionStorage
   * Only restores if:
   * - Position exists
   * - Not expired (within TTL)
   * - Key matches
   *
   * Gracefully handles storage access errors (privacy mode)
   */
  const restoreScrollPosition = useCallback(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      if (!saved) return;

      const position = JSON.parse(saved);

      // Validate parsed JSON structure (defense against corrupted/malformed data)
      if (
        typeof position.scrollTop !== 'number' ||
        typeof position.timestamp !== 'number' ||
        typeof position.key !== 'string'
      ) {
        // Invalid structure - clear corrupted data
        try {
          sessionStorage.removeItem(STORAGE_KEY);
        } catch (e) {
          // Ignore errors when clearing (privacy mode)
        }
        return;
      }

      // Check TTL and key match
      const isExpired = Date.now() - position.timestamp >= POSITION_TTL_MS;
      const keyMatches = position.key === key;

      if (isExpired || !keyMatches) {
        // Clear stale or mismatched position
        try {
          sessionStorage.removeItem(STORAGE_KEY);
        } catch (e) {
          // Ignore errors when clearing (privacy mode)
        }
        return;
      }

      // Restore position on next animation frame to ensure DOM is ready
      // This is more reliable than setTimeout and syncs with browser paint cycle
      requestAnimationFrame(() => {
        scrollTo(position.scrollTop);
      });
    } catch (err) {
      // Gracefully handle:
      // - SecurityError: sessionStorage access blocked (privacy mode)
      // - JSON parse errors: corrupted data
      // - Other storage access errors
      console.warn('Failed to restore scroll position:', err.message);
    }
  }, [key, scrollTo]);

  // Restore position on mount
  useEffect(() => {
    restoreScrollPosition();
  }, [restoreScrollPosition]);

  return {
    scrollRef,
    saveScrollPosition,
    scrollTo
  };
}
