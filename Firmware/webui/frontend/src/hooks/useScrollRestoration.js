import { useRef, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'gallery-scroll-position';
const POSITION_TTL_MS = 30000; // 30 seconds

/**
 * Scroll position restoration for virtual grid
 * Saves and restores scroll position across navigation
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
   */
  const saveScrollPosition = useCallback(() => {
    if (!scrollRef.current) return;

    const position = {
      scrollTop: scrollRef.current.scrollTop,
      timestamp: Date.now(),
      key
    };

    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(position));
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
   */
  const restoreScrollPosition = useCallback(() => {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (!saved) return;

    try {
      const position = JSON.parse(saved);

      // Check TTL and key match
      const isExpired = Date.now() - position.timestamp >= POSITION_TTL_MS;
      const keyMatches = position.key === key;

      if (isExpired || !keyMatches) {
        // Clear stale or mismatched position
        sessionStorage.removeItem(STORAGE_KEY);
        return;
      }

      // Restore position after a short delay to ensure DOM is ready
      setTimeout(() => {
        scrollTo(position.scrollTop);
      }, 100);
    } catch (err) {
      console.error('Failed to restore scroll position:', err);
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
