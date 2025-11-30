import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import useClusterNavigation from '../useClusterNavigation'

describe('useClusterNavigation', () => {
  let mockClusterPhotos

  beforeEach(() => {
    // Mock cluster photos array
    mockClusterPhotos = [
      { path: 'cluster1_photo1.jpg', lat: 37.7749, lon: -122.4194 },
      { path: 'cluster1_photo2.jpg', lat: 37.7750, lon: -122.4195 },
      { path: 'cluster1_photo3.jpg', lat: 37.7751, lon: -122.4196 },
      { path: 'cluster1_photo4.jpg', lat: 37.7752, lon: -122.4197 },
      { path: 'cluster1_photo5.jpg', lat: 37.7753, lon: -122.4198 },
    ]
  })

  it('initializes with cluster photos and current index', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 2)
    })

    expect(result.current.currentPhoto).toEqual(mockClusterPhotos[2])
    expect(result.current.currentIndex).toBe(2)
    expect(result.current.total).toBe(5)
    expect(result.current.position).toBe('3 of 5')
  })

  it('navigates to next photo in cluster', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 1)
    })

    expect(result.current.currentPhoto).toEqual(mockClusterPhotos[1])

    act(() => {
      result.current.goNext()
    })

    expect(result.current.currentPhoto).toEqual(mockClusterPhotos[2])
    expect(result.current.currentIndex).toBe(2)
  })

  it('navigates to previous photo in cluster', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 3)
    })

    expect(result.current.currentPhoto).toEqual(mockClusterPhotos[3])

    act(() => {
      result.current.goPrevious()
    })

    expect(result.current.currentPhoto).toEqual(mockClusterPhotos[2])
    expect(result.current.currentIndex).toBe(2)
  })

  it('wraps around at cluster boundaries - next', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 4) // Last photo
    })

    expect(result.current.currentIndex).toBe(4)

    act(() => {
      result.current.goNext()
    })

    // Should wrap to first photo
    expect(result.current.currentIndex).toBe(0)
    expect(result.current.currentPhoto).toEqual(mockClusterPhotos[0])
  })

  it('wraps around at cluster boundaries - previous', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 0) // First photo
    })

    expect(result.current.currentIndex).toBe(0)

    act(() => {
      result.current.goPrevious()
    })

    // Should wrap to last photo
    expect(result.current.currentIndex).toBe(4)
    expect(result.current.currentPhoto).toEqual(mockClusterPhotos[4])
  })

  it('returns hasNext/hasPrevious flags correctly - middle', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 2)
    })

    expect(result.current.hasNext).toBe(true)
    expect(result.current.hasPrevious).toBe(true)
  })

  it('returns hasNext/hasPrevious flags correctly - first photo', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 0)
    })

    expect(result.current.hasNext).toBe(true)
    expect(result.current.hasPrevious).toBe(false)
  })

  it('returns hasNext/hasPrevious flags correctly - last photo', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 4)
    })

    expect(result.current.hasNext).toBe(false)
    expect(result.current.hasPrevious).toBe(true)
  })

  it('returns total count and current position', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 0)
    })

    expect(result.current.total).toBe(5)
    expect(result.current.position).toBe('1 of 5')

    act(() => {
      result.current.goNext()
    })

    expect(result.current.position).toBe('2 of 5')

    act(() => {
      result.current.goToIndex(4)
    })

    expect(result.current.position).toBe('5 of 5')
  })

  it('handles single-photo clusters', () => {
    const singlePhoto = [mockClusterPhotos[0]]
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(singlePhoto, 0)
    })

    expect(result.current.currentPhoto).toEqual(singlePhoto[0])
    expect(result.current.total).toBe(1)
    expect(result.current.position).toBe('1 of 1')
    expect(result.current.hasNext).toBe(false)
    expect(result.current.hasPrevious).toBe(false)

    // Navigation should not change index
    act(() => {
      result.current.goNext()
    })
    expect(result.current.currentIndex).toBe(0)

    act(() => {
      result.current.goPrevious()
    })
    expect(result.current.currentIndex).toBe(0)
  })

  it('resets when new cluster photos are provided', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 2)
    })

    expect(result.current.currentIndex).toBe(2)
    expect(result.current.total).toBe(5)

    const newCluster = [
      { path: 'cluster2_photo1.jpg', lat: 38.0, lon: -123.0 },
      { path: 'cluster2_photo2.jpg', lat: 38.1, lon: -123.1 },
      { path: 'cluster2_photo3.jpg', lat: 38.2, lon: -123.2 },
    ]

    act(() => {
      result.current.setCluster(newCluster, 1)
    })

    expect(result.current.currentIndex).toBe(1)
    expect(result.current.total).toBe(3)
    expect(result.current.currentPhoto).toEqual(newCluster[1])
  })

  it('handles empty cluster gracefully', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster([], 0)
    })

    expect(result.current.currentPhoto).toBeNull()
    expect(result.current.currentIndex).toBe(-1)
    expect(result.current.total).toBe(0)
    expect(result.current.position).toBe('0 of 0')
    expect(result.current.hasNext).toBe(false)
    expect(result.current.hasPrevious).toBe(false)
  })

  it('handles goToIndex with valid index', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 0)
    })

    act(() => {
      result.current.goToIndex(3)
    })

    expect(result.current.currentIndex).toBe(3)
    expect(result.current.currentPhoto).toEqual(mockClusterPhotos[3])
  })

  it('handles goToIndex with invalid index - negative', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 2)
    })

    act(() => {
      result.current.goToIndex(-1)
    })

    // Should not change index
    expect(result.current.currentIndex).toBe(2)
  })

  it('handles goToIndex with invalid index - too large', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 2)
    })

    act(() => {
      result.current.goToIndex(10)
    })

    // Should not change index
    expect(result.current.currentIndex).toBe(2)
  })

  it('clearCluster resets to empty state', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 2)
    })

    expect(result.current.currentPhoto).not.toBeNull()

    act(() => {
      result.current.clearCluster()
    })

    expect(result.current.currentPhoto).toBeNull()
    expect(result.current.currentIndex).toBe(-1)
    expect(result.current.total).toBe(0)
    expect(result.current.position).toBe('0 of 0')
  })

  it('defaults to index 0 if startIndex not provided', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos)
    })

    expect(result.current.currentIndex).toBe(0)
    expect(result.current.currentPhoto).toEqual(mockClusterPhotos[0])
  })

  it('initializes with empty state', () => {
    const { result } = renderHook(() => useClusterNavigation())

    expect(result.current.currentPhoto).toBeNull()
    expect(result.current.currentIndex).toBe(-1)
    expect(result.current.total).toBe(0)
    expect(result.current.position).toBe('0 of 0')
    expect(result.current.hasNext).toBe(false)
    expect(result.current.hasPrevious).toBe(false)
  })

  it('handles rapid navigation calls', () => {
    const { result } = renderHook(() => useClusterNavigation())

    act(() => {
      result.current.setCluster(mockClusterPhotos, 2)
    })

    act(() => {
      result.current.goNext()
      result.current.goNext()
      result.current.goPrevious()
    })

    // Should end at index 3
    expect(result.current.currentIndex).toBe(3)
  })
})
