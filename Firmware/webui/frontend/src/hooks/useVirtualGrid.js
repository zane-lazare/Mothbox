/**
 * Custom hook for virtual grid layout calculations
 *
 * Tracks container dimensions using ResizeObserver and provides
 * grid parameters for react-window virtualization.
 *
 * @module hooks/useVirtualGrid
 */

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { calculateGridDimensions } from '../utils/gridCalculations';

/**
 * Simple debounce utility for ResizeObserver callbacks
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(fn, delay) {
  let timeoutId = null;
  return function debounced(...args) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      fn(...args);
      timeoutId = null;
    }, delay);
  };
}

/**
 * Custom hook for virtual grid layout calculations
 *
 * Tracks container dimensions and provides grid parameters for react-window.
 * Automatically recalculates on container resize and photo count changes.
 *
 * @param {number} photoCount - Total number of photos
 * @param {Object} options - Configuration options
 * @param {number} options.gap - Gap between items (default: 16px)
 * @param {number} options.aspectRatio - Width/height ratio (default: 4/3)
 * @param {Object} options.breakpoints - Custom breakpoints
 * @returns {Object} Grid layout parameters and container ref
 *
 * @example
 * const { containerRef, columnCount, rowCount, itemWidth, itemHeight, totalHeight } =
 *   useVirtualGrid(photoCount, { gap: 16, aspectRatio: 4/3 });
 *
 * return (
 *   <div ref={containerRef}>
 *     <FixedSizeGrid
 *       columnCount={columnCount}
 *       rowCount={rowCount}
 *       columnWidth={itemWidth}
 *       rowHeight={itemHeight}
 *       height={600}
 *       width="100%"
 *     />
 *   </div>
 * );
 */
export default function useVirtualGrid(photoCount, options = {}) {
  const [containerWidth, setContainerWidth] = useState(0);
  const resizeObserverRef = useRef(null);
  const debouncedSetWidthRef = useRef(null);

  // Create debounced width setter (memoized to avoid recreation)
  if (!debouncedSetWidthRef.current) {
    debouncedSetWidthRef.current = debounce((width) => {
      setContainerWidth(width);
    }, 150); // 150ms debounce - balance between responsiveness and performance
  }

  // Callback ref that sets up ResizeObserver when element is attached
  const containerRef = useCallback((node) => {
    // Disconnect previous observer if any
    if (resizeObserverRef.current) {
      resizeObserverRef.current.disconnect();
    }

    // Set up new observer for the new node
    if (node) {
      resizeObserverRef.current = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width } = entry.contentRect;
          // Use debounced setter to prevent excessive re-renders during window resizing
          debouncedSetWidthRef.current(width);
        }
      });

      resizeObserverRef.current.observe(node);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
      }
    };
  }, []);

  // Calculate grid dimensions (memoized for performance)
  const gridDimensions = useMemo(() => {
    if (containerWidth === 0) {
      // Before ResizeObserver fires, return default/zero state
      return {
        columnCount: 1,
        rowCount: photoCount,
        itemWidth: 0,
        itemHeight: 0,
        totalHeight: 0,
      };
    }

    return calculateGridDimensions(containerWidth, photoCount, options);
  }, [containerWidth, photoCount, options]);

  return {
    containerRef,
    ...gridDimensions,
  };
}
