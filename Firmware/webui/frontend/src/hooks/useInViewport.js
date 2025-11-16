import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook using IntersectionObserver to detect when element is in viewport
 * Optimized for lazy loading - tracks "has ever been visible" for one-time loading
 *
 * @param {object} options - IntersectionObserver options
 * @param {string} options.rootMargin - Margin around root (e.g., '100px' for preloading)
 * @param {number|number[]} options.threshold - Percentage of element visibility (0-1)
 * @param {Element} options.root - Root element (default: viewport)
 * @returns {object} { ref, isInViewport, hasBeenInViewport }
 */
export default function useInViewport(options = {}) {
  const {
    rootMargin = '0px',
    threshold = 0.1,
    root = null
  } = options;

  const [isInViewport, setIsInViewport] = useState(false);
  const [hasBeenInViewport, setHasBeenInViewport] = useState(false);
  const elementRef = useRef(null);
  const observerRef = useRef(null);

  // Callback ref pattern for element attachment
  const setRef = useCallback((node) => {
    // Unobserve previous element if exists
    if (observerRef.current && elementRef.current) {
      observerRef.current.unobserve(elementRef.current);
    }

    // Update elementRef.current
    elementRef.current = node;

    // Observe new element if exists
    if (observerRef.current && node) {
      observerRef.current.observe(node);
    }
  }, []);

  useEffect(() => {
    // Disconnect existing observer before creating new one
    // Critical: Prevents memory leak when options change (e.g., rootMargin update)
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    // Create IntersectionObserver
    const callback = (entries) => {
      entries.forEach((entry) => {
        setIsInViewport(entry.isIntersecting);

        // Once in viewport, always remember
        if (entry.isIntersecting) {
          setHasBeenInViewport(true);
        }
      });
    };

    observerRef.current = new IntersectionObserver(callback, {
      root,
      rootMargin,
      threshold
    });

    // If element already attached, observe it
    if (elementRef.current) {
      observerRef.current.observe(elementRef.current);
    }

    // Cleanup function
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [rootMargin, threshold, root]);

  return {
    ref: setRef,
    isInViewport,
    hasBeenInViewport
  };
}
