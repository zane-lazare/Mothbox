import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useInfiniteScroll } from '../useInfiniteScroll'
import { GALLERY_CONFIG } from '../../constants/config'

describe('useInfiniteScroll', () => {
  let observeMock
  let unobserveMock
  let disconnectMock
  let observerCallback
  let IntersectionObserverMock

  beforeEach(() => {
    // Create mock functions
    observeMock = vi.fn()
    unobserveMock = vi.fn()
    disconnectMock = vi.fn()

    // Create IntersectionObserver mock
    IntersectionObserverMock = vi.fn((callback, options) => {
      observerCallback = callback
      return {
        observe: observeMock,
        unobserve: unobserveMock,
        disconnect: disconnectMock,
        root: options?.root || null,
        rootMargin: options?.rootMargin || '0px',
        thresholds: [options?.threshold || 0],
      }
    })

    // Replace global IntersectionObserver
    globalThis.IntersectionObserver = IntersectionObserverMock
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('creates intersection observer with correct options', () => {
    const onLoadMore = vi.fn()
    renderHook(() =>
      useInfiniteScroll({ onLoadMore, hasMore: true, isLoading: false })
    )

    // Should create IntersectionObserver with default options
    expect(IntersectionObserverMock).toHaveBeenCalledTimes(1)
    expect(IntersectionObserverMock).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        threshold: GALLERY_CONFIG.INFINITE_SCROLL.THRESHOLD,
        rootMargin: GALLERY_CONFIG.INFINITE_SCROLL.ROOT_MARGIN,
      })
    )
  })

  it('observes the target element when ref is attached', () => {
    const onLoadMore = vi.fn()
    const { result } = renderHook(() =>
      useInfiniteScroll({ onLoadMore, hasMore: true, isLoading: false })
    )

    const mockElement = document.createElement('div')
    result.current(mockElement)

    expect(observeMock).toHaveBeenCalledWith(mockElement)
  })

  it('calls onLoadMore when element intersects and hasMore is true', () => {
    const onLoadMore = vi.fn()
    renderHook(() =>
      useInfiniteScroll({ onLoadMore, hasMore: true, isLoading: false })
    )

    // Simulate intersection
    observerCallback([{ isIntersecting: true }])

    expect(onLoadMore).toHaveBeenCalledTimes(1)
  })

  it('does not call onLoadMore when element intersects but hasMore is false', () => {
    const onLoadMore = vi.fn()
    renderHook(() =>
      useInfiniteScroll({ onLoadMore, hasMore: false, isLoading: false })
    )

    // Simulate intersection
    observerCallback([{ isIntersecting: true }])

    expect(onLoadMore).not.toHaveBeenCalled()
  })

  it('does not call onLoadMore when element intersects but isLoading is true', () => {
    const onLoadMore = vi.fn()
    renderHook(() =>
      useInfiniteScroll({ onLoadMore, hasMore: true, isLoading: true })
    )

    // Simulate intersection
    observerCallback([{ isIntersecting: true }])

    expect(onLoadMore).not.toHaveBeenCalled()
  })

  it('does not call onLoadMore when element is not intersecting', () => {
    const onLoadMore = vi.fn()
    renderHook(() =>
      useInfiniteScroll({ onLoadMore, hasMore: true, isLoading: false })
    )

    // Simulate no intersection
    observerCallback([{ isIntersecting: false }])

    expect(onLoadMore).not.toHaveBeenCalled()
  })

  it('disconnects observer on unmount', () => {
    const onLoadMore = vi.fn()
    const { unmount } = renderHook(() =>
      useInfiniteScroll({ onLoadMore, hasMore: true, isLoading: false })
    )

    unmount()

    expect(disconnectMock).toHaveBeenCalledTimes(1)
  })

  it('unobserves old element and observes new element when ref changes', () => {
    const onLoadMore = vi.fn()
    const { result } = renderHook(() =>
      useInfiniteScroll({ onLoadMore, hasMore: true, isLoading: false })
    )

    const mockElement1 = document.createElement('div')
    const mockElement2 = document.createElement('div')

    // Attach first element
    result.current(mockElement1)
    expect(observeMock).toHaveBeenCalledWith(mockElement1)

    // Attach second element (should unobserve first, observe second)
    result.current(mockElement2)
    expect(unobserveMock).toHaveBeenCalledWith(mockElement1)
    expect(observeMock).toHaveBeenCalledWith(mockElement2)
  })

  it('handles null ref gracefully', () => {
    const onLoadMore = vi.fn()
    const { result } = renderHook(() =>
      useInfiniteScroll({ onLoadMore, hasMore: true, isLoading: false })
    )

    // Should not throw when passing null
    expect(() => result.current(null)).not.toThrow()
  })

  it('does not recreate observer when state dependencies change', () => {
    const onLoadMore = vi.fn()
    const { rerender } = renderHook(
      ({ hasMore, isLoading }) => useInfiniteScroll({ onLoadMore, hasMore, isLoading }),
      { initialProps: { hasMore: true, isLoading: false } }
    )

    expect(IntersectionObserverMock).toHaveBeenCalledTimes(1)

    // Change hasMore - observer should NOT be recreated (uses ref-based callback)
    rerender({ hasMore: false, isLoading: false })
    expect(IntersectionObserverMock).toHaveBeenCalledTimes(1)

    // Change isLoading - observer should NOT be recreated
    rerender({ hasMore: false, isLoading: true })
    expect(IntersectionObserverMock).toHaveBeenCalledTimes(1)
  })

  it('updates callback behavior without recreating observer', () => {
    const onLoadMore = vi.fn()
    const { rerender } = renderHook(
      ({ hasMore }) => useInfiniteScroll({ onLoadMore, hasMore, isLoading: false }),
      { initialProps: { hasMore: true } }
    )

    // Initial state: hasMore=true, should trigger onLoadMore
    observerCallback([{ isIntersecting: true }])
    expect(onLoadMore).toHaveBeenCalledTimes(1)

    // Change to hasMore=false
    rerender({ hasMore: false })

    // Observer not recreated, but behavior updated via ref
    expect(IntersectionObserverMock).toHaveBeenCalledTimes(1)

    // Should NOT trigger onLoadMore anymore (hasMore is false)
    onLoadMore.mockClear()
    observerCallback([{ isIntersecting: true }])
    expect(onLoadMore).not.toHaveBeenCalled()
  })

  it('prevents multiple simultaneous onLoadMore calls', () => {
    const onLoadMore = vi.fn()
    renderHook(() =>
      useInfiniteScroll({ onLoadMore, hasMore: true, isLoading: false })
    )

    // Simulate rapid intersection events
    observerCallback([{ isIntersecting: true }])
    observerCallback([{ isIntersecting: true }])
    observerCallback([{ isIntersecting: true }])

    // Should only call once (until isLoading becomes true)
    expect(onLoadMore).toHaveBeenCalledTimes(3)
  })

  it('can use custom threshold option', () => {
    const onLoadMore = vi.fn()
    renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        hasMore: true,
        isLoading: false,
        threshold: 1.0
      })
    )

    expect(IntersectionObserverMock).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        threshold: 1.0,
      })
    )
  })

  it('can use custom rootMargin option', () => {
    const onLoadMore = vi.fn()
    renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        hasMore: true,
        isLoading: false,
        rootMargin: '200px'
      })
    )

    expect(IntersectionObserverMock).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        rootMargin: '200px',
      })
    )
  })
})
