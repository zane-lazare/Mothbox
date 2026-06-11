import { useEffect, useRef, useCallback } from 'react'

/**
 * Options for useInfiniteScroll hook
 */
interface UseInfiniteScrollOptions {
  onLoadMore: () => void
  hasMore: boolean
  isLoading: boolean
  threshold?: number
  rootMargin?: string
}

/**
 * useInfiniteScroll - Custom hook for implementing infinite scroll with Intersection Observer
 *
 * This hook sets up an intersection observer that triggers a callback when a sentinel element
 * enters the viewport, enabling automatic loading of more content as the user scrolls.
 *
 * @param {Object} options - Configuration options
 * @param {Function} options.onLoadMore - Callback to load more data when sentinel is visible
 * @param {boolean} options.hasMore - Whether more data is available to load
 * @param {boolean} options.isLoading - Whether data is currently being loaded
 * @param {number} [options.threshold=0.5] - Intersection threshold (0.0 to 1.0)
 * @param {string} [options.rootMargin='100px'] - Root margin for intersection observer
 *
 * @returns {Function} - Ref callback to attach to the sentinel element
 *
 * @example
 * const sentinelRef = useInfiniteScroll({
 *   onLoadMore: fetchNextPage,
 *   hasMore: hasNextPage,
 *   isLoading: isFetchingNextPage,
 * })
 *
 * return (
 *   <div>
 *     {items.map(item => <Item key={item.id} {...item} />)}
 *     <div ref={sentinelRef} />
 *   </div>
 * )
 */
export function useInfiniteScroll({
  onLoadMore,
  hasMore,
  isLoading,
  threshold = 0.5,
  rootMargin = '100px',
}: UseInfiniteScrollOptions): (element: Element | null) => void {
  const observerRef = useRef<IntersectionObserver | null>(null)
  const elementRef = useRef<Element | null>(null)
  const callbackRef = useRef<((entries: IntersectionObserverEntry[]) => void) | null>(null)

  // Memoize the intersection callback
  const handleIntersection = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries

      // Only trigger load if:
      // 1. Element is intersecting
      // 2. More data is available
      // 3. Not currently loading
      if (entry.isIntersecting && hasMore && !isLoading) {
        onLoadMore()
      }
    },
    [hasMore, isLoading, onLoadMore]
  )

  // Performance Optimization: Store latest callback in ref to prevent observer recreation
  // When handleIntersection changes (due to prop updates like hasMore/isLoading),
  // we update callbackRef.current instead of recreating the IntersectionObserver.
  // This avoids expensive DOM operations while keeping behavior up-to-date.
  useEffect(() => {
    callbackRef.current = handleIntersection
  }, [handleIntersection])

  // Set up IntersectionObserver - only recreates if threshold/rootMargin change
  // Note: handleIntersection is intentionally NOT in dependencies.
  // The observer uses a stable wrapper callback that reads from callbackRef.current,
  // allowing behavior updates without expensive observer recreation.
  useEffect(() => {
    const options = {
      root: null, // Use viewport as root
      rootMargin,
      threshold,
    }

    // Stable wrapper callback - always calls the latest behavior via ref indirection
    // This prevents observer recreation when hasMore, isLoading, or onLoadMore change
    observerRef.current = new IntersectionObserver((entries) => {
      if (callbackRef.current) {
        callbackRef.current(entries)
      }
    }, options)

    // If we already have an element attached, observe it
    if (elementRef.current) {
      observerRef.current.observe(elementRef.current)
    }

    // Cleanup on unmount
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [rootMargin, threshold])

  // Ref callback to attach to sentinel element
  const setElement = useCallback((element: Element | null) => {
    // Unobserve old element if it exists
    if (elementRef.current && observerRef.current) {
      observerRef.current.unobserve(elementRef.current)
    }

    // Store new element reference
    elementRef.current = element

    // Observe new element if it exists
    if (element && observerRef.current) {
      observerRef.current.observe(element)
    }
  }, [])

  return setElement
}
